import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from engine.models import Finding
from engine.queue.models import (
    RemediationQueue,
    RemediationBatchReport,
    QueueStatus,
    BatchStatus,
    CanonicalFinding,
)
from engine.queue.remediation_queue import RemediationQueueEngine

from engine.github.publisher import store_authoritative_batch_report

logger = logging.getLogger("codeloom.api.queues")

router = APIRouter(prefix="/api/v1/queues", tags=["queues"])

_active_queues: Dict[str, RemediationQueue] = {}
_completed_batch_reports: Dict[str, RemediationBatchReport] = {}
_queue_engine = RemediationQueueEngine()


class CreateQueueRequest(BaseModel):
    repository_url: str
    base_commit_sha: str = "main"
    findings: List[Any] = Field(default_factory=list)
    async_mode: bool = True
    max_retries_per_finding: int = 1


class QueueResponse(BaseModel):
    queue_id: str
    status: str
    total_findings: int
    verified_count: int
    failed_count: int
    current_index: int
    findings: List[CanonicalFinding] = Field(default_factory=list)
    batch_report: Optional[RemediationBatchReport] = None


async def _run_queue_background(queue: RemediationQueue, max_retries: int):
    try:
        report = await _queue_engine.run_queue(queue, max_retries_per_finding=max_retries)
        _completed_batch_reports[queue.queue_id] = report
        store_authoritative_batch_report(report)
    except Exception as e:
        logger.error(f"[{queue.queue_id}] Background queue execution failed: {e}", exc_info=True)


@router.post("", response_model=QueueResponse)
async def create_and_run_queue(request: CreateQueueRequest, background_tasks: BackgroundTasks):
    """
    Creates a new sequential remediation queue from raw accessibility findings.
    - Synchronous (default): executes all findings sequentially and returns final batch report.
    - Asynchronous (async_mode=True): starts queue in background and returns active queue status.
    """
    import uuid
    normalized_findings = []
    for item in request.findings:
        if isinstance(item, Finding):
            normalized_findings.append(item)
        elif isinstance(item, dict):
            rule = item.get("rule_id") or item.get("ruleId") or "wcag-rule"
            title = item.get("title") or item.get("description") or f"Violation of {rule}"
            desc = item.get("description") or title
            selectors = item.get("selectors") or []
            if isinstance(selectors, str):
                selectors = [selectors]
            snippets = item.get("html_snippets") or item.get("html_context") or []
            if isinstance(snippets, str):
                snippets = [snippets]
            
            f_obj = Finding(
                id=item.get("id") or item.get("finding_id") or f"f_{uuid.uuid4().hex[:8]}",
                rule_id=rule,
                title=title,
                description=desc,
                selectors=selectors,
                html_snippets=snippets
            )
            normalized_findings.append(f_obj)

    if not normalized_findings:
        normalized_findings = [
            Finding(
                rule_id="image-alt",
                title="Images must have alt text",
                description="Hero brand image requires descriptive alt attribute",
                selectors=["img.hero-logo"],
                html_snippets=['<img class="hero-logo" src="logo.png">']
            )
        ]

    queue = _queue_engine.create_queue_from_findings(
        repository_url=request.repository_url,
        base_commit_sha=request.base_commit_sha,
        raw_findings=normalized_findings
    )
    _active_queues[queue.queue_id] = queue


    if request.async_mode:
        background_tasks.add_task(_run_queue_background, queue, request.max_retries_per_finding)
        live_report = RemediationBatchReport(
            batch_id=f"batch_{queue.queue_id}",
            queue_id=queue.queue_id,
            repository=queue.repository_url,
            base_commit_sha=queue.base_commit_sha,
            final_working_sha=queue.current_working_sha or queue.base_commit_sha,
            aggregate_status=BatchStatus.NONE_VERIFIED,
            total_findings=queue.total_findings,
            verified_count=queue.verified_count,
            failed_count=queue.failed_count,
            skipped_count=queue.skipped_count,
            blocked_count=queue.blocked_count,
            findings=queue.findings,
            reports={},
        )
        return QueueResponse(
            queue_id=queue.queue_id,
            status=queue.status.value,
            total_findings=queue.total_findings,
            verified_count=queue.verified_count,
            failed_count=queue.failed_count,
            current_index=queue.current_index,
            findings=queue.findings,
            batch_report=live_report,
        )

    # Synchronous mode
    batch_report = await _queue_engine.run_queue(queue, max_retries_per_finding=request.max_retries_per_finding)
    _completed_batch_reports[queue.queue_id] = batch_report
    store_authoritative_batch_report(batch_report)

    return QueueResponse(
        queue_id=queue.queue_id,
        status=queue.status.value,
        total_findings=queue.total_findings,
        verified_count=queue.verified_count,
        failed_count=queue.failed_count,
        current_index=queue.current_index,
        findings=queue.findings,
        batch_report=batch_report,
    )


@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue_status(queue_id: str):
    """Retrieves current queue progress and completed batch report."""
    queue = _active_queues.get(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail=f"Remediation queue '{queue_id}' not found.")

    batch_report = _completed_batch_reports.get(queue_id)
    if not batch_report and queue:
        batch_report = RemediationBatchReport(
            batch_id=f"batch_{queue.queue_id}",
            queue_id=queue.queue_id,
            repository=queue.repository_url,
            base_commit_sha=queue.base_commit_sha,
            final_working_sha=queue.current_working_sha or queue.base_commit_sha,
            aggregate_status=BatchStatus.NONE_VERIFIED,
            total_findings=queue.total_findings,
            verified_count=queue.verified_count,
            failed_count=queue.failed_count,
            skipped_count=queue.skipped_count,
            blocked_count=queue.blocked_count,
            findings=queue.findings,
            reports={},
        )

    return QueueResponse(
        queue_id=queue.queue_id,
        status=queue.status.value,
        total_findings=queue.total_findings,
        verified_count=queue.verified_count,
        failed_count=queue.failed_count,
        current_index=queue.current_index,
        findings=queue.findings,
        batch_report=batch_report,
    )
