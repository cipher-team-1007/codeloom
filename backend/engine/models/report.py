from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class ReportIdentity(BaseModel):
    workflow_id: str
    repository: str
    commit_sha: str
    plan_id: Optional[str] = None
    patch_id: Optional[str] = None

class ReportFinding(BaseModel):
    rule_id: str
    description: str
    impact: str
    target_selector: str

class ReportRootCause(BaseModel):
    description: str

class ReportSourceLocation(BaseModel):
    file: str
    start_line: int
    end_line: int
    component: Optional[str] = None
    match_status: str

class ReportPatch(BaseModel):
    patch_id: str
    files_changed: List[str]
    unified_diff: str
    rationale: str
    patch_fingerprint: Optional[str] = None

class ReportValidationCheck(BaseModel):
    name: str
    status: Literal["PASS", "FAIL", "SKIPPED", "WARN"]
    message: str

class ReportValidation(BaseModel):
    status: str
    checks: List[ReportValidationCheck]

class ReportSandbox(BaseModel):
    status: str
    verification_reason: str

class ReportBeforeAfter(BaseModel):
    rule_id: str
    target_selector: str
    before_status: str
    after_status: str

class RemediationReport(BaseModel):
    identity: ReportIdentity
    finding: ReportFinding
    root_cause: Optional[ReportRootCause] = None
    source_location: Optional[ReportSourceLocation] = None
    patch: Optional[ReportPatch] = None
    validation: Optional[ReportValidation] = None
    sandbox_execution: Optional[ReportSandbox] = None
    before_after: Optional[ReportBeforeAfter] = None
    final_status: str
    failure_stage: Optional[str] = None
    error_message: Optional[str] = None
