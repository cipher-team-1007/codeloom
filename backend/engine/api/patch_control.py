"""
FastAPI Router for Developer Patch Review Control.
Exposes endpoints for ACCEPT, EDIT, REJECT, DEFER, REOPEN, REVALIDATE, BATCH DECISION, and PR ELIGIBILITY.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from engine.models.patch_plan import DeveloperDecision, PatchCandidate
from engine.ai.patch_control import patch_control_service, PatchControlError
from engine.storage.sqlite_store import store

logger = logging.getLogger("codeloom.api.patch_control")
router = APIRouter(prefix="/api/v1/patch-plans", tags=["patch-control"])


class RejectRequest(BaseModel):
    reason: Optional[str] = Field(default=None, description="Rejection reason")
    comment: Optional[str] = Field(default=None, description="Optional developer explanation")


class DeferRequest(BaseModel):
    comment: Optional[str] = Field(default=None, description="Optional developer explanation")


class EditPatchRequest(BaseModel):
    after_code: str = Field(description="Developer-edited AFTER code")
    comment: Optional[str] = Field(default=None, description="Optional edit explanation")
    # Extra immutable fields included in body by mistake MUST BE IGNORED BY BACKEND
    file_path: Optional[str] = None
    commit_sha: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    source_fingerprint: Optional[str] = None


class BatchDecisionRequest(BaseModel):
    plan_id: str = Field(alias="planId")
    candidate_ids: List[str] = Field(alias="candidateIds")
    decision: str
    reason: Optional[str] = None
    comment: Optional[str] = None

    class Config:
        populate_by_name = True


@router.post("/{plan_id}/candidates/{candidate_id}/accept")
async def accept_candidate(plan_id: str, candidate_id: str):
    """
    Accepts a patch candidate. Direct transition from REJECTED is blocked (requires REOPEN).
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    try:
        updated = patch_control_service.accept_candidate(candidate)
        store.save_patch_candidate(updated)
        return {"status": "success", "candidate": updated.model_dump()}
    except PatchControlError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plan_id}/candidates/{candidate_id}/reject")
async def reject_candidate(plan_id: str, candidate_id: str, req: Optional[RejectRequest] = Body(None)):
    """
    Rejects a patch candidate with optional reason and comment.
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    reason = req.reason if req else None
    comment = req.comment if req else None

    updated = patch_control_service.reject_candidate(candidate, reason=reason, comment=comment)
    store.save_patch_candidate(updated)
    return {"status": "success", "candidate": updated.model_dump()}


@router.post("/{plan_id}/candidates/{candidate_id}/defer")
async def defer_candidate(plan_id: str, candidate_id: str, req: Optional[DeferRequest] = Body(None)):
    """
    Defers a patch candidate.
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    comment = req.comment if req else None
    updated = patch_control_service.defer_candidate(candidate, comment=comment)
    store.save_patch_candidate(updated)
    return {"status": "success", "candidate": updated.model_dump()}


@router.post("/{plan_id}/candidates/{candidate_id}/reopen")
async def reopen_candidate(plan_id: str, candidate_id: str):
    """
    Reopens a REJECTED or DEFERRED candidate back to PENDING.
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    try:
        updated = patch_control_service.reopen_candidate(candidate)
        store.save_patch_candidate(updated)
        return {"status": "success", "candidate": updated.model_dump()}
    except PatchControlError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plan_id}/candidates/{candidate_id}/edit")
async def edit_candidate(plan_id: str, candidate_id: str, req: EditPatchRequest = Body(...)):
    """
    Applies developer edit to AFTER code.
    Creates a new PatchRevision and invalidates previous validation/verification.
    Ignores any attempts to mutate immutable target fields (file_path, commit_sha, etc.).
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    plan = store.get_patch_plan(plan_id)
    if not plan:
        # Fallback plan mock if plan object isn't saved separately
        from engine.models.patch_plan import PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
        plan = PatchPlan(
            plan_id=plan_id,
            repository_identity=candidate.base_commit_sha,
            commit_sha=candidate.base_commit_sha,
            target=PatchTarget(file_path=candidate.files_changed[0] if candidate.files_changed else "file.tsx", element_type="code", start_line=1),
            intent=RemediationIntent(rule_id="manual", root_cause="Developer edit", instruction="Apply developer edit"),
            constraints=PatchConstraint(allowed_files=candidate.files_changed or ["file.tsx"])
        )

    # Note: Immutable target fields in req (req.file_path, req.commit_sha) are EXPLICITLY IGNORED.
    result = patch_control_service.edit_candidate(candidate, plan=plan, new_after_code=req.after_code, comment=req.comment)
    store.save_patch_candidate(candidate)
    return result


@router.post("/{plan_id}/candidates/{candidate_id}/validate")
async def validate_candidate(plan_id: str, candidate_id: str):
    """
    Revalidates a patch candidate's latest revision.
    """
    candidate = store.get_patch_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Patch candidate '{candidate_id}' not found.")

    plan = store.get_patch_plan(plan_id)
    if not plan:
        from engine.models.patch_plan import PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
        plan = PatchPlan(
            plan_id=plan_id,
            repository_identity=candidate.base_commit_sha,
            commit_sha=candidate.base_commit_sha,
            target=PatchTarget(file_path=candidate.files_changed[0] if candidate.files_changed else "file.tsx", element_type="code", start_line=1),
            intent=RemediationIntent(rule_id="manual", root_cause="Revalidation", instruction="Revalidate patch"),
            constraints=PatchConstraint(allowed_files=candidate.files_changed or ["file.tsx"])
        )

    is_valid, status_str = patch_control_service.revalidate_candidate(candidate, plan=plan)
    store.save_patch_candidate(candidate)
    return {
        "status": "success",
        "isValid": is_valid,
        "validationStatus": status_str,
        "candidate": candidate.model_dump()
    }


@router.get("/{plan_id}/pr-eligibility")
async def get_pr_eligibility(plan_id: str):
    """
    Returns the authoritative plan-level PR eligibility summary.
    """
    candidates = store.get_patch_candidates_by_plan(plan_id)
    summary = patch_control_service.get_plan_pr_eligibility_summary(candidates)
    return summary


@router.post("/batch-decision")
async def batch_decision(req: BatchDecisionRequest = Body(...)):
    """
    Processes batch decisions independently per candidate.
    Returns: { "updated": [...], "failed": [ { "candidateId": "...", "reason": "..." } ] }
    """
    candidates = store.get_patch_candidates_by_plan(req.plan_id)
    candidate_map = {c.patch_id: c for c in candidates}

    result = patch_control_service.process_batch_decision(
        plan_id=req.plan_id,
        candidate_map=candidate_map,
        candidate_ids=req.candidate_ids,
        decision=req.decision,
        reason=req.reason,
        comment=req.comment
    )

    # Persist updated candidates
    for cid in result.get("updated", []):
        if cid in candidate_map:
            store.save_patch_candidate(candidate_map[cid])

    return result
