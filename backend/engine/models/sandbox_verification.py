from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class FindingIdentity(BaseModel):
    rule_id: str
    selectors: List[str]

class SandboxVerificationResult(BaseModel):
    status: Literal["VERIFIED", "NOT_VERIFIED", "SANDBOX_START_FAILED", "SANDBOX_TIMEOUT", "SCAN_FAILED"]
    patch_id: str
    plan_id: str
    
    baseline_finding: Optional[FindingIdentity] = None
    after_finding: Optional[FindingIdentity] = None
    target_rule: str
    
    application_url: Optional[str] = None
    execution_metadata: dict = Field(default_factory=dict)
    verification_reason: str
