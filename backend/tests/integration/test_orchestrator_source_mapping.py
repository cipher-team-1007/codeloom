import pytest
import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from engine.orchestrator.orchestrator import EngineOrchestrator
from engine.models.finding import Finding
from engine.config import EngineConfig

os.environ["SOURCE_INTELLIGENCE_URL"] = "http://127.0.0.1:8004"

@pytest.fixture
def e2e_git_repo():
    """Creates a temporary local git repository for E2E testing."""
    repo_dir = tempfile.mkdtemp(prefix="e2e_test_repo_")
    
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Create a TSX file that matches the finding
    os.makedirs(os.path.join(repo_dir, "components"), exist_ok=True)
    file_path = os.path.join(repo_dir, "components", "ProductCard.tsx")
    with open(file_path, "w") as f:
        f.write('''
export function ProductCard() {
    return (
        <div className="card">
            <img className="product-image" src="/placeholder1.jpg" />
        </div>
    );
}
''')
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit with issue"], cwd=repo_dir, check=True)
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()
    
    yield {
        "url": repo_dir,
        "commit": commit_sha
    }
    
    def handle_remove_readonly(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(repo_dir, onerror=handle_remove_readonly)


@pytest.mark.asyncio
async def test_orchestrator_source_mapping(e2e_git_repo, monkeypatch):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', 8004)) != 0:
            pytest.skip("Source intelligence Node service not running on port 8004")

    # Setup orchestrator with dummy config
    config = EngineConfig(dry_run=True, max_tokens_per_scan=1000)
    orchestrator = EngineOrchestrator(config)
    
    # Patch validation to allow local file paths for testing
    monkeypatch.setattr(orchestrator.repo_acquirer, "_validate_url", lambda x: True)
    
    findings = [
        Finding(
            source="axe",
            category="accessibility",
            rule_id="image-alt",
            title="Image missing alt attribute",
            description="Images must have alternate text",
            severity="critical",
            selectors=["img.product-image"],
            html_snippets=['<img class="product-image" src="/placeholder1.jpg">']
        )
    ]
    
    # Process scan with repo URL attached
    result = await orchestrator.process_scan(
        findings,
        repo_url=e2e_git_repo["url"],
        commit_sha=e2e_git_repo["commit"]
    )
    
    # Verify result
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    
    # Check if the source mapping succeeded and enriched the root cause
    assert "ProductCard.tsx" in cluster.likely_root_cause
    assert "Source mapped to" in cluster.likely_root_cause
