import pytest
from pydantic import ValidationError
from engine.models.patch_plan import (
    PatchTarget,
    RemediationIntent,
    PatchConstraint,
    PatchPlan,
    PatchGenerationRequest,
    PatchCandidate
)

def test_valid_patch_plan():
    target = PatchTarget(
        file_path="src/components/ProductCard.tsx",
        component_name="ProductCard",
        element_type="img",
        start_line=15
    )
    intent = RemediationIntent(
        rule_id="image-alt",
        root_cause="Image missing alternative text",
        instruction="Add descriptive alt text based on surrounding context."
    )
    constraints = PatchConstraint(
        allowed_files=["src/components/ProductCard.tsx"],
        forbid_dependency_changes=True,
        forbid_css_changes=True,
        forbid_api_changes=True,
        max_lines_changed=10
    )
    plan = PatchPlan(
        plan_id="plan-123",
        repository_identity="https://github.com/test/repo.git",
        commit_sha="abcd1234abcd1234abcd1234abcd1234abcd1234",
        target=target,
        intent=intent,
        constraints=constraints
    )
    assert plan.plan_id == "plan-123"
    assert plan.target.file_path == "src/components/ProductCard.tsx"
    assert plan.constraints.max_lines_changed == 10

def test_missing_source_revision():
    with pytest.raises(ValidationError) as exc:
        PatchPlan(
            plan_id="plan-123",
            repository_identity="https://github.com/test/repo.git",
            # missing commit_sha
            target=PatchTarget(file_path="a", element_type="b", start_line=1),
            intent=RemediationIntent(rule_id="a", root_cause="b", instruction="c"),
            constraints=PatchConstraint(allowed_files=["a"])
        )
    assert "commit_sha" in str(exc.value)

def test_missing_target():
    with pytest.raises(ValidationError) as exc:
        PatchPlan(
            plan_id="plan-123",
            repository_identity="https://github.com/test/repo.git",
            commit_sha="abc",
            # missing target
            intent=RemediationIntent(rule_id="a", root_cause="b", instruction="c"),
            constraints=PatchConstraint(allowed_files=["a"])
        )
    assert "target" in str(exc.value)

def test_invalid_status_for_candidate():
    with pytest.raises(ValidationError) as exc:
        PatchCandidate(
            patch_id="patch-123",
            plan_id="plan-123",
            base_commit_sha="abc",
            status="APPLIED", # invalid status, must be GENERATED, REJECTED, or INVALID
            files_changed=["a"],
            unified_diff="diff",
            rationale="rationale"
        )
    assert "status" in str(exc.value)
    
def test_valid_candidate():
    candidate = PatchCandidate(
        patch_id="patch-123",
        plan_id="plan-123",
        base_commit_sha="abc",
        status="GENERATED",
        files_changed=["a"],
        unified_diff="diff",
        rationale="rationale"
    )
    assert candidate.status == "GENERATED"
