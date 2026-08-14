"""
Patch Control Service.
Manages developer patch decisions (ACCEPT, EDIT, REJECT, DEFER, REOPEN),
patch revision history, edit validation invalidation, and backend PR eligibility guards.
"""
import uuid
import logging
import difflib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from engine.models.patch_plan import (
    PatchPlan,
    PatchCandidate,
    PatchRevision,
    DeveloperDecision,
    CandidateLifecycleStatus,
    PatchValidationStatus,
    PatchVerificationStatus
)
from engine.ai.patch_validator import PatchValidator

logger = logging.getLogger("codeloom.ai.patch_control")


class PatchControlError(Exception):
    """Raised when an illegal patch decision transition or edit operation is attempted."""
    pass


class PatchControlService:
    """
    Authoritative backend service enforcing the developer patch review workflow.
    """

    def __init__(self, validator: Optional[PatchValidator] = None):
        self.validator = validator or PatchValidator()

    def create_initial_revision(self, candidate: PatchCandidate, before_code: str, after_code: str, unified_diff: str) -> PatchRevision:
        """
        Creates the initial (Revision 1) AI-generated revision for a newly created PatchCandidate.
        """
        rev_id = f"rev-{candidate.patch_id}-1"
        revision = PatchRevision(
            revision_id=rev_id,
            candidate_id=candidate.patch_id,
            revision_number=1,
            before_code=before_code,
            after_code=after_code,
            unified_diff=unified_diff,
            created_by="ai",
            validation_status=PatchValidationStatus.NOT_RUN,
            verification_status=PatchVerificationStatus.NOT_RUN
        )
        candidate.before_code = before_code
        candidate.after_code = after_code
        candidate.unified_diff = unified_diff
        candidate.revisions = [revision]
        candidate.latest_revision_id = rev_id
        candidate.decision = DeveloperDecision.PENDING
        candidate.status = CandidateLifecycleStatus.GENERATED
        return revision

    def accept_candidate(self, candidate: PatchCandidate) -> PatchCandidate:
        """
        Transitions candidate to ACCEPTED.
        Blocks direct ACCEPTED transition if candidate is currently REJECTED (requires reopen).
        """
        if candidate.decision == DeveloperDecision.REJECTED:
            raise PatchControlError(
                f"Candidate '{candidate.patch_id}' is REJECTED. Direct transition to ACCEPTED is blocked. Use reopen endpoint."
            )
        
        candidate.decision = DeveloperDecision.ACCEPTED
        if candidate.status in [CandidateLifecycleStatus.GENERATED, CandidateLifecycleStatus.REJECTED, CandidateLifecycleStatus.DEFERRED]:
            candidate.status = CandidateLifecycleStatus.REVIEW
            
        logger.info(f"Patch candidate {candidate.patch_id} ACCEPTED by developer.")
        return candidate

    def reject_candidate(self, candidate: PatchCandidate, reason: Optional[str] = None, comment: Optional[str] = None, user: Optional[str] = None) -> PatchCandidate:
        """
        Transitions candidate to REJECTED.
        Candidate becomes permanently excluded from PRs unless explicitly reopened.
        """
        candidate.decision = DeveloperDecision.REJECTED
        candidate.status = CandidateLifecycleStatus.REJECTED
        candidate.rejection_reason = reason or "Developer rejected patch"
        candidate.rejected_at = datetime.now(timezone.utc).isoformat()
        candidate.rejected_by = user
        candidate.comment = comment
        
        logger.info(f"Patch candidate {candidate.patch_id} REJECTED: reason='{reason}'.")
        return candidate

    def defer_candidate(self, candidate: PatchCandidate, comment: Optional[str] = None) -> PatchCandidate:
        """
        Transitions candidate to DEFERRED.
        Excluded from PR generation until returned to review.
        """
        candidate.decision = DeveloperDecision.DEFERRED
        candidate.status = CandidateLifecycleStatus.DEFERRED
        candidate.deferred_at = datetime.now(timezone.utc).isoformat()
        candidate.comment = comment
        
        logger.info(f"Patch candidate {candidate.patch_id} DEFERRED.")
        return candidate

    def reopen_candidate(self, candidate: PatchCandidate) -> PatchCandidate:
        """
        Reopens a REJECTED or DEFERRED candidate back to PENDING review state.
        Blocks reopening a VERIFIED candidate directly.
        """
        if candidate.decision not in [DeveloperDecision.REJECTED, DeveloperDecision.DEFERRED]:
            raise PatchControlError(f"Candidate '{candidate.patch_id}' is not in REJECTED or DEFERRED state.")
            
        candidate.decision = DeveloperDecision.PENDING
        candidate.status = CandidateLifecycleStatus.REVIEW
        candidate.rejection_reason = None
        candidate.rejected_at = None
        candidate.deferred_at = None
        
        logger.info(f"Patch candidate {candidate.patch_id} REOPENED to PENDING.")
        return candidate

    def edit_candidate(self, candidate: PatchCandidate, plan: PatchPlan, new_after_code: str, comment: Optional[str] = None, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Applies a developer edit to afterCode.
        Creates a new PatchRevision (revision_number = len(revisions) + 1),
        recomputes the unified diff, and EXPLICITLY INVALIDATES previous validation and verification.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # Invalidate previous revision metadata if present
        if candidate.revisions:
            latest_rev = candidate.revisions[-1]
            latest_rev.invalidated_at = now_iso
            latest_rev.invalidated_reason = "Developer modified after_code"

        # Compute new unified diff
        file_path = plan.target.file_path
        before_lines = candidate.before_code.splitlines(keepends=True)
        after_lines = new_after_code.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}"
        ))
        new_diff = "".join(diff_lines)
        if not new_diff and candidate.before_code != new_after_code:
            new_diff = f"--- a/{file_path}\n+++ b/{file_path}\n@@ -1,1 +1,1 @@\n-{candidate.before_code}\n+{new_after_code}\n"

        next_rev_num = len(candidate.revisions) + 1
        new_rev_id = f"rev-{candidate.patch_id}-{next_rev_num}"

        new_revision = PatchRevision(
            revision_id=new_rev_id,
            candidate_id=candidate.patch_id,
            revision_number=next_rev_num,
            before_code=candidate.before_code,
            after_code=new_after_code,
            unified_diff=new_diff,
            created_by="developer",
            created_at=now_iso,
            validation_status=PatchValidationStatus.NOT_RUN,
            verification_status=PatchVerificationStatus.NOT_RUN
        )

        candidate.revisions.append(new_revision)
        candidate.latest_revision_id = new_rev_id
        candidate.after_code = new_after_code
        candidate.unified_diff = new_diff
        candidate.comment = comment

        logger.info(f"Created revision {next_rev_num} for candidate {candidate.patch_id}. Previous validation & verification cleared.")

        rev_dict = new_revision.model_dump()
        rev_dict["revisionNumber"] = next_rev_num
        rev_dict["revisionId"] = new_rev_id
        rev_dict["createdBy"] = new_revision.created_by
        rev_dict["validationStatus"] = str(new_revision.validation_status)
        rev_dict["verificationStatus"] = str(new_revision.verification_status)

        return {
            "candidateId": candidate.patch_id,
            "revision": rev_dict
        }

    def revalidate_candidate(self, candidate: PatchCandidate, plan: PatchPlan, snapshot: Optional[Any] = None) -> Tuple[bool, str]:
        """
        Runs the deterministic validation pipeline on candidate's latest revision.
        """
        if not candidate.revisions:
            latest_rev = self.create_initial_revision(
                candidate,
                before_code=candidate.before_code,
                after_code=candidate.after_code,
                unified_diff=candidate.unified_diff
            )
        else:
            latest_rev = candidate.revisions[-1]

        import tempfile
        from engine.repository.models import SourceSnapshot

        if not snapshot:
            snapshot = SourceSnapshot(
                local_path=tempfile.gettempdir(),
                commit_sha=plan.commit_sha or "0000000000000000000000000000000000000000",
                repository_identity=plan.repository_identity or "https://github.com/test/repo.git"
            )

        validation_result = self.validator.validate(
            candidate=candidate,
            plan=plan,
            snapshot=snapshot
        )

        is_valid = validation_result.status == "VALID"
        latest_rev.validation_status = PatchValidationStatus.VALID if is_valid else PatchValidationStatus.INVALID
        latest_rev.validation_message = f"Validation result: {validation_result.status}"
        latest_rev.checks = [c.model_dump() for c in validation_result.checks]

        if is_valid:
            if candidate.status in [CandidateLifecycleStatus.GENERATED, CandidateLifecycleStatus.INVALID]:
                candidate.status = CandidateLifecycleStatus.READY
        else:
            candidate.status = CandidateLifecycleStatus.INVALID

        val_str = latest_rev.validation_status.value if hasattr(latest_rev.validation_status, "value") else str(latest_rev.validation_status)
        logger.info(f"Revalidated candidate {candidate.patch_id} revision {latest_rev.revision_number}: status={val_str}")
        return is_valid, val_str

    def check_candidate_pr_eligibility(self, candidate: PatchCandidate) -> Tuple[bool, str]:
        """
        Authoritative backend guard enforcing PR eligibility constraints:
        1. decision == ACCEPTED
        2. latest_revision.validation_status in ["VALID", "PASSED"]
        3. latest_revision.verification_status in ["VERIFIED", "PASSED"]
        4. decision NOT in [REJECTED, DEFERRED]
        5. has_conflict == False
        """
        if candidate.decision != DeveloperDecision.ACCEPTED:
            return False, f"Candidate decision is '{candidate.decision}', expected 'ACCEPTED'."

        if not candidate.revisions:
            return False, "Candidate has no revisions."

        latest_rev = candidate.revisions[-1]
        val_status_str = str(latest_rev.validation_status.value if hasattr(latest_rev.validation_status, 'value') else latest_rev.validation_status)
        ver_status_str = str(latest_rev.verification_status.value if hasattr(latest_rev.verification_status, 'value') else latest_rev.verification_status)

        if val_status_str not in ["VALID", "PASSED"]:
            return False, f"Latest revision validation status is '{val_status_str}', expected 'VALID'."

        if ver_status_str not in ["VERIFIED", "PASSED"]:
            return False, f"Latest revision verification status is '{ver_status_str}', expected 'VERIFIED'."

        if candidate.has_conflict:
            return False, "Candidate has unresolved merge conflicts."

        return True, "Candidate is eligible for Pull Request."

    def get_plan_pr_eligible_candidates(self, candidates: List[PatchCandidate]) -> List[PatchCandidate]:
        """
        Calculates the PLAN-level set of PR-eligible candidates.
        Excludes REJECTED, DEFERRED, PENDING, unvalidated, or unverified candidates.
        """
        eligible = []
        for c in candidates:
            is_eligible, _ = self.check_candidate_pr_eligibility(c)
            if is_eligible:
                eligible.append(c)
        return eligible

    def get_plan_pr_eligibility_summary(self, candidates: List[PatchCandidate]) -> Dict[str, Any]:
        """
        Calculates a structured PR eligibility summary for the whole PatchPlan.
        Returns: { "eligible": bool, "eligibleCount": int, "excludedCount": int, "excludedReasons": { "rejected": int, "deferred": int, "unverified": int, "conflict": int } }
        """
        eligible_candidates = self.get_plan_pr_eligible_candidates(candidates)
        eligible_count = len(eligible_candidates)
        total_count = len(candidates)
        excluded_count = total_count - eligible_count

        excluded_reasons = {
            "rejected": 0,
            "deferred": 0,
            "unverified": 0,
            "conflict": 0
        }

        for c in candidates:
            is_el, _ = self.check_candidate_pr_eligibility(c)
            if not is_el:
                if c.decision == DeveloperDecision.REJECTED:
                    excluded_reasons["rejected"] += 1
                elif c.decision == DeveloperDecision.DEFERRED:
                    excluded_reasons["deferred"] += 1
                elif c.has_conflict:
                    excluded_reasons["conflict"] += 1
                else:
                    excluded_reasons["unverified"] += 1

        return {
            "eligible": eligible_count > 0,
            "eligibleCount": eligible_count,
            "excludedCount": excluded_count,
            "excludedReasons": excluded_reasons
        }

    def process_batch_decision(self, plan_id: str, candidate_map: Dict[str, PatchCandidate], candidate_ids: List[str], decision: str, reason: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes batch decisions independently per candidate.
        Returns: { "updated": [...], "failed": [ { "candidateId": "...", "reason": "..." } ] }
        """
        updated = []
        failed = []

        dec_str = str(decision).upper()

        for cid in candidate_ids:
            candidate = candidate_map.get(cid)
            if not candidate:
                failed.append({"candidateId": cid, "reason": f"Candidate '{cid}' not found in plan '{plan_id}'."})
                continue

            try:
                if dec_str == "ACCEPTED":
                    self.accept_candidate(candidate)
                    updated.append(cid)
                elif dec_str == "REJECTED":
                    self.reject_candidate(candidate, reason=reason, comment=comment)
                    updated.append(cid)
                elif dec_str == "DEFERRED":
                    self.defer_candidate(candidate, comment=comment)
                    updated.append(cid)
                else:
                    failed.append({"candidateId": cid, "reason": f"Invalid decision string '{decision}'."})
            except Exception as e:
                failed.append({"candidateId": cid, "reason": str(e)})

        return {
            "updated": updated,
            "failed": failed
        }


# Singleton service instance
patch_control_service = PatchControlService()
