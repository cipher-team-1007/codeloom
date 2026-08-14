from typing import List, Literal
from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    name: str
    status: Literal["PASS", "FAIL", "SKIPPED", "WARN"]
    message: str


class PatchValidationResult(BaseModel):
    patch_id: str
    plan_id: str
    base_commit_sha: str
    
    status: Literal["VALID", "INVALID", "INVALID_DIFF", "CONSTRAINT_VIOLATION", "COMMIT_MISMATCH", "PATCH_APPLY_FAILED", "SYNTAX_ERROR", "COMPILE_ERROR", "PATH_VIOLATION"]
    
    checks: List[ValidationCheck] = Field(default_factory=list)
