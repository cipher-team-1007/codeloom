import os
import shutil
import tempfile
import subprocess
import pytest
import asyncio
from unittest.mock import AsyncMock

from engine.sandbox.executor import SandboxExecutor
from engine.models.patch_plan import PatchCandidate, PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
from engine.models.patch_validation import PatchValidationResult
from engine.models.sandbox_verification import FindingIdentity
from engine.repository.models import SourceSnapshot

FIXTURE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "experiments", "source-mapping", "fixture"))

@pytest.fixture
def valid_snapshot():
    return SourceSnapshot(
        local_path=FIXTURE_PATH,
        commit_sha="dummy-sha",
        repository_identity="fixture-repo"
    )

@pytest.fixture
def mock_snapshot(tmp_path):
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_dir), check=True)
    
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    comp_dir = src_dir / "components"
    comp_dir.mkdir()
    
    product_card = comp_dir / "ProductCard.tsx"
    product_card.write_text("export function ProductCard({ image, title }: { image: string, title: string }) {\n  return (\n    <div className=\"product-card\" data-title={title}>\n      <img className=\"product-image\" src={image} />\n      <h3>{title}</h3>\n    </div>\n  );\n}\n")
    
    package_json = repo_dir / "package.json"
    package_json.write_text('{"name": "test"}')
    
    # We create a dummy vite.config.ts and a dummy script that sleeps so we can mock vite
    vite_cmd = repo_dir / "vite.bat" if os.name == "nt" else repo_dir / "vite"
    if os.name == "nt":
        # Powershell or batch to start a python web server to simulate vite
        vite_cmd.write_text("@echo off\npython -m http.server %5")
    else:
        vite_cmd.write_text("#!/bin/bash\npython3 -m http.server $5")
        os.chmod(vite_cmd, 0o755)
        
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(repo_dir), check=True)
    
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), capture_output=True, text=True, check=True).stdout.strip()
    
    return SourceSnapshot(
        local_path=str(repo_dir),
        commit_sha=commit_sha,
        repository_identity="test-repo"
    )

@pytest.fixture
def mock_candidate():
    return PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -4,7 +4,7 @@\n   return (\n     <div className=\"product-card\" data-title={title}>\n       {/* Intentionally missing alt attribute */}\n-      <img className=\"product-image\" src={image} />\n+      <img className=\"product-image\" src={image} alt={title} />\n       <h3>{title}</h3>\n     </div>\n   );\n",
        rationale="Added alt text"
    )

@pytest.fixture
def mock_validation():
    return PatchValidationResult(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="VALID"
    )

@pytest.fixture
def baseline_finding():
    return FindingIdentity(
        rule_id="image-alt",
        selectors=["img.product-image"]
    )

@pytest.mark.asyncio
async def test_invalid_patch_rejected_before_execution(mock_snapshot, mock_candidate, baseline_finding):
    invalid_validation = PatchValidationResult(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="CONSTRAINT_VIOLATION"
    )
    
    executor = SandboxExecutor()
    result = await executor.execute_and_verify(mock_candidate, invalid_validation, mock_snapshot, baseline_finding)
    
    assert result.status == "NOT_VERIFIED"
    assert "rejected by validator" in result.verification_reason

@pytest.mark.asyncio
async def test_validated_patch_starts_application(mock_snapshot, mock_candidate, mock_validation, baseline_finding, monkeypatch):
    executor = SandboxExecutor()
    # Mock AxeScanner to prevent real scan, we just want to see it started
    executor.axe_scanner.scan_url = AsyncMock(return_value=[])
    
    # We must patch shutil.which so that 'npx' resolves to our dummy vite script
    def mock_which(cmd):
        if cmd == "npx":
            return os.path.join(mock_snapshot.local_path, "vite.bat" if os.name == "nt" else "vite")
        return shutil.which(cmd)
    monkeypatch.setattr(shutil, "which", mock_which)
    
    # Need to update mock_candidate diff to match mock_snapshot exactly
    mock_candidate.unified_diff = "--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,6 @@\n   return (\n     <div className=\"product-card\" data-title={title}>\n-      <img className=\"product-image\" src={image} />\n+      <img className=\"product-image\" src={image} alt={title} />\n       <h3>{title}</h3>\n     </div>\n   );\n"
    
    result = await executor.execute_and_verify(mock_candidate, mock_validation, mock_snapshot, baseline_finding)
    
    # Wait, AxeScanner returned [], so there are no findings, so the target violation disappeared!
    assert result.status == "VERIFIED"
    assert "no longer exists" in result.verification_reason
    
    # Verify original unchanged
    original_content = open(os.path.join(mock_snapshot.local_path, "src", "components", "ProductCard.tsx")).read()
    assert "alt={title}" not in original_content

@pytest.mark.asyncio
async def test_target_violation_exists_after_patch(mock_snapshot, mock_candidate, mock_validation, baseline_finding, monkeypatch):
    executor = SandboxExecutor()
    
    # Mock AxeScanner to return the finding STILL EXISTS
    from engine.models import Finding, Source, Category, Severity
    mock_finding = Finding(
        source=Source.AXE,
        category=Category.ACCESSIBILITY,
        rule_id="image-alt",
        title="Images must have alternate text",
        description="...",
        severity=Severity.MODERATE,
        selectors=["img.product-image"],
        html_snippets=["<img class='product-image' />"],
        help_url="...",
        page_url="..."
    )
    executor.axe_scanner.scan_url = AsyncMock(return_value=[mock_finding])
    
    def mock_which(cmd):
        if cmd == "npx":
            return os.path.join(mock_snapshot.local_path, "vite.bat" if os.name == "nt" else "vite")
        return shutil.which(cmd)
    monkeypatch.setattr(shutil, "which", mock_which)
    
    mock_candidate.unified_diff = "--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,6 @@\n   return (\n     <div className=\"product-card\" data-title={title}>\n-      <img className=\"product-image\" src={image} />\n+      <img className=\"product-image\" src={image} alt={title} />\n       <h3>{title}</h3>\n     </div>\n   );\n"
    
    result = await executor.execute_and_verify(mock_candidate, mock_validation, mock_snapshot, baseline_finding)
    
    assert result.status == "NOT_VERIFIED"
    assert "still present" in result.verification_reason

@pytest.mark.asyncio
async def test_application_crashes_after_patch(mock_snapshot, mock_candidate, mock_validation, baseline_finding, monkeypatch):
    executor = SandboxExecutor()
    
    # Make the dummy script immediately exit
    vite_cmd = os.path.join(mock_snapshot.local_path, "vite.bat" if os.name == "nt" else "vite")
    with open(vite_cmd, "w") as f:
        f.write("@echo off\nexit 1" if os.name == "nt" else "#!/bin/bash\nexit 1")
        
    def mock_which(cmd):
        if cmd == "npx":
            return vite_cmd
        return shutil.which(cmd)
    monkeypatch.setattr(shutil, "which", mock_which)
    
    mock_candidate.unified_diff = "--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,6 @@\n   return (\n     <div className=\"product-card\" data-title={title}>\n-      <img className=\"product-image\" src={image} />\n+      <img className=\"product-image\" src={image} alt={title} />\n       <h3>{title}</h3>\n     </div>\n   );\n"
    
    result = await executor.execute_and_verify(mock_candidate, mock_validation, mock_snapshot, baseline_finding)
    
    assert result.status == "SANDBOX_PROCESS_EXITED"

@pytest.mark.asyncio
async def test_startup_timeout_handled(mock_snapshot, mock_candidate, mock_validation, baseline_finding, monkeypatch):
    executor = SandboxExecutor()
    
    # Dummy script that sleeps instead of starting a web server
    vite_cmd = os.path.join(mock_snapshot.local_path, "vite.bat" if os.name == "nt" else "vite")
    with open(vite_cmd, "w") as f:
        f.write("@echo off\npython -c \"import time; time.sleep(200)\"" if os.name == "nt" else "#!/bin/bash\npython3 -c \"import time; time.sleep(200)\"")
        
    def mock_which(cmd):
        if cmd == "npx":
            return vite_cmd
        return shutil.which(cmd)
    monkeypatch.setattr(shutil, "which", mock_which)
    
    # We will lower the timeout for tests inside SandboxExecutor using monkeypatch
    import engine.sandbox.executor
    original_sleep = engine.sandbox.executor.time.sleep
    def mock_sleep(secs):
        pass # fast forward
    monkeypatch.setattr(engine.sandbox.executor.time, "sleep", mock_sleep)
    
    # Mock urlopen to fail instantly instead of taking 150 seconds
    import urllib.request
    from urllib.error import URLError
    def mock_urlopen(*args, **kwargs):
        raise URLError("Connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    mock_candidate.unified_diff = "--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,6 @@\n   return (\n     <div className=\"product-card\" data-title={title}>\n-      <img className=\"product-image\" src={image} />\n+      <img className=\"product-image\" src={image} alt={title} />\n       <h3>{title}</h3>\n     </div>\n   );\n"
    
    result = await executor.execute_and_verify(mock_candidate, mock_validation, mock_snapshot, baseline_finding)
    
    assert result.status == "SANDBOX_TIMEOUT"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_end_to_end_fixture_verification(valid_snapshot, mock_candidate, mock_validation, baseline_finding):
    """
    Test 32: FIRST END-TO-END PROOF
    This actually runs Vite and Playwright!
    """
    # The fixture already has `image-alt` missing.
    # The `mock_candidate` adds `alt={title}` which fixes the rule.
    
    executor = SandboxExecutor()
    result = await executor.execute_and_verify(mock_candidate, mock_validation, valid_snapshot, baseline_finding)
    
    # If successful, Axe should no longer report image-alt for img.product-image
    assert result.status == "VERIFIED", f"Failed: {result.verification_reason}"
    assert "no longer exists" in result.verification_reason
    assert result.execution_metadata["startup_duration"] > 0
    assert result.execution_metadata["scan_duration"] > 0
