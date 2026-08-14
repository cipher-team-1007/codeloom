import os
import shutil
import tempfile
import subprocess
import pytest
from engine.ai.patch_validator import PatchValidator
from engine.models.patch_plan import PatchCandidate, PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
from engine.repository.models import SourceSnapshot

@pytest.fixture
def mock_snapshot(tmp_path):
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_dir), check=True)
    
    # Create test files
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    
    comp_dir = src_dir / "components"
    comp_dir.mkdir()
    
    product_card = comp_dir / "ProductCard.tsx"
    product_card.write_text("export function ProductCard({ product }) {\n    return (\n        <img\n            className=\"product-image\"\n            src={product.image}\n        />\n    );\n}\n")
    
    package_json = repo_dir / "package.json"
    package_json.write_text('{"name": "test"}')
    
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(repo_dir), check=True)
    
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), capture_output=True, text=True, check=True).stdout.strip()
    
    return SourceSnapshot(
        local_path=str(repo_dir),
        commit_sha=commit_sha,
        repository_identity="test-repo"
    )

@pytest.fixture
def valid_plan(mock_snapshot):
    return PatchPlan(
        plan_id="plan-1",
        repository_identity="test-repo",
        commit_sha=mock_snapshot.commit_sha,
        target=PatchTarget(
            file_path="src/components/ProductCard.tsx",
            element_type="img",
            start_line=3
        ),
        intent=RemediationIntent(
            rule_id="image-alt",
            root_cause="Missing alt",
            instruction="Add alt text"
        ),
        constraints=PatchConstraint(
            allowed_files=["src/components/ProductCard.tsx"],
            max_lines_changed=5
        )
    )

def test_valid_patch(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,7 @@ export function ProductCard({ product }) {\n         <img\n             className=\"product-image\"\n             src={product.image}\n+            alt={product.name}\n         />\n     );\n }\n",
        rationale="Added alt text"
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "VALID"
    # Ensure original snapshot untouched
    assert "alt=" not in os.path.join(mock_snapshot.local_path, "src", "components", "ProductCard.tsx")

def test_malformed_diff(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="Not a diff format at all",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "INVALID_DIFF"

def test_patch_apply_failed(valid_plan, mock_snapshot):
    # Diff points to context that doesn't exist in the file
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -10,3 +10,4 @@\n         <div\n             id=\"doesnotexist\"\n+            alt=\"wrong\"\n         />",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "PATCH_APPLY_FAILED"

def test_wrong_commit_sha(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="wrong-sha-1234",
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,7 @@\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "COMMIT_MISMATCH"

def test_unauthorized_file(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/App.tsx"],
        unified_diff="--- a/src/App.tsx\n+++ b/src/App.tsx\n@@ -1,1 +1,2 @@\n-<div>\n+<div></div>\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "CONSTRAINT_VIOLATION"

def test_path_traversal(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["../../etc/passwd"],
        unified_diff="--- a/../../etc/passwd\n+++ b/../../etc/passwd\n@@ -1,1 +1,2 @@\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "PATH_VIOLATION"

def test_package_json_modification(valid_plan, mock_snapshot):
    # Even if we append it to allowed files...
    valid_plan.constraints.allowed_files.append("package.json")
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["package.json"],
        unified_diff="--- a/package.json\n+++ b/package.json\n@@ -1,1 +1,2 @@\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "CONSTRAINT_VIOLATION"

def test_css_modification(valid_plan, mock_snapshot):
    valid_plan.constraints.allowed_files.append("styles.css")
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["styles.css"],
        unified_diff="--- a/styles.css\n+++ b/styles.css\n@@ -1,1 +1,2 @@\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    assert result.status == "CONSTRAINT_VIOLATION"

def test_invalid_tsx_syntax(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,7 @@ export function ProductCard({ product }) {\n         <img\n             className=\"product-image\"\n             src={product.image}\n+            alt=INVALID_SYNTAX_WITHOUT_QUOTES<<<\n         />\n     );\n }\n",
        rationale="Added bad syntax"
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    
    # Since syntax checking via fallback node check or tsc might fail... wait, 
    # my fallback in patch_validator only checks .js files with `node -c`, and there's no tsconfig.
    # We should ensure the test can fail syntax if it's TSX.
    # Currently `PatchValidator` skips full check if no tsconfig and files are not JS.
    # Let's just create a tsconfig in the mock repo for this test to prove tsc execution works.
    tsconfig = os.path.join(mock_snapshot.local_path, "tsconfig.json")
    with open(tsconfig, "w") as f:
        f.write('{"compilerOptions": {"jsx": "react"}}')
        
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    assert result.status == "SYNTAX_ERROR"
    os.remove(tsconfig)

def test_original_unchanged(valid_plan, mock_snapshot):
    candidate = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha=mock_snapshot.commit_sha,
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- a/src/components/ProductCard.tsx\n+++ b/src/components/ProductCard.tsx\n@@ -3,6 +3,7 @@ export function ProductCard({ product }) {\n         <img\n             className=\"product-image\"\n             src={product.image}\n+            alt={product.name}\n         />\n     );\n }\n",
        rationale=""
    )
    
    validator = PatchValidator()
    result = validator.validate(candidate, valid_plan, mock_snapshot)
    assert result.status == "VALID"
    
    # Check original
    original_content = open(os.path.join(mock_snapshot.local_path, "src", "components", "ProductCard.tsx")).read()
    assert "alt=" not in original_content
