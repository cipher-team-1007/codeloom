import os
import subprocess
import logging
from typing import Optional, List, Set
from engine.repository.models import RepositoryCoordinate, SourceSnapshot
from engine.repository.acquirer import RepositoryAcquirer

logger = logging.getLogger("codeloom.queue.snapshot")


class SnapshotEvolutionError(Exception):
    """Raised when snapshot application, verification, or rollback fails."""
    pass


class SnapshotManager:
    """
    Manages the lifecycle and evolution of a working repository snapshot across sequential
    remediation jobs in a multi-finding queue.
    """

    def __init__(self, repo_acquirer: Optional[RepositoryAcquirer] = None):
        self.repo_acquirer = repo_acquirer or RepositoryAcquirer()
        self._initial_snapshot: Optional[SourceSnapshot] = None
        self._current_snapshot: Optional[SourceSnapshot] = None
        self._modified_files: Set[str] = set()
        self._applied_diffs: List[str] = []

    @property
    def current_snapshot(self) -> Optional[SourceSnapshot]:
        return self._current_snapshot

    @property
    def current_working_sha(self) -> str:
        if not self._current_snapshot:
            return ""
        return self._current_snapshot.commit_sha

    @property
    def modified_files(self) -> List[str]:
        return sorted(list(self._modified_files))

    def initialize(self, repository_url: str, base_commit_sha: str) -> SourceSnapshot:
        """Acquires initial repository clone at base_commit_sha."""
        coord = RepositoryCoordinate(repository_url=repository_url, requested_commit_sha=base_commit_sha)
        snapshot = self.repo_acquirer.acquire(coord)
        self._initial_snapshot = snapshot
        self._current_snapshot = SourceSnapshot(
            local_path=snapshot.local_path,
            commit_sha=snapshot.commit_sha,
            repository_identity=snapshot.repository_identity
        )
        self._modified_files.clear()
        self._applied_diffs.clear()

        # Configure local git user if not present (for local commits on working branch)
        self._run_git(["config", "user.name", "CodeLoom Engine"])
        self._run_git(["config", "user.email", "engine@codeloom.local"])

        logger.info(f"Initialized snapshot manager for {repository_url} at base commit {base_commit_sha[:7]}")
        return self._current_snapshot

    def apply_verified_patch(self, unified_diff: str, target_file: str, rule_id: str = "a11y-fix") -> str:
        """
        Applies an independently verified patch candidate to the cumulative working tree,
        enforces single-file modification boundaries, and commits locally to advance working SHA.
        """
        if not self._current_snapshot or not os.path.exists(self._current_snapshot.local_path):
            raise SnapshotEvolutionError("No active working snapshot available to apply patch.")

        cwd = self._current_snapshot.local_path
        patch_file = os.path.join(cwd, ".codeloom_temp.patch")

        try:
            from engine.ai.patch_generator import normalize_unified_diff
            unified_diff = normalize_unified_diff(unified_diff)

            # 1. Write patch file
            with open(patch_file, "w", encoding="utf-8") as f:
                f.write(unified_diff)

            # 2. Apply patch via git apply with --recount and --3way for shifted hunks
            apply_res = subprocess.run(
                ["git", "apply", "--ignore-whitespace", "--ignore-space-change", "--recount", "--3way", ".codeloom_temp.patch"],
                cwd=cwd, capture_output=True, text=True, check=False
            )
            # Remove temp patch file immediately so it is never seen by git diff
            if os.path.exists(patch_file):
                try:
                    os.remove(patch_file)
                except Exception:
                    pass

            if apply_res.returncode != 0:
                logger.warning(f"git apply failed in snapshot manager: {apply_res.stderr.strip()}. Trying robust string-replace/insertion fallback.")
                applied_direct = False
                target_abs = os.path.join(cwd, target_file)
                if os.path.exists(target_abs):
                    try:
                        with open(target_abs, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        lines = unified_diff.splitlines()
                        deletions = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]
                        additions = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
                        context = [l[1:] for l in lines if l.startswith(" ") and l[1:].strip()]

                        new_content = None
                        if deletions and additions:
                            target_str = "\n".join(deletions)
                            replacement_str = "\n".join(additions)
                            if target_str in content:
                                new_content = content.replace(target_str, replacement_str, 1)
                            else:
                                # Try line-by-line whitespace-stripped matching
                                strip_target = "\n".join([d.strip() for d in deletions if d.strip()])
                                content_lines = content.splitlines()
                                for i in range(len(content_lines) - len(deletions) + 1):
                                    chunk = "\n".join([c.strip() for c in content_lines[i:i+len(deletions)]])
                                    if chunk == strip_target:
                                        content_lines[i:i+len(deletions)] = [replacement_str]
                                        new_content = "\n".join(content_lines)
                                        break
                        elif additions and not deletions:
                            replacement_str = "\n".join(additions)
                            # Check if insertion anchor context line exists (like </head> or <body>)
                            for c in context:
                                c_strip = c.strip()
                                if c_strip and c_strip in content:
                                    if "</head>" in c_strip:
                                        new_content = content.replace("</head>", replacement_str + "\n</head>", 1)
                                    elif "<body>" in c_strip:
                                        new_content = content.replace("<body>", "<body>\n" + replacement_str, 1)
                                    elif "<head>" in c_strip:
                                        new_content = content.replace("<head>", "<head>\n" + replacement_str, 1)
                                    else:
                                        new_content = content.replace(c_strip, c_strip + "\n" + replacement_str, 1)
                                    break
                            if not new_content:
                                if "</head>" in content:
                                    new_content = content.replace("</head>", replacement_str + "\n</head>", 1)
                                elif "<body>" in content:
                                    new_content = content.replace("<body>", "<body>\n" + replacement_str, 1)

                        if new_content and new_content != content:
                            with open(target_abs, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            applied_direct = True
                            logger.info("Fallback string replacement patch application succeeded in snapshot manager.")
                    except Exception as e:
                        logger.warning(f"Direct string replacement failed: {e}")
                
                if not applied_direct:
                    raise SnapshotEvolutionError(f"Failed to apply verified patch to snapshot: {apply_res.stderr.strip()}")

            # 3. Verify single-file safety boundary
            diff_names = self._run_git(["diff", "--name-only"]).strip().splitlines()
            cleaned_names = [f.strip().replace("\\", "/") for f in diff_names if f.strip() and not f.strip().startswith(".codeloom_temp")]

            # Normalize target file
            norm_target = target_file.replace("\\", "/").lstrip("/")
            for changed in cleaned_names:
                if not changed.endswith(norm_target) and not norm_target.endswith(changed):
                    # Multi-file boundary violation
                    self.rollback_unverified_changes()
                    raise SnapshotEvolutionError(
                        f"Single-file safety violation: expected only '{target_file}', but '{changed}' was modified."
                    )

            # 4. Commit locally to record snapshot state
            self._run_git(["add", "-A"])
            self._run_git(["commit", "-m", f"Verified fix for {rule_id} in {target_file}"])

            # 5. Obtain new working tree commit SHA
            new_head_sha = self._run_git(["rev-parse", "HEAD"]).strip()
            self._current_snapshot.commit_sha = new_head_sha
            self._modified_files.add(target_file)
            self._applied_diffs.append(unified_diff)

            logger.info(f"Advanced snapshot to working SHA {new_head_sha[:7]} after verified fix for {rule_id}")
            return new_head_sha

        finally:
            if os.path.exists(patch_file):
                try:
                    os.remove(patch_file)
                except Exception:
                    pass

    def rollback_unverified_changes(self):
        """
        Guarantees atomic reversion: discards any uncommitted or dirty changes left by
        failed, unverified, or aborted remediation attempts.
        """
        if not self._current_snapshot or not os.path.exists(self._current_snapshot.local_path):
            return

        cwd = self._current_snapshot.local_path
        patch_file = os.path.join(cwd, ".codeloom_temp.patch")
        if os.path.exists(patch_file):
            try:
                os.remove(patch_file)
            except Exception:
                pass

        try:
            self._run_git(["reset", "--hard", "HEAD"])
            self._run_git(["clean", "-fd"])
            logger.info(f"Cleaned working tree back to verified commit {self.current_working_sha[:7]}")
        except Exception as e:
            logger.warning(f"Error during atomic rollback in {cwd}: {e}")

    def cleanup(self):
        """Cleans up the working workspace directory."""
        if self._initial_snapshot:
            try:
                self.repo_acquirer._cleanup_workspace(self._initial_snapshot.local_path)
            except Exception as e:
                logger.warning(f"Error cleaning up snapshot manager workspace: {e}")
        self._initial_snapshot = None
        self._current_snapshot = None

    def _run_git(self, cmd: list) -> str:
        """Helper to run git commands inside the working snapshot directory."""
        cwd = self._current_snapshot.local_path if self._current_snapshot else None
        res = subprocess.run(
            ["git"] + cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode != 0:
            raise SnapshotEvolutionError(f"Git {' '.join(cmd)} failed: {res.stderr.strip()}")
        return res.stdout
