import os
import tempfile
import subprocess
import shutil
import pytest

from engine.repository.models import SourceSnapshot, RepositoryCoordinate
from engine.repository.acquirer import RepositoryAcquirer
from engine.queue.snapshot import SnapshotManager, SnapshotEvolutionError


@pytest.fixture
def temp_git_repo():
    """Creates a temporary local git repository with initial commit."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_")
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True)

    # Initial file
    file_path = os.path.join(temp_dir, "ProductCard.tsx")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("export function ProductCard() {\n  return <img src='/hero.png' />;\n}\n")

    subprocess.run(["git", "add", "ProductCard.tsx"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)

    rev_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True, check=True)
    base_sha = rev_res.stdout.strip()

    yield temp_dir, base_sha

    # Teardown
    def handle_remove_readonly(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)


def test_snapshot_initialization(temp_git_repo):
    repo_path, base_sha = temp_git_repo

    mgr = SnapshotManager()
    mgr._initial_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)
    mgr._current_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)

    assert mgr.current_working_sha == base_sha
    assert mgr.modified_files == []


def test_apply_verified_patch_single_file(temp_git_repo):
    repo_path, base_sha = temp_git_repo

    mgr = SnapshotManager()
    mgr._initial_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)
    mgr._current_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)

    diff = (
        "--- a/ProductCard.tsx\n"
        "+++ b/ProductCard.tsx\n"
        "@@ -1,3 +1,3 @@\n"
        " export function ProductCard() {\n"
        "-  return <img src='/hero.png' />;\n"
        "+  return <img src='/hero.png' alt='Hero image' />;\n"
        " }\n"
    )

    new_sha = mgr.apply_verified_patch(diff, "ProductCard.tsx", rule_id="image-alt")
    assert new_sha != base_sha
    assert mgr.current_working_sha == new_sha
    assert "ProductCard.tsx" in mgr.modified_files

    with open(os.path.join(repo_path, "ProductCard.tsx"), "r", encoding="utf-8") as f:
        content = f.read()
    assert "alt='Hero image'" in content


def test_apply_verified_patch_multi_file_rejection(temp_git_repo):
    repo_path, base_sha = temp_git_repo

    # Add a second file
    with open(os.path.join(repo_path, "Header.tsx"), "w", encoding="utf-8") as f:
        f.write("export function Header() { return <header>Logo</header>; }\n")
    subprocess.run(["git", "add", "Header.tsx"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add header"], cwd=repo_path, check=True, capture_output=True)
    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, check=True).stdout.strip()

    mgr = SnapshotManager()
    mgr._initial_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=head_sha, repository_identity=repo_path)
    mgr._current_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=head_sha, repository_identity=repo_path)

    # Multi-file patch attempting to modify both ProductCard.tsx and Header.tsx
    multi_diff = (
        "--- a/ProductCard.tsx\n"
        "+++ b/ProductCard.tsx\n"
        "@@ -1,3 +1,3 @@\n"
        " export function ProductCard() {\n"
        "-  return <img src='/hero.png' />;\n"
        "+  return <img src='/hero.png' alt='Hero' />;\n"
        " }\n"
        "--- a/Header.tsx\n"
        "+++ b/Header.tsx\n"
        "@@ -1,1 +1,1 @@\n"
        "-export function Header() { return <header>Logo</header>; }\n"
        "+export function Header() { return <header>Updated Logo</header>; }\n"
    )

    with pytest.raises(SnapshotEvolutionError) as exc_info:
        mgr.apply_verified_patch(multi_diff, "ProductCard.tsx", rule_id="image-alt")

    assert "Single-file safety violation" in str(exc_info.value)
    assert mgr.current_working_sha == head_sha


def test_atomic_rollback(temp_git_repo):
    repo_path, base_sha = temp_git_repo

    mgr = SnapshotManager()
    mgr._initial_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)
    mgr._current_snapshot = SourceSnapshot(local_path=repo_path, commit_sha=base_sha, repository_identity=repo_path)

    # Introduce uncommitted dirty changes
    with open(os.path.join(repo_path, "ProductCard.tsx"), "a", encoding="utf-8") as f:
        f.write("\n// Corrupted dirty modification\n")

    # Add an untracked garbage file
    with open(os.path.join(repo_path, "junk.txt"), "w", encoding="utf-8") as f:
        f.write("junk")

    mgr.rollback_unverified_changes()

    assert not os.path.exists(os.path.join(repo_path, "junk.txt"))
    with open(os.path.join(repo_path, "ProductCard.tsx"), "r", encoding="utf-8") as f:
        content = f.read()
    assert "Corrupted" not in content
