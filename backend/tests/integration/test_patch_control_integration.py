"""
Integration test suite for Developer Patch Review Control (Step 3).
Executes a 4-candidate plan scenario (A: Accepted+Verified, B: Rejected, C: Developer edited+Validated+Verified+Accepted, D: Deferred).
Verifies that the backend authoritatively filters and includes ONLY A + C in the final Pull Request payload!
"""
import pytest
from engine.models.patch_plan import (
    PatchPlan,
    PatchTarget,
    RemediationIntent,
    PatchConstraint,
    PatchCandidate,
    DeveloperDecision,
    PatchValidationStatus,
    PatchVerificationStatus
)
from engine.ai.patch_control import PatchControlService


def test_4_candidate_pr_filtering_integration():
    service = PatchControlService()

    plan = PatchPlan(
        plan_id="plan-integration-999",
        repository_identity="https://github.com/cipher-team-1007/codeloom.git",
        commit_sha="4ce5133bbcfd8e2dcf5b85f0915e71186947ed01",
        target=PatchTarget(file_path="src/App.tsx", element_type="main", start_line=1),
        intent=RemediationIntent(rule_id="a11y-suite", root_cause="Multi-candidate test", instruction="Fix components"),
        constraints=PatchConstraint(allowed_files=["src/App.tsx"])
    )

    # Candidate A: AI generated, developer accepts, validation passes, verification passes
    cA = PatchCandidate(patch_id="cand-A", plan_id=plan.plan_id, base_commit_sha=plan.commit_sha, files_changed=["src/components/Header.tsx"])
    service.create_initial_revision(cA, "<header />", "<header role='banner' />", "diff A")
    service.accept_candidate(cA)
    cA.revisions[-1].validation_status = PatchValidationStatus.VALID
    cA.revisions[-1].verification_status = PatchVerificationStatus.VERIFIED

    # Candidate B: AI generated, developer rejects
    cB = PatchCandidate(patch_id="cand-B", plan_id=plan.plan_id, base_commit_sha=plan.commit_sha, files_changed=["src/components/Footer.tsx"])
    service.create_initial_revision(cB, "<footer />", "<footer role='contentinfo' />", "diff B")
    service.reject_candidate(cB, reason="Too broad", comment="Will fix manually later")

    # Candidate C: AI generated, developer edits -> rev 2 created, validation passes, verification passes, developer accepts
    import tempfile, os
    from engine.repository.models import SourceSnapshot

    tmp_dir = tempfile.mkdtemp()
    target_file = os.path.join(tmp_dir, "src", "components", "ProductCard.tsx")
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w") as f:
        f.write("<img />\n")

    snapshot = SourceSnapshot(local_path=tmp_dir, commit_sha=plan.commit_sha, repository_identity=plan.repository_identity)

    cC = PatchCandidate(patch_id="cand-C", plan_id=plan.plan_id, base_commit_sha=plan.commit_sha, files_changed=["src/components/ProductCard.tsx"])
    service.create_initial_revision(cC, "<img />\n", "<img alt='Product' />\n", "diff C1")
    service.edit_candidate(cC, plan=plan, new_after_code="<img alt='Detailed Product Image' />\n", comment="Enhanced alt text")
    assert len(cC.revisions) == 2
    assert cC.revisions[0].invalidated_at is not None
    assert cC.revisions[1].validation_status == PatchValidationStatus.NOT_RUN
    service.revalidate_candidate(cC, plan=plan, snapshot=snapshot)
    cC.revisions[-1].verification_status = PatchVerificationStatus.VERIFIED
    service.accept_candidate(cC)

    # Candidate D: AI generated, developer defers
    cD = PatchCandidate(patch_id="cand-D", plan_id=plan.plan_id, base_commit_sha=plan.commit_sha, files_changed=["src/components/Nav.tsx"])
    service.create_initial_revision(cD, "<nav />", "<nav aria-label='Main' />", "diff D")
    service.defer_candidate(cD, comment="Postpone to next sprint")

    # Run Authoritative Backend PR Filter
    all_candidates = [cA, cB, cC, cD]
    eligible_candidates = service.get_plan_pr_eligible_candidates(all_candidates)
    eligible_ids = [c.patch_id for c in eligible_candidates]

    assert len(eligible_candidates) == 2
    assert "cand-A" in eligible_ids
    assert "cand-C" in eligible_ids
    assert "cand-B" not in eligible_ids
    assert "cand-D" not in eligible_ids

    # Run Plan Eligibility Summary
    summary = service.get_plan_pr_eligibility_summary(all_candidates)
    assert summary["eligible"] is True
    assert summary["eligibleCount"] == 2
    assert summary["excludedCount"] == 2
    assert summary["excludedReasons"]["rejected"] == 1
    assert summary["excludedReasons"]["deferred"] == 1
