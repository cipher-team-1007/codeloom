from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class DeveloperDecision(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class CandidateLifecycleStatus(str, Enum):
    GENERATED = "GENERATED"
    REVIEW = "REVIEW"
    VALIDATING = "VALIDATING"
    READY = "READY"
    APPLIED = "APPLIED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"
    INVALID = "INVALID"


class PatchTarget(BaseModel):
    """
    Identifies WHERE the change should happen in the source code.
    Based strictly on verified source intelligence, NOT runtime DOM.
    """
    file_path: str = Field(description="Relative path to the source file within the repository")
    component_name: Optional[str] = Field(default=None, description="Name of the React/Vue component if applicable")
    element_type: str = Field(description="Type of the JSX/HTML element (e.g., 'button', 'img')")
    start_line: int = Field(description="Starting line of the target element in the source file")
    end_line: Optional[int] = Field(default=None, description="Ending line of the target element, if known")


class RemediationIntent(BaseModel):
    """
    Describes WHAT kind of accessibility fix is required semantically.
    """
    rule_id: str = Field(description="The accessibility rule violated (e.g., 'image-alt')")
    root_cause: str = Field(description="Plaintext explanation of the source-level issue")
    instruction: str = Field(description="Instruction for the future AI generator (e.g., 'Add descriptive alt text based on context')")


class PatchConstraint(BaseModel):
    """
    Describes constraints and boundaries for the AI Patch Generator.
    Prevents unbounded file modifications and arbitrary refactoring.
    """
    allowed_files: List[str] = Field(description="Strict list of files the patch is permitted to modify")
    forbid_dependency_changes: bool = Field(default=True, description="Do not allow changes to package.json")
    forbid_css_changes: bool = Field(default=True, description="Do not allow changes to CSS files unless explicitly allowed")
    forbid_api_changes: bool = Field(default=True, description="Do not change component props or public APIs")
    max_lines_changed: int = Field(default=50, description="Hard limit on the number of source lines the AI can modify")


class PatchPlan(BaseModel):
    """
    A precise, constrained description of the source-code change 
    that CodeLoom wants a future Patch Generator to attempt.
    """
    plan_id: str
    repository_identity: str = Field(description="URL or unique identifier of the source repository")
    commit_sha: str = Field(description="Verified commit SHA that this plan applies to")
    
    target: PatchTarget
    intent: RemediationIntent
    constraints: PatchConstraint
    source_context: Optional[str] = Field(default=None, description="Extracted source code snippet around target element for the LLM")


class PatchGenerationRequest(BaseModel):
    """
    Input contract for the future AI Patch Generator.
    Combines the deterministic plan with necessary context.
    """
    plan: PatchPlan
    source_context: str = Field(description="Actual source code snippet around the target for the LLM to inspect")


class PatchValidationStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    INVALID = "INVALID"
    CONFLICT = "CONFLICT"


class PatchVerificationStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REGRESSION = "REGRESSION"


class PatchRevision(BaseModel):
    """
    Represents an individual revision of a patch candidate.
    Created initially by AI, or subsequently when developer edits afterCode.
    """
    revision_id: str
    candidate_id: str
    revision_number: int = 1
    before_code: str = ""
    after_code: str = ""
    unified_diff: str = ""
    created_by: Literal["ai", "developer"] = "ai"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validation_status: PatchValidationStatus = Field(default=PatchValidationStatus.NOT_RUN)
    verification_status: PatchVerificationStatus = Field(default=PatchVerificationStatus.NOT_RUN)
    invalidated_at: Optional[str] = None
    invalidated_reason: Optional[str] = None
    validation_message: Optional[str] = None
    checks: List[Dict[str, Any]] = Field(default_factory=list)


class PatchCandidate(BaseModel):
    """
    Output contract from the AI Patch Generator with Developer Review Control.
    Represents proposed source code changes to be deterministically validated.
    """
    patch_id: str
    plan_id: str
    base_commit_sha: str = Field(description="The commit SHA this patch was generated against")
    
    decision: DeveloperDecision = Field(default=DeveloperDecision.PENDING, description="Developer decision: PENDING, ACCEPTED, REJECTED, DEFERRED")
    status: CandidateLifecycleStatus = Field(default=CandidateLifecycleStatus.GENERATED, description="Lifecycle status")
    
    files_changed: List[str] = Field(default_factory=list, description="Files modified by this candidate")
    unified_diff: str = Field(default="", description="The actual unified diff of the proposed changes")
    rationale: str = Field(default="", description="The AI's explanation for the changes made")
    
    before_code: str = Field(default="", description="Read-only before code")
    after_code: str = Field(default="", description="Editable after code")
    
    revisions: List[PatchRevision] = Field(default_factory=list, description="Historical revisions of this candidate")
    latest_revision_id: Optional[str] = Field(default=None, description="ID of the latest revision")
    
    rejection_reason: Optional[str] = None
    rejected_at: Optional[str] = None
    rejected_by: Optional[str] = None
    deferred_at: Optional[str] = None
    comment: Optional[str] = None
    
    has_conflict: bool = False
    conflict_details: Optional[Dict[str, Any]] = None

