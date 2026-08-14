import json
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine.orchestrator.master_workflow import MasterOrchestrator
from engine.orchestrator.report_builder import RemediationReportBuilder
from engine.models import Finding
from engine.models.report import RemediationReport
from engine.telemetry.event_bus import global_event_bus
from engine.telemetry.models import JobStatus, RemediationEvent, RemediationJob
from engine.github.publisher import (
    store_authoritative_remediation,
    get_authoritative_remediation,
)

logger = logging.getLogger("codeloom.api.remediations")

router = APIRouter(prefix="/api/v1/remediations", tags=["remediations"])


class RemediationRequest(BaseModel):
    finding: Optional[Finding] = None
    repository_url: str
    commit_sha: str
    rule_id: Optional[str] = None
    target_selector: Optional[str] = None
    description: Optional[str] = None
    workflow_id: Optional[str] = None
    async_mode: bool = False

    def get_finding(self) -> Finding:
        if self.finding:
            return self.finding
        from engine.models import Source, Category, Severity
        return Finding(
            id=f"f_{uuid.uuid4().hex[:8]}",
            source=Source.AXE,
            category=Category.ACCESSIBILITY,
            rule_id=self.rule_id or "image-alt",
            title=self.description or f"Violation of {self.rule_id}",
            description=self.description or f"Remediation target for {self.rule_id}",
            severity=Severity.CRITICAL,
            selectors=[self.target_selector] if self.target_selector else ["body"],
            html_snippets=[f"<{self.target_selector or 'element'}>"]
        )


class WorkflowAsyncResponse(BaseModel):
    workflow_id: str
    status: str = "QUEUED"
    events_url: str
    status_url: str


async def _run_workflow_background(request: RemediationRequest, workflow_id: str):
    """Background execution runner for asynchronous remediation workflows."""
    orchestrator = MasterOrchestrator(event_bus=global_event_bus)
    try:
        target_finding = request.get_finding()
        result = await orchestrator.run_remediation_workflow(
            finding=target_finding,
            repo_url=request.repository_url,
            commit_sha=request.commit_sha,
            workflow_id=workflow_id,
        )
        report = RemediationReportBuilder.build(result)
        store_authoritative_remediation(report)
        job = global_event_bus.get_job(workflow_id)
        if job:
            job.report_summary = report.model_dump()
    except Exception as e:
        logger.error(f"[{workflow_id}] Background workflow failed: {e}", exc_info=True)


@router.post("/workflow")
async def run_remediation_workflow(
    request: RemediationRequest,
    async_mode: Optional[bool] = Query(False, description="Run workflow asynchronously with SSE telemetry")
):
    """
    Run full remediation workflow.
    - Synchronous mode (default): returns RemediationReport directly.
    - Asynchronous mode (`async_mode=true`): returns 202 Accepted with SSE events_url.
    """
    is_async = request.async_mode or async_mode
    wid = request.workflow_id or str(uuid.uuid4())
    target_finding = request.get_finding()

    if is_async:
        global_event_bus.create_job(
            workflow_id=wid,
            repository_url=request.repository_url,
            target_commit_sha=request.commit_sha,
            target_rule_id=target_finding.rule_id,
        )
        asyncio.create_task(_run_workflow_background(request, wid))
        return WorkflowAsyncResponse(
            workflow_id=wid,
            status="QUEUED",
            events_url=f"/api/v1/remediations/{wid}/events",
            status_url=f"/api/v1/remediations/{wid}",
        )

    # Synchronous Execution (Backward Compatible)
    orchestrator = MasterOrchestrator(event_bus=global_event_bus)
    try:
        result = await orchestrator.run_remediation_workflow(
            finding=target_finding,
            repo_url=request.repository_url,
            commit_sha=request.commit_sha,
            workflow_id=wid,
        )
        report = RemediationReportBuilder.build(result)
        store_authoritative_remediation(report)
        return report
    except Exception as e:
        logger.error(f"Remediation workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}/events")
async def stream_remediation_events(
    workflow_id: str,
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID")
):
    """
    Streams live and historical remediation progress events via Server-Sent Events (SSE).
    Supports reconnection and event replay using standard `Last-Event-ID`.
    """
    job = global_event_bus.get_job(workflow_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Remediation job '{workflow_id}' not found.")

    last_seq = None
    if last_event_id:
        try:
            last_seq = int(last_event_id)
        except ValueError:
            last_seq = None

    async def event_generator():
        try:
            # Yield initial connection comment
            yield ": connected\n\n"
            
            async for event in global_event_bus.subscribe(workflow_id, last_event_id=last_seq):
                if await request.is_disconnected():
                    break
                event_data = event.model_dump_json()
                yield f"id: {event.sequence}\nevent: {event.event_type.value}\ndata: {event_data}\n\n"

        except asyncio.CancelledError:
            logger.info(f"[{workflow_id}] Client disconnected from SSE stream.")
        except Exception as e:
            logger.error(f"[{workflow_id}] Error in SSE stream: {e}")
            error_payload = json.dumps({"error": "STREAM_ERROR", "message": "An error occurred while streaming telemetry."})
            yield f"event: ERROR\ndata: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{workflow_id}")
async def get_remediation_job(workflow_id: str):
    """
    Retrieves the current job lifecycle status and completed report summary if available.
    """
    job = global_event_bus.get_job(workflow_id)
    report = get_authoritative_remediation(workflow_id)

    if job:
        if report and not job.report_summary:
            job.report_summary = report.model_dump()
        return job

    if report:
        return {
            "workflow_id": workflow_id,
            "status": report.final_status,
            "report_summary": report.model_dump(),
            "report": report.model_dump(),
        }

    raise HTTPException(status_code=404, detail=f"Remediation job '{workflow_id}' not found.")
