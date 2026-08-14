import os
import shutil
import tempfile
import subprocess
import pytest
from pathlib import Path

from engine.repository.acquirer import RepositoryAcquirer
from engine.repository.models import RepositoryCoordinate
from engine.repository.exceptions import (
    InvalidRepositoryURLError,
    UnsupportedRepositoryProviderError,
    CommitNotFoundError,
    RepositoryNotFoundError,
    CommitIntegrityFailureError
)

@pytest.fixture(scope="module")
def local_git_repo():
    """Creates a temporary local git repository for deterministic testing."""
    repo_dir = tempfile.mkdtemp(prefix="test_repo_origin_")
    
    # Initialize bare git repository (better for cloning)
    # Actually a normal repository is fine if we just clone the .git folder
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Commit A
    file_path = os.path.join(repo_dir, "ProductCard.tsx")
    with open(file_path, "w") as f:
        f.write("<div>Version A</div>")
    subprocess.run(["git", "add", "ProductCard.tsx"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Commit A"], cwd=repo_dir, check=True)
    commit_a_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()
    
    # Commit B
    with open(file_path, "w") as f:
        f.write("<div>Version B</div>")
    subprocess.run(["git", "add", "ProductCard.tsx"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Commit B"], cwd=repo_dir, check=True)
    commit_b_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()

    # We need to serve this locally or just use file:// for tests if we bypass the validation temporarily.
    # To bypass URL validation strictly for this test, we can patch the validate method.
    yield {
        "url": repo_dir,
        "commit_a": commit_a_sha,
        "commit_b": commit_b_sha
    }
    
    # Cleanup
    def handle_remove_readonly(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(repo_dir, onerror=handle_remove_readonly)


@pytest.fixture
def acquirer(monkeypatch, tmp_path):
    workspace = tmp_path / "workspaces"
    workspace.mkdir(parents=True, exist_ok=True)
    acq = RepositoryAcquirer(workspace_root=str(workspace), timeout=10)
    # Patch validation to allow local file paths for testing
    monkeypatch.setattr(acq, "_validate_url", lambda x: True)
    return acq

def test_commit_a(acquirer, local_git_repo):
    coord = RepositoryCoordinate(
        repository_url=local_git_repo["url"],
        requested_commit_sha=local_git_repo["commit_a"]
    )
    snapshot = acquirer.acquire(coord)
    
    assert snapshot.commit_sha == local_git_repo["commit_a"]
    assert os.path.exists(snapshot.local_path)
    
    # Verify file content is version A
    with open(os.path.join(snapshot.local_path, "ProductCard.tsx"), "r") as f:
        assert f.read() == "<div>Version A</div>"
        
    acquirer._cleanup_workspace(snapshot.local_path)

def test_commit_b(acquirer, local_git_repo):
    coord = RepositoryCoordinate(
        repository_url=local_git_repo["url"],
        requested_commit_sha=local_git_repo["commit_b"]
    )
    snapshot = acquirer.acquire(coord)
    
    assert snapshot.commit_sha == local_git_repo["commit_b"]
    assert os.path.exists(snapshot.local_path)
    
    # Verify file content is version B
    with open(os.path.join(snapshot.local_path, "ProductCard.tsx"), "r") as f:
        assert f.read() == "<div>Version B</div>"
        
    acquirer._cleanup_workspace(snapshot.local_path)

def test_invalid_sha(acquirer, local_git_repo):
    coord = RepositoryCoordinate(
        repository_url=local_git_repo["url"],
        requested_commit_sha="invalid-sha-123"
    )
    with pytest.raises(CommitNotFoundError):
        acquirer.acquire(coord)

def test_invalid_url():
    acq = RepositoryAcquirer() # Use real validation
    coord = RepositoryCoordinate(
        repository_url="file:///etc/passwd",
        requested_commit_sha="any"
    )
    with pytest.raises(InvalidRepositoryURLError):
        acq.acquire(coord)

def test_acquisition_failure(acquirer):
    coord = RepositoryCoordinate(
        repository_url="/path/to/nonexistent/repo",
        requested_commit_sha="any"
    )
    with pytest.raises(RepositoryNotFoundError):
        acquirer.acquire(coord)

def test_cleanup_on_failure(acquirer, local_git_repo):
    coord = RepositoryCoordinate(
        repository_url=local_git_repo["url"],
        requested_commit_sha="invalid-sha-123"
    )
    with pytest.raises(CommitNotFoundError):
        acquirer.acquire(coord)
    
    # Check that temporary workspaces were cleaned up
    # The workspace root should be empty (or only contain other concurrent test dirs, which there aren't)
    workspace_root = acquirer.workspace_root
    assert len(os.listdir(workspace_root)) == 0

@pytest.mark.skipif(not os.environ.get("RUN_INTERNET_TESTS"), reason="Network tests disabled")
def test_public_repository():
    # Use a real public repository to test actual HTTPS cloning
    # We will use something small and reliable, like a minimal test repo
    # But since we shouldn't rely on random internet stuff, we skip by default
    acq = RepositoryAcquirer()
    coord = RepositoryCoordinate(
        repository_url="https://github.com/octocat/Hello-World.git",
        requested_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
    )
    snapshot = acq.acquire(coord)
    assert snapshot.commit_sha == "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
    acq._cleanup_workspace(snapshot.local_path)
