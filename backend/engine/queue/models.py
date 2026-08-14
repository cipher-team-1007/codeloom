from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class FindingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class QueueStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchStatus(str, Enum):
    ALL_VERIFIED = "ALL_VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NONE_VERIFIED = "NONE_VERIFIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CanonicalFinding(BaseModel):
    """
    Canonical unit of accessibility work enqueued into a RemediationQueue.
    """
    finding_id: str
    rule_id: str
    category: str = "accessibility"
    severity: str = "serious"
    title: str
    description: str
    selectors: List[str] = Field(default_factory=list)
    html_snippets: List[str] = Field(default_factory=list)
    instance_count: int = 1
    source_matches: List[Dict[str, Any]] = Field(default_factory=list)
    source_file: Optional[str] = None
    source_component: Optional[str] = None
    status: FindingStatus = FindingStatus.DISCOVERED
    retry_count: int = 0
    remediation_workflow_id: Optional[str] = None
    report_id: Optional[str] = None
    error_message: Optional[str] = None
    block_reason: Optional[str] = None


class RemediationQueue(BaseModel):
    """
    Sequential queue orchestrating the execution of multiple CanonicalFindings.
    """
    queue_id: str
    repository_url: str
    base_commit_sha: str
    current_working_sha: str
    findings: List[CanonicalFinding] = Field(default_factory=list)
    current_index: int = 0
    total_findings: int = 0
    verified_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    blocked_count: int = 0
    status: QueueStatus = QueueStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    reports: Dict[str, str] = Field(default_factory=dict)  # finding_id -> workflow_id


class RemediationBatchReport(BaseModel):
    """
    Higher-level aggregation report summarizing multi-finding queue execution.
    Individual RemediationReports remain authoritative for verification.
    """
    batch_id: str
    queue_id: str
    repository: str
    base_commit_sha: str
    final_working_sha: str
    aggregate_status: BatchStatus
    total_findings: int
    verified_count: int
    failed_count: int
    skipped_count: int
    blocked_count: int
    findings: List[CanonicalFinding]
    reports: Dict[str, Any] = Field(default_factory=dict)  # finding_id -> serialized RemediationReport
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
