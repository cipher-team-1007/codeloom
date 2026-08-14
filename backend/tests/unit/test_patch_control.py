"""
Unit test suite for Developer Patch Review Control (Step 3).
Verifies Accept, Reject, Defer, Reopen, Edit revision creation, Edit invalidation metadata,
Revalidation, Syntax/Stale/Conflict rejection, PR eligibility guards, and Batch decision processing.
"""
import pytest
from datetime import datetime
from engine.models.patch_plan import (
    PatchPlan,
    PatchTarget,
    RemediationIntent,
    PatchConstraint,
    PatchCandidate,
    DeveloperDecision,
    CandidateLifecycleStatus,
    PatchValidationStatus,
    PatchVerificationStatus
)
from engine.ai.patch_control import PatchControlService, PatchControlError


@pytest.fixture
def sample_plan():
    return PatchPlan(
        plan_id="plan-test-101",
        repository_identity="https://github.com/cipher-team-1007/codeloom.git",
        commit_sha="abcd1234abcd1234abcd1234abcd1234abcd1234",
        target=PatchTarget(
            file_path="src/components/Header.tsx",
            component_name="Header",
            element_type="img",
            start_line=84,
            end_line=91
        ),
        intent=RemediationIntent(
            rule_id="image-alt",
            root_cause="Image element missing alt attribute",
            instruction="Add alt text"
        ),
        constraints=PatchConstraint(
            allowed_files=["src/components/Header.tsx"],
            max_lines_changed=10
        )
    )


@pytest.fixture
def patch_service():
    return PatchControlService()


@pytest.fixture
def candidate_generator(patch_service, sample_plan):
    def _create(patch_id="patch-001", before="<img src='logo.png' />\n", after="<img src='logo.png' alt='Logo' />\n"):
        cand = PatchCandidate(
            patch_id=patch_id,
            plan_id=sample_plan.plan_id,
            base_commit_sha=sample_plan.commit_sha,
            files_changed=["src/components/Header.tsx"],
            rationale="Added alt text for image accessibility"
        )
        patch_service.create_initial_revision(cand, before_code=before, after_code=after, unified_diff="--- a/src/components/Header.tsx\n+++ b/src/components/Header.tsx\n@@ -1,1 +1,1 @@\n-<img src='logo.png' />\n+<img src='logo.png' alt='Logo' />\n")
        return cand
    return _create


def test_1_accept_candidate(patch_service, candidate_generator):
    cand = candidate_generator()
    assert cand.decision == DeveloperDecision.PENDING
    updated = patch_service.accept_candidate(cand)
    assert updated.decision == DeveloperDecision.ACCEPTED
    assert updated.status == CandidateLifecycleStatus.REVIEW


def test_2_reject_candidate(patch_service, candidate_generator):
    cand = candidate_generator()
    updated = patch_service.reject_candidate(cand, reason="Too broad", comment="Fix manual")
    assert updated.decision == DeveloperDecision.REJECTED
    assert updated.status == CandidateLifecycleStatus.REJECTED
    assert updated.rejection_reason == "Too broad"
    assert updated.comment == "Fix manual"
    assert updated.rejected_at is not None


def test_3_defer_candidate(patch_service, candidate_generator):
    cand = candidate_generator()
    updated = patch_service.defer_candidate(cand, comment="Review next sprint")
    assert updated.decision == DeveloperDecision.DEFERRED
    assert updated.status == CandidateLifecycleStatus.DEFERRED
    assert updated.deferred_at is not None


def test_4_edit_candidate_creates_revision_2(patch_service, sample_plan, candidate_generator):
    cand = candidate_generator()
    assert len(cand.revisions) == 1
    assert cand.revisions[0].revision_number == 1

    res = patch_service.edit_candidate(cand, plan=sample_plan, new_after_code="<img src='logo.png' alt='Brand Logo' />", comment="Refined alt text")
    assert res["candidateId"] == cand.patch_id
    assert res["revision"]["revisionNumber"] == 2
    assert len(cand.revisions) == 2
    assert cand.after_code == "<img src='logo.png' alt='Brand Logo' />"


def test_5_edit_invalidates_previous_validation_and_verification(patch_service, sample_plan, candidate_generator):
    cand = candidate_generator()
    cand.revisions[0].validation_status = PatchValidationStatus.VALID
    cand.revisions[0].verification_status = PatchVerificationStatus.VERIFIED

    patch_service.edit_candidate(cand, plan=sample_plan, new_after_code="<img src='logo.png' alt='Edited' />")

    # Check previous revision metadata
    rev1 = cand.revisions[0]
    assert rev1.invalidated_at is not None
    assert rev1.invalidated_reason == "Developer modified after_code"

    # Check new revision status
    rev2 = cand.revisions[1]
    assert rev2.validation_status == PatchValidationStatus.NOT_RUN
    assert rev2.verification_status == PatchVerificationStatus.NOT_RUN

    # Check PR eligibility is cleared
    is_el, reason = patch_service.check_candidate_pr_eligibility(cand)
    assert not is_el
    assert "PENDING" in reason or "VALID" in reason or "ACCEPTED" in reason


def test_6_revalidation_succeeds_for_valid_edited_patch(patch_service, sample_plan, candidate_generator):
    import tempfile, os
    from engine.repository.models import SourceSnapshot

    tmp_dir = tempfile.mkdtemp()
    target_file = os.path.join(tmp_dir, "src", "components", "Header.tsx")
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w") as f:
        f.write("<img src='logo.png' />\n")

    snapshot = SourceSnapshot(local_path=tmp_dir, commit_sha=sample_plan.commit_sha, repository_identity=sample_plan.repository_identity)

    cand = candidate_generator()
    patch_service.edit_candidate(cand, plan=sample_plan, new_after_code="<img src='logo.png' alt='Header Logo' />\n")

    is_valid, status_str = patch_service.revalidate_candidate(cand, plan=sample_plan, snapshot=snapshot)
    assert is_valid
    assert status_str == "VALID"
    assert cand.revisions[-1].validation_status == PatchValidationStatus.VALID


def test_7_reopen_rejected_or_deferred_candidate(patch_service, candidate_generator):
    cand = candidate_generator()
    patch_service.reject_candidate(cand, reason="Wrong match")
    assert cand.decision == DeveloperDecision.REJECTED

    # Direct accept should fail
    with pytest.raises(PatchControlError) as exc:
        patch_service.accept_candidate(cand)
    assert "Direct transition to ACCEPTED is blocked" in str(exc.value)

    # Reopen should succeed
    reopened = patch_service.reopen_candidate(cand)
    assert reopened.decision == DeveloperDecision.PENDING
    assert reopened.rejection_reason is None

    # Defer and reopen
    patch_service.defer_candidate(cand)
    assert cand.decision == DeveloperDecision.DEFERRED
    reopened2 = patch_service.reopen_candidate(cand)
    assert reopened2.decision == DeveloperDecision.PENDING


def test_8_pr_eligibility_guard_strict(patch_service, candidate_generator):
    cand = candidate_generator()
    patch_service.accept_candidate(cand)
    rev = cand.revisions[-1]

    # Validated but not verified -> ineligible
    rev.validation_status = PatchValidationStatus.VALID
    rev.verification_status = PatchVerificationStatus.NOT_RUN
    is_el, _ = patch_service.check_candidate_pr_eligibility(cand)
    assert not is_el

    # Validated + Verified -> ELIGIBLE!
    rev.verification_status = PatchVerificationStatus.VERIFIED
    is_el, msg = patch_service.check_candidate_pr_eligibility(cand)
    assert is_el
    assert "eligible" in msg.lower()

    # Conflict -> ineligible
    cand.has_conflict = True
    is_el, _ = patch_service.check_candidate_pr_eligibility(cand)
    assert not is_el


def test_9_plan_pr_eligibility_summary(patch_service, candidate_generator):
    c1 = candidate_generator("patch-1")
    patch_service.accept_candidate(c1)
    c1.revisions[-1].validation_status = PatchValidationStatus.VALID
    c1.revisions[-1].verification_status = PatchVerificationStatus.VERIFIED

    c2 = candidate_generator("patch-2")
    patch_service.reject_candidate(c2, reason="Too broad")

    c3 = candidate_generator("patch-3")
    patch_service.defer_candidate(c3)

    summary = patch_service.get_plan_pr_eligibility_summary([c1, c2, c3])
    assert summary["eligible"] is True
    assert summary["eligibleCount"] == 1
    assert summary["excludedCount"] == 2
    assert summary["excludedReasons"]["rejected"] == 1
    assert summary["excludedReasons"]["deferred"] == 1


def test_10_batch_decision_independent_processing(patch_service, candidate_generator):
    c1 = candidate_generator("patch-1")
    c2 = candidate_generator("patch-2")

    cmap = {"patch-1": c1, "patch-2": c2}
    res = patch_service.process_batch_decision(
        plan_id="plan-101",
        candidate_map=cmap,
        candidate_ids=["patch-1", "patch-2", "patch-nonexistent"],
        decision="ACCEPTED"
    )

    assert "patch-1" in res["updated"]
    assert "patch-2" in res["updated"]
    assert len(res["failed"]) == 1
    assert res["failed"][0]["candidateId"] == "patch-nonexistent"
    assert c1.decision == DeveloperDecision.ACCEPTED
    assert c2.decision == DeveloperDecision.ACCEPTED
