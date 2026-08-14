from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RemediationStage(str, Enum):
    INITIALIZING = "INITIALIZING"
    REPOSITORY_ACQUISITION = "REPOSITORY_ACQUISITION"
    ROOT_CAUSE_CLUSTERING = "ROOT_CAUSE_CLUSTERING"
    SOURCE_INTELLIGENCE = "SOURCE_INTELLIGENCE"
    PATCH_PLANNING = "PATCH_PLANNING"
    PATCH_GENERATION = "PATCH_GENERATION"
    PATCH_VALIDATION = "PATCH_VALIDATION"
    SANDBOX_VERIFICATION = "SANDBOX_VERIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TelemetryEventType(str, Enum):
    WORKFLOW_QUEUED = "WORKFLOW_QUEUED"
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_PROGRESS = "STAGE_PROGRESS"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    STAGE_FAILED = "STAGE_FAILED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"


class RemediationEvent(BaseModel):
    """
    Structured event streamed to subscribers via SSE.
    Guaranteed to be sanitized and contain zero secrets or absolute server paths.
    """
    event_id: str
    workflow_id: str
    sequence: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: TelemetryEventType
    stage: RemediationStage
    stage_index: int = Field(ge=0, le=7)
    total_stages: int = 7
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    final_status: Optional[str] = None
    error_code: Optional[str] = None


class RemediationJob(BaseModel):
    """
    In-memory state model representing an active or completed remediation execution.
    """
    workflow_id: str
    repository_url: str
    target_commit_sha: str
    target_rule_id: str
    status: JobStatus = JobStatus.QUEUED
    current_stage: RemediationStage = RemediationStage.INITIALIZING
    stage_index: int = 0
    total_stages: int = 7
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_stage: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    final_status: Optional[str] = None
    report_summary: Optional[Dict[str, Any]] = None
