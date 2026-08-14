import os
import tempfile
import subprocess
import shutil
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from engine.models import Finding, Source, Category, Severity
from engine.repository.models import SourceSnapshot
from engine.repository.acquirer import RepositoryAcquirer
from engine.source_intelligence.client import SourceIntelligenceClient
from engine.source_intelligence.models import (
    SourceMappingResult,
    SourceCandidate,
    SourceRange,
    SourceLocation,
)
from engine.models.patch_plan import (
    PatchCandidate,
    PatchPlan,
    PatchTarget,
    RemediationIntent,
    PatchConstraint,
)
from engine.models.patch_validation import PatchValidationResult, ValidationCheck
from engine.models.sandbox_verification import SandboxVerificationResult, FindingIdentity
from engine.orchestrator.models import RemediationWorkflowResult
from engine.orchestrator.master_workflow import MasterOrchestrator
from engine.queue.models import (
    FindingStatus,
    QueueStatus,
    BatchStatus,
    CanonicalFinding,
)
from engine.queue.remediation_queue import RemediationQueueEngine


@pytest.fixture
def mock_repo():
    temp_dir = tempfile.mkdtemp(prefix="queue_test_repo_")
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Engine"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "engine@codeloom.local"], cwd=temp_dir, check=True, capture_output=True)

    with open(os.path.join(temp_dir, "ProductCard.tsx"), "w", encoding="utf-8") as f:
        f.write("export function ProductCard() {\n  return <img src='/hero.png' />;\n}\n")

    with open(os.path.join(temp_dir, "Header.tsx"), "w", encoding="utf-8") as f:
        f.write("export function Header() {\n  return <button className='menu'></button>;\n}\n")

    subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)
    base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True, check=True).stdout.strip()

    yield temp_dir, base_sha

    def handle_remove_readonly(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)


@pytest.mark.asyncio
async def test_queue_sequential_all_verified(mock_repo):
    repo_path, base_sha = mock_repo

    mock_acquirer = MagicMock(spec=RepositoryAcquirer)
    mock_acquirer.acquire.return_value = SourceSnapshot(
        local_path=repo_path,
        commit_sha=base_sha,
        repository_identity=repo_path
    )

    mock_source_intel = MagicMock(spec=SourceIntelligenceClient)
    
    # Mock source mapping returns ProductCard.tsx
    candidate1 = SourceCandidate(
        file="ProductCard.tsx",
        component="ProductCard",
        element="img",
        score=100,
        sourceRange=SourceRange(
            start=SourceLocation(line=2, column=10)
        )
    )
    mock_source_intel.map_source = AsyncMock(return_value=SourceMappingResult(
        status="EXACT_MATCH",
        candidates=[candidate1]
    ))

    # Mock MasterOrchestrator to return verified patch
    mock_orchestrator = MagicMock(spec=MasterOrchestrator)

    diff1 = (
        "--- a/ProductCard.tsx\n"
        "+++ b/ProductCard.tsx\n"
        "@@ -1,3 +1,3 @@\n"
        " export function ProductCard() {\n"
        "-  return <img src='/hero.png' />;\n"
        "+  return <img src='/hero.png' alt='Product hero' />;\n"
        " }\n"
    )
    candidate_patch = PatchCandidate(
        patch_id="p_001",
        plan_id="plan_001",
        base_commit_sha=base_sha,
        status="GENERATED",
        files_changed=["ProductCard.tsx"],
        unified_diff=diff1,
        rationale="Added alt attribute"
    )

    verified_result = RemediationWorkflowResult(
        workflow_id="wf_001",
        target_rule="image-alt",
        repository_identity=repo_path,
        commit_sha=base_sha,
        final_status="VERIFIED",
        patch_candidate=candidate_patch
    )
    verified_result.finding = Finding(
        source=Source.AXE,
        category=Category.ACCESSIBILITY,
        rule_id="image-alt",
        title="Images missing alt",
        description="Fix image-alt",
        severity=Severity.CRITICAL,
        selectors=["img.hero"],
        html_snippets=["<img src='/hero.png' />"]
    )
    verified_result.source_mapping_result = SourceMappingResult(status="EXACT_MATCH", candidates=[candidate1])
    verified_result.patch_plan = PatchPlan(
        plan_id="plan_001",
        repository_identity=repo_path,
        commit_sha=base_sha,
        target=PatchTarget(file_path="ProductCard.tsx", component_name="ProductCard", element_type="img", start_line=2, end_line=2),
        intent=RemediationIntent(rule_id="image-alt", description="Fix alt", violating_html="<img />", root_cause="missing alt", instruction="add alt"),
        constraints=PatchConstraint(allowed_files=["ProductCard.tsx"], forbid_dependency_changes=True, forbid_css_changes=True, forbid_api_changes=True, max_lines_changed=50)
    )
    verified_result.validation_result = PatchValidationResult(
        status="VALID",
        patch_id="p_001",
        plan_id="plan_001",
        base_commit_sha=base_sha,
        checks=[ValidationCheck(name="SingleFileCheck", status="PASS", message="Valid single file modification")]
    )
    verified_result.sandbox_result = SandboxVerificationResult(
        status="VERIFIED",
        patch_id="p_001",
        plan_id="plan_001",
        target_rule="image-alt",
        baseline_finding=FindingIdentity(rule_id="image-alt", selectors=["img.hero"]),
        verification_reason="Axe-core scan passed with 0 violations."
    )

    mock_orchestrator.run_remediation_workflow = AsyncMock(return_value=verified_result)

    engine = RemediationQueueEngine(
        repo_acquirer=mock_acquirer,
        source_intel=mock_source_intel,
        orchestrator=mock_orchestrator,
    )

    queue = engine.create_queue_from_findings(
        repository_url=repo_path,
        base_commit_sha=base_sha,
        raw_findings=[verified_result.finding]
    )

    batch_report = await engine.run_queue(queue)

    assert batch_report.aggregate_status == BatchStatus.ALL_VERIFIED
    assert batch_report.verified_count == 1
    assert batch_report.failed_count == 0
    assert batch_report.final_working_sha != base_sha


@pytest.mark.asyncio
async def test_queue_failure_continuation_and_snapshot_protection(mock_repo):
    repo_path, base_sha = mock_repo

    mock_acquirer = MagicMock(spec=RepositoryAcquirer)
    mock_acquirer.acquire.return_value = SourceSnapshot(
        local_path=repo_path,
        commit_sha=base_sha,
        repository_identity=repo_path
    )

    mock_source_intel = MagicMock(spec=SourceIntelligenceClient)
    candidate_card = SourceCandidate(file="ProductCard.tsx", component="ProductCard", element="img", score=100, sourceRange=SourceRange(start=SourceLocation(line=2, column=10)))
    candidate_header = SourceCandidate(file="Header.tsx", component="Header", element="button", score=100, sourceRange=SourceRange(start=SourceLocation(line=2, column=10)))
    
    async def fake_map_source(req):
        if "button" in req.runtimeEvidence.ruleId:
            return SourceMappingResult(status="EXACT_MATCH", candidates=[candidate_header])
        return SourceMappingResult(status="EXACT_MATCH", candidates=[candidate_card])

    mock_source_intel.map_source = AsyncMock(side_effect=fake_map_source)

    mock_orchestrator = MagicMock(spec=MasterOrchestrator)

    # Finding 1: VERIFIED
    diff1 = "--- a/ProductCard.tsx\n+++ b/ProductCard.tsx\n@@ -1,3 +1,3 @@\n export function ProductCard() {\n-  return <img src='/hero.png' />;\n+  return <img src='/hero.png' alt='Hero' />;\n }\n"
    res1 = RemediationWorkflowResult(
        workflow_id="wf_1", target_rule="image-alt", repository_identity=repo_path, commit_sha=base_sha, final_status="VERIFIED",
        patch_candidate=PatchCandidate(patch_id="p1", plan_id="pl1", base_commit_sha=base_sha, status="GENERATED", files_changed=["ProductCard.tsx"], unified_diff=diff1, rationale="alt"),
        finding=Finding(source=Source.AXE, category=Category.ACCESSIBILITY, rule_id="image-alt", title="Alt", description="Alt", severity=Severity.CRITICAL, selectors=["img"], html_snippets=["<img />"]),
        source_mapping_result=SourceMappingResult(status="EXACT_MATCH", candidates=[candidate_card]),
        patch_plan=PatchPlan(plan_id="pl1", repository_identity=repo_path, commit_sha=base_sha, target=PatchTarget(file_path="ProductCard.tsx", component_name="ProductCard", element_type="img", start_line=2, end_line=2), intent=RemediationIntent(rule_id="image-alt", description="alt", violating_html="<img />", root_cause="alt", instruction="alt"), constraints=PatchConstraint(allowed_files=["ProductCard.tsx"], forbid_dependency_changes=True, forbid_css_changes=True, forbid_api_changes=True, max_lines_changed=50)),
        validation_result=PatchValidationResult(status="VALID", patch_id="p1", plan_id="pl1", base_commit_sha=base_sha, checks=[ValidationCheck(name="Check", status="PASS", message="Valid")]),
        sandbox_result=SandboxVerificationResult(status="VERIFIED", patch_id="p1", plan_id="pl1", target_rule="image-alt", baseline_finding=FindingIdentity(rule_id="image-alt", selectors=["img"]), verification_reason="0 violations")
    )

    # Finding 2: NOT_VERIFIED (Sandbox rejected)
    res2 = RemediationWorkflowResult(
        workflow_id="wf_2", target_rule="button-name", repository_identity=repo_path, commit_sha=base_sha, final_status="FAILED",
        failure_stage="SANDBOX_VERIFICATION", error_message="Violation persisted in sandbox",
        finding=Finding(source=Source.AXE, category=Category.ACCESSIBILITY, rule_id="button-name", title="Btn", description="Btn", severity=Severity.SERIOUS, selectors=["button"], html_snippets=["<button />"]),
        source_mapping_result=SourceMappingResult(status="EXACT_MATCH", candidates=[candidate_header]),
        patch_plan=PatchPlan(plan_id="pl2", repository_identity=repo_path, commit_sha=base_sha, target=PatchTarget(file_path="Header.tsx", component_name="Header", element_type="button", start_line=2, end_line=2), intent=RemediationIntent(rule_id="button-name", description="btn", violating_html="<btn />", root_cause="btn", instruction="btn"), constraints=PatchConstraint(allowed_files=["Header.tsx"], forbid_dependency_changes=True, forbid_css_changes=True, forbid_api_changes=True, max_lines_changed=50)),
        validation_result=PatchValidationResult(status="VALID", patch_id="p2", plan_id="pl2", base_commit_sha=base_sha, checks=[ValidationCheck(name="Check", status="PASS", message="Valid")]),
        sandbox_result=SandboxVerificationResult(status="NOT_VERIFIED", patch_id="p2", plan_id="pl2", target_rule="button-name", baseline_finding=FindingIdentity(rule_id="button-name", selectors=["button"]), verification_reason="Violation remained")
    )

    async def fake_run_remediation(finding, repo_url, commit_sha, workflow_id=None, snapshot=None, cleanup_snapshot=True):
        if finding.rule_id == "image-alt":
            return res1
        return res2

    mock_orchestrator.run_remediation_workflow = AsyncMock(side_effect=fake_run_remediation)

    engine = RemediationQueueEngine(
        repo_acquirer=mock_acquirer,
        source_intel=mock_source_intel,
        orchestrator=mock_orchestrator,
    )

    raw_findings = [res1.finding, res2.finding]
    queue = engine.create_queue_from_findings(repo_path, base_sha, raw_findings)

    batch_report = await engine.run_queue(queue, max_retries_per_finding=0)

    # Finding 1 verified, Finding 2 failed
    assert batch_report.aggregate_status == BatchStatus.PARTIALLY_VERIFIED
    assert batch_report.verified_count == 1
    assert batch_report.failed_count == 1
    assert queue.findings[0].status == FindingStatus.VERIFIED
    assert queue.findings[1].status == FindingStatus.NOT_VERIFIED


@pytest.mark.asyncio
async def test_queue_ast_line_drift_blocked(mock_repo):
    repo_path, base_sha = mock_repo

    mock_acquirer = MagicMock(spec=RepositoryAcquirer)
    mock_acquirer.acquire.return_value = SourceSnapshot(
        local_path=repo_path,
        commit_sha=base_sha,
        repository_identity=repo_path
    )

    # Source intelligence returns AMBIGUOUS
    mock_source_intel = MagicMock(spec=SourceIntelligenceClient)
    mock_source_intel.map_source = AsyncMock(return_value=SourceMappingResult(
        status="AMBIGUOUS",
        candidates=[]
    ))

    mock_orchestrator = MagicMock(spec=MasterOrchestrator)

    engine = RemediationQueueEngine(
        repo_acquirer=mock_acquirer,
        source_intel=mock_source_intel,
        orchestrator=mock_orchestrator,
    )

    raw_finding = Finding(
        source=Source.AXE,
        category=Category.ACCESSIBILITY,
        rule_id="image-alt",
        title="Images missing alt",
        description="Fix image-alt",
        severity=Severity.CRITICAL,
        selectors=["img.ambiguous"],
        html_snippets=["<img />"]
    )

    queue = engine.create_queue_from_findings(repo_path, base_sha, [raw_finding])
    batch_report = await engine.run_queue(queue)

    assert batch_report.aggregate_status == BatchStatus.NONE_VERIFIED
    assert queue.findings[0].status == FindingStatus.BLOCKED
    assert "AMBIGUOUS" in (queue.findings[0].block_reason or "")
