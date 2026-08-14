import pytest
import uuid
import json
from engine.orchestrator.models import RemediationWorkflowResult
from engine.orchestrator.report_builder import RemediationReportBuilder
from engine.models import Finding
from engine.models.cluster import Cluster
from engine.source_intelligence.models import SourceMappingResult, SourceCandidate, SourceRange, SourceLocation
from engine.models.patch_plan import PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
from engine.models.patch_plan import PatchCandidate
from engine.models.patch_validation import PatchValidationResult, ValidationCheck
from engine.models.sandbox_verification import SandboxVerificationResult, FindingIdentity

def test_report_builder_success():
    finding = Finding(
        source="axe",
        category="accessibility",
        rule_id="image-alt",
        title="Images must have alt text",
        description="Missing alt attribute",
        severity="critical",
        selectors=["img.logo"]
    )
    
    cluster = Cluster(
        cluster_id=str(uuid.uuid4()),
        rule_id="image-alt",
        title="Images must have alt text",
        category="accessibility",
        severity="critical",
        instance_count=1,
        impact="critical",
        affected_selectors=["img.logo"],
        representative_snippet="<img class='logo' src='logo.png'>",
        likely_root_cause="Missing alt text on logo image"
    )
    
    mapping_res = SourceMappingResult(
        status="MATCHED",
        candidates=[
            SourceCandidate(
                file="src/App.tsx",
                component="App",
                element="img",
                score=100,
                sourceRange=SourceRange(
                    start=SourceLocation(line=10, column=5)
                )
            )
        ]
    )
    
    plan = PatchPlan(
        plan_id=str(uuid.uuid4()),
        repository_identity="https://github.com/org/repo",
        commit_sha="abcdef123456",
        target=PatchTarget(
            file_path="src/App.tsx",
            component_name="App",
            element_type="img",
            start_line=10,
            end_line=30
        ),
        intent=RemediationIntent(
            rule_id="image-alt",
            description="Fix alt text",
            violating_html="<img class='logo' src='logo.png'>",
            root_cause="Missing alt text",
            instruction="Add alt text"
        ),
        constraints=PatchConstraint(allowed_files=["src/App.tsx"])
    )
    
    patch_candidate = PatchCandidate(
        patch_id=str(uuid.uuid4()),
        plan_id=plan.plan_id,
        base_commit_sha="abcdef123456",
        unified_diff="--- src/App.tsx\n+++ src/App.tsx\n@@ -10,1 +10,1 @@\n-<img class='logo' src='logo.png'>\n+<img class='logo' src='logo.png' alt='Company Logo'>",
        rationale="Added descriptive alt text to the company logo.",
        status="GENERATED",
        files_changed=["src/App.tsx"]
    )
    
    validation_result = PatchValidationResult(
        patch_id=patch_candidate.patch_id,
        plan_id=plan.plan_id,
        base_commit_sha="abcdef123456",
        status="VALID",
        checks=[
            ValidationCheck(name="Syntax Check", status="PASS", message="TypeScript compiled successfully")
        ]
    )
    
    sandbox_result = SandboxVerificationResult(
        status="VERIFIED",
        patch_id=patch_candidate.patch_id,
        plan_id=plan.plan_id,
        target_rule="image-alt",
        baseline_finding=FindingIdentity(rule_id="image-alt", selectors=["img.logo"]),
        verification_reason="The violation disappeared after the patch."
    )
    
    workflow_result = RemediationWorkflowResult(
        workflow_id=str(uuid.uuid4()),
        target_rule="image-alt",
        repository_identity="https://github.com/org/repo",
        commit_sha="abcdef123456",
        final_status="VERIFIED"
    )
    workflow_result.finding = finding
    workflow_result.cluster = cluster
    workflow_result.source_mapping_result = mapping_res
    workflow_result.patch_plan = plan
    workflow_result.patch_candidate = patch_candidate
    workflow_result.validation_result = validation_result
    workflow_result.sandbox_result = sandbox_result
    
    report = RemediationReportBuilder.build(workflow_result)
    
    # Assertions
    assert report.identity.repository == "https://github.com/org/repo"
    assert report.finding.rule_id == "image-alt"
    assert report.root_cause.description == "Missing alt text on logo image"
    assert report.source_location.file == "src/App.tsx"
    assert report.source_location.match_status == "MATCHED"
    assert report.patch.rationale == "Added descriptive alt text to the company logo."
    assert "--- src/App.tsx" in report.patch.unified_diff
    assert report.validation.status == "VALID"
    assert report.validation.checks[0].name == "Syntax Check"
    assert report.sandbox_execution.status == "VERIFIED"
    assert report.before_after.before_status == "VIOLATION_PRESENT"
    assert report.before_after.after_status == "VIOLATION_RESOLVED"
    assert report.final_status == "VERIFIED"

    # Test JSON Serialization
    report_json = report.model_dump_json()
    parsed_json = json.loads(report_json)
    assert parsed_json["final_status"] == "VERIFIED"
    assert "--- src/App.tsx" in parsed_json["patch"]["unified_diff"]
    # Check that secrets don't accidentally leak (assuming no secrets were inserted)
    assert "token" not in report_json.lower()

def test_report_builder_ambiguous_source():
    workflow_result = RemediationWorkflowResult(
        workflow_id=str(uuid.uuid4()),
        target_rule="image-alt",
        repository_identity="https://github.com/org/repo",
        commit_sha="abcdef123456",
        final_status="FAILED",
        source_mapping_status="AMBIGUOUS",
        failure_stage="SOURCE_MAPPING_AMBIGUOUS",
        error_message="Multiple matches found"
    )
    
    finding = Finding(
        source="axe", category="accessibility", rule_id="image-alt",
        title="alt", description="Missing alt", severity="minor", selectors=["img"]
    )
    workflow_result.finding = finding
    
    report = RemediationReportBuilder.build(workflow_result)
    assert report.final_status == "FAILED"
    assert report.failure_stage == "SOURCE_MAPPING_AMBIGUOUS"
    assert report.source_location.match_status == "AMBIGUOUS"
    assert report.patch is None
    assert report.sandbox_execution is None
