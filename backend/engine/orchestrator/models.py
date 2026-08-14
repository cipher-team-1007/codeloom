import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from engine.models import Finding, Cluster
from engine.repository.models import RepositoryCoordinate, SourceSnapshot
from engine.source_intelligence.models import SourceMappingResult
from engine.models.patch_plan import PatchPlan, PatchCandidate
from engine.models.patch_validation import PatchValidationResult
from engine.models.sandbox_verification import SandboxVerificationResult

class RemediationWorkflowResult(BaseModel):
    workflow_id: str
    target_rule: str
    repository_identity: str
    commit_sha: str
    
    # Traceability
    cluster_id: Optional[str] = None
    source_mapping_status: str = "PENDING"
    mapped_file: Optional[str] = None
    plan_id: Optional[str] = None
    patch_id: Optional[str] = None
    
    patch_validation_status: str = "PENDING"
    sandbox_verification_status: str = "PENDING"
    final_status: str = "FAILED"
    failure_stage: Optional[str] = None
    error_message: Optional[str] = None

    # Internal Evidence
    finding: Optional[Finding] = None
    cluster: Optional[Cluster] = None
    source_mapping_result: Optional[SourceMappingResult] = None
    patch_plan: Optional[PatchPlan] = None
    patch_candidate: Optional[PatchCandidate] = None
    validation_result: Optional[PatchValidationResult] = None
    sandbox_result: Optional[SandboxVerificationResult] = None
