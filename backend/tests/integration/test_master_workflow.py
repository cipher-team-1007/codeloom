import pytest
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from engine.orchestrator.master_workflow import MasterOrchestrator
from engine.models import Finding, Source, Category, Severity
from engine.repository.models import SourceSnapshot
from engine.source_intelligence.models import SourceMappingResult, SourceCandidate
from engine.models.patch_plan import PatchCandidate, PatchPlan
from engine.models.patch_validation import PatchValidationResult
from engine.models.sandbox_verification import SandboxVerificationResult

FIXTURE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "experiments", "source-mapping", "fixture"))

@pytest.fixture
def baseline_finding():
    return Finding(
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

@pytest.fixture
def repo_url():
    return "https://github.com/example/repo"

@pytest.fixture
def commit_sha():
    return "dummy-sha"

@pytest.fixture
def mock_acquirer():
    acquirer = MagicMock()
    acquirer.acquire.return_value = SourceSnapshot(
        local_path=FIXTURE_PATH,
        commit_sha="dummy-sha",
        repository_identity="https://github.com/example/repo"
    )
    acquirer._cleanup_workspace = MagicMock()
    return acquirer

@pytest.fixture
def mock_source_intel():
    intel = AsyncMock()
    intel.map_source.return_value = SourceMappingResult(
        status="MATCHED",
        candidates=[
            SourceCandidate(
                file="src/components/ProductCard.tsx",
                component="ProductCard",
                element="div",
                score=99,
                sourceRange={
                    "start": {"line": 3, "column": 0}
                },
                signals=[]
            )
        ]
    )
    return intel

@pytest.fixture
def mock_patch_generator():
    gen = AsyncMock()
    import os
    import difflib
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "experiments", "source-mapping", "fixture"))
    file_path = os.path.join(fixture_path, "src", "components", "ProductCard.tsx")
    
    with open(file_path, "r", encoding="utf-8") as f:
        old_content = f.readlines()
        
    new_content = []
    for line in old_content:
        if '<img className="product-image" src={image} />' in line:
            new_content.append(line.replace('<img className="product-image" src={image} />', '<img className="product-image" src={image} alt={title} />'))
        else:
            new_content.append(line)
            
    diff_lines = list(difflib.unified_diff(
        old_content, new_content,
        fromfile="a/src/components/ProductCard.tsx",
        tofile="b/src/components/ProductCard.tsx"
    ))
    diff = "".join(diff_lines)
    
    gen.generate_patch.return_value = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff=diff,
        rationale="Added alt text"
    )
    return gen

@pytest.fixture
def orchestrator(mock_acquirer, mock_source_intel, mock_patch_generator):
    orch = MasterOrchestrator()
    orch.repo_acquirer = mock_acquirer
    orch.source_intel = mock_source_intel
    orch.patch_generator = mock_patch_generator
    # We will use the REAL PatchValidator and SandboxExecutor to prove E2E integration,
    # except in tests where we intentionally want to mock a failure in those.
    return orch

@pytest.mark.asyncio
async def test_a_source_mapping_ambiguous(orchestrator, baseline_finding, repo_url, commit_sha):
    orchestrator.source_intel.map_source.return_value = SourceMappingResult(
        status="AMBIGUOUS",
        candidates=[]
    )
    
    result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
    assert result.final_status == "FAILED"
    assert result.failure_stage == "SOURCE_MAPPING_AMBIGUOUS"
    orchestrator.patch_generator.generate_patch.assert_not_called()

@pytest.mark.asyncio
async def test_b_source_mapping_not_found(orchestrator, baseline_finding, repo_url, commit_sha):
    orchestrator.source_intel.map_source.return_value = SourceMappingResult(
        status="NOT_FOUND",
        candidates=[]
    )
    
    result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
    assert result.final_status == "FAILED"
    assert result.failure_stage == "SOURCE_MAPPING_NOT_FOUND"

@pytest.mark.asyncio
async def test_c_patch_generation_rejected(orchestrator, baseline_finding, repo_url, commit_sha):
    orchestrator.patch_generator.generate_patch.return_value = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="REJECTED",
        files_changed=[],
        unified_diff="",
        rationale="Prompt injection detected"
    )
    
    with patch.object(orchestrator.patch_validator, 'validate') as mock_validate:
        result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
        assert result.final_status == "FAILED"
        assert result.failure_stage == "PATCH_GENERATION_FAILED"
        mock_validate.assert_not_called()

@pytest.mark.asyncio
async def test_d_patch_validation_fails(orchestrator, baseline_finding, repo_url, commit_sha):
    # Make the patch diff invalid so PatchValidator rejects it
    orchestrator.patch_generator.generate_patch.return_value = PatchCandidate(
        patch_id="patch-1",
        plan_id="plan-1",
        base_commit_sha="dummy-sha",
        status="GENERATED",
        files_changed=["src/components/ProductCard.tsx"],
        unified_diff="--- invalid diff ---",
        rationale="Invalid"
    )
    
    with patch.object(orchestrator.sandbox_executor, 'execute_and_verify') as mock_sandbox:
        result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
        assert result.final_status == "FAILED"
        assert result.failure_stage == "PATCH_VALIDATION_FAILED"
        mock_sandbox.assert_not_called()

@pytest.mark.asyncio
async def test_e_sandbox_startup_fails(orchestrator, baseline_finding, repo_url, commit_sha):
    # Mock SandboxExecutor just for this test
    orchestrator.sandbox_executor.execute_and_verify = AsyncMock(return_value=SandboxVerificationResult(
        status="SANDBOX_START_FAILED",
        patch_id="p", plan_id="p", target_rule="r",
        verification_reason="crashed"
    ))
    
    result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
    assert result.final_status == "FAILED"
    assert result.failure_stage == "SANDBOX_START_FAILED"

@pytest.mark.asyncio
async def test_f_target_violation_remains(orchestrator, baseline_finding, repo_url, commit_sha):
    orchestrator.sandbox_executor.execute_and_verify = AsyncMock(return_value=SandboxVerificationResult(
        status="NOT_VERIFIED",
        patch_id="p", plan_id="p", target_rule="r",
        verification_reason="Still present"
    ))
    
    result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
    assert result.final_status == "FAILED"
    assert result.failure_stage == "NOT_VERIFIED"

@pytest.mark.asyncio
@pytest.mark.integration
async def test_g_full_successful_remediation(orchestrator, baseline_finding, repo_url, commit_sha):
    """
    This uses the REAL PatchValidator and REAL SandboxExecutor (and real Playwright/Axe)
    against the real fixture. It proves the master orchestration correctly glues them together.
    """
    
    result = await orchestrator.run_remediation_workflow(baseline_finding, repo_url, commit_sha)
    print("\nFINAL STATUS:", result.final_status)
    print("FAILURE STAGE:", result.failure_stage)
    print("ERROR MSG:", result.error_message)
    
    assert result.final_status == "VERIFIED"
    assert result.failure_stage is None
    assert result.source_mapping_status == "MATCHED"
    assert result.patch_validation_status == "VALID"
    assert result.sandbox_verification_status == "VERIFIED"
    assert result.mapped_file == "src/components/ProductCard.tsx"
    
    # Assert Cleanup happened
    orchestrator.repo_acquirer._cleanup_workspace.assert_called_once()
