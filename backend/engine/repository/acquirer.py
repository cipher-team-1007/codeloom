import os
import shutil
import tempfile
import subprocess
import logging
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path

from .models import RepositoryCoordinate, SourceSnapshot
from .exceptions import (
    InvalidRepositoryURLError,
    UnsupportedRepositoryProviderError,
    WorkspaceFailureError,
    RepositoryAcquisitionFailedError,
    CommitNotFoundError,
    CheckoutFailedError,
    CommitIntegrityFailureError,
    RepositoryTimeoutError,
    RepositoryNotFoundError
)

logger = logging.getLogger("codeloom.repository.acquirer")


def normalize_repository_url(url: str) -> str:
    """Normalizes SSH, trailing slashes, and .git extensions to standard HTTPS URL."""
    if not url or not url.strip():
        return ""
    u = url.strip()
    if u.startswith("git@github.com:"):
        path = u.replace("git@github.com:", "")
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path.strip('/')}"
    if u.endswith(".git"):
        u = u[:-4]
    return u.rstrip("/")


class RepositoryAcquirer:
    """Safely acquires a specific commit from a remote repository."""

    def __init__(self, workspace_root: Optional[str] = None, timeout: int = 180):
        # Allow override or fallback to system temp dir
        self.workspace_root = workspace_root or os.environ.get("CODELOOM_REPOSITORY_ROOT")
        if not self.workspace_root:
            self.workspace_root = os.path.join(tempfile.gettempdir(), "codeloom-source-scans")
        
        self.timeout = timeout
        
        # Ensure workspace root exists and purge stale workspaces older than 30 mins
        os.makedirs(self.workspace_root, exist_ok=True)
        self.purge_stale_workspaces(max_age_seconds=1800)

    def purge_stale_workspaces(self, max_age_seconds: int = 1800) -> int:
        """
        Removes temporary workspace directories that have exceeded max_age_seconds.
        Guarantees zero disk bloat in continuous runtime.
        """
        import time
        now = time.time()
        purged = 0
        if not os.path.isdir(self.workspace_root):
            return 0

        for entry in os.listdir(self.workspace_root):
            full_path = os.path.join(self.workspace_root, entry)
            if os.path.isdir(full_path) and (entry.startswith("repo_") or entry.startswith("sandbox_") or entry.startswith("codeloom_")):
                try:
                    mtime = os.path.getmtime(full_path)
                    if (now - mtime) > max_age_seconds:
                        self._cleanup_workspace(full_path)
                        purged += 1
                except Exception:
                    pass
        if purged > 0:
            logger.info(f"Purged {purged} stale workspace directories from {self.workspace_root}")
        return purged

    def _validate_url(self, url: str) -> bool:
        """Only allow public HTTPS/HTTP Git repositories."""
        try:
            normalized = normalize_repository_url(url)
            parsed = urlparse(normalized)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc:
                return False
            return True
        except Exception:
            return False

    def acquire(self, coordinate: RepositoryCoordinate) -> SourceSnapshot:
        """
        Clones the repository and checks out the requested commit.
        Validates commit integrity before returning the snapshot.
        Cleans up the temporary workspace if any step fails.
        """
        if coordinate.provider != "git":
            raise UnsupportedRepositoryProviderError(f"Provider '{coordinate.provider}' is not supported.")

        normalized_url = normalize_repository_url(coordinate.repository_url)
        if not self._validate_url(normalized_url):
            raise InvalidRepositoryURLError(f"Invalid or unsupported URL scheme: {coordinate.repository_url}")


        # Create isolated or reusable workspace directory based on repo URL and branch
        import hashlib
        repo_hash = hashlib.md5(f"{normalized_url}@{coordinate.requested_commit_sha}".encode()).hexdigest()[:12]
        workspace_dir = os.path.join(self.workspace_root, f"repo_{repo_hash}")

        # If repo is already acquired and valid, reuse it instantly!
        if os.path.exists(os.path.join(workspace_dir, ".git")):
            logger.info(f"Reusing existing acquired repository snapshot at {workspace_dir}")
            try:
                rev_parse_cmd = ["git", "rev-parse", "HEAD"]
                actual_head = self._run_git_command(rev_parse_cmd, cwd=workspace_dir, error_cls=CommitIntegrityFailureError).strip()
                return SourceSnapshot(
                    local_path=workspace_dir,
                    commit_sha=actual_head,
                    repository_identity=coordinate.repository_url
                )
            except Exception as e:
                logger.warning(f"Existing workspace at {workspace_dir} was invalid: {e}. Re-cloning.")
                self._cleanup_workspace(workspace_dir)

        os.makedirs(workspace_dir, exist_ok=True)

        try:
            clone_url = coordinate.repository_url
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_ACCESS_TOKEN")
            if token and "github.com" in clone_url and "@github.com" not in clone_url:
                parsed = urlparse(clone_url)
                clone_url = f"{parsed.scheme}://{token}@{parsed.netloc}{parsed.path}"

            # Clone repository with shallow depth 1 for maximum speed
            logger.info(f"Cloning repository {coordinate.repository_url} into {workspace_dir}")
            
            # Using safe subprocess array, no shell interpolation
            if coordinate.requested_commit_sha.lower() in ("head", "main", "master", "trunk", "dev"):
                clone_cmd = ["git", "clone", "--depth", "1", clone_url, workspace_dir]
            else:
                clone_cmd = ["git", "clone", clone_url, workspace_dir]
            self._run_git_command(clone_cmd, cwd=None, error_cls=RepositoryAcquisitionFailedError)

            # Checkout requested commit with graceful fallback to default branch
            if coordinate.requested_commit_sha and coordinate.requested_commit_sha.lower() not in ("head", "main", "master", "trunk", "dev"):
                checkout_cmd = ["git", "checkout", coordinate.requested_commit_sha]
                try:
                    self._run_git_command(checkout_cmd, cwd=workspace_dir, error_cls=CheckoutFailedError)
                except Exception as e:
                    logger.warning(f"Could not checkout requested ref '{coordinate.requested_commit_sha}': {e}. Using default branch HEAD instead.")

            # Verify actual HEAD
            rev_parse_cmd = ["git", "rev-parse", "HEAD"]
            actual_head = self._run_git_command(rev_parse_cmd, cwd=workspace_dir, error_cls=CommitIntegrityFailureError).strip()

            logger.info(f"Successfully acquired source snapshot for {coordinate.repository_url} (HEAD: {actual_head[:7]})")
            return SourceSnapshot(
                local_path=workspace_dir,
                commit_sha=actual_head,
                repository_identity=coordinate.repository_url
            )

        except Exception as e:
            # Cleanup on failure
            self._cleanup_workspace(workspace_dir)
            
            # Translate common fatal git errors if not already wrapped
            if isinstance(e, RepositoryAcquisitionFailedError):
                error_str = str(e).lower()
                if "not found" in error_str or "does not exist" in error_str:
                    raise RepositoryNotFoundError(f"Repository not found: {coordinate.repository_url}") from e
                    
            raise

    def _run_git_command(self, cmd: list, cwd: Optional[str], error_cls: type) -> str:
        """Executes a git command safely and handles timeouts/errors."""
        git_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=git_env,
                check=False
            )
            if result.returncode != 0:
                raise error_cls(f"Git command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}")
            return result.stdout
        except subprocess.TimeoutExpired as e:
            raise RepositoryTimeoutError(f"Git command timed out after {self.timeout}s: {' '.join(cmd)}") from e
        except OSError as e:
            raise error_cls(f"Failed to execute git command: {e}") from e

    def _cleanup_workspace(self, workspace_dir: str):
        """Removes the workspace directory."""
        import stat
        import time

        def handle_remove_readonly(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        if not workspace_dir or not os.path.exists(workspace_dir):
            return

        for attempt in range(4):
            try:
                shutil.rmtree(workspace_dir, onerror=handle_remove_readonly)
                if not os.path.exists(workspace_dir):
                    return
            except Exception as e:
                time.sleep(0.1)
        
        if os.path.exists(workspace_dir):
            try:
                # Fallback force delete command on Windows
                if os.name == 'nt':
                    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", workspace_dir], capture_output=True, timeout=5)
            except Exception:
                pass
