import re
import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, AsyncGenerator
from datetime import datetime, timezone

from engine.telemetry.models import (
    JobStatus,
    RemediationStage,
    TelemetryEventType,
    RemediationEvent,
    RemediationJob,
)

logger = logging.getLogger("codeloom.telemetry.event_bus")

# Sanitization regex patterns
TOKEN_PATTERNS = [
    re.compile(r'ghp_[a-zA-Z0-9]{20,}', re.IGNORECASE),
    re.compile(r'gho_[a-zA-Z0-9]{20,}', re.IGNORECASE),
    re.compile(r'github_pat_[a-zA-Z0-9_]{20,}', re.IGNORECASE),
    re.compile(r'sk-[a-zA-Z0-9]{20,}', re.IGNORECASE),
    re.compile(r'AIzaSy[a-zA-Z0-9_-]{20,}', re.IGNORECASE),
    re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]+', re.IGNORECASE),
]

PATH_PATTERNS = [
    re.compile(r'[a-zA-Z]:\\[^\s:;,"]+', re.IGNORECASE),  # Windows absolute paths
    re.compile(r'/(?:Users|home|tmp|private|var)/[^\s:;,"]+', re.IGNORECASE),  # Unix absolute paths
]


def sanitize_text(text: str) -> str:
    """Sanitizes text by redacting sensitive tokens, credentials, and local filesystem paths."""
    if not isinstance(text, str):
        return text

    sanitized = text
    for pattern in TOKEN_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

    for pattern in PATH_PATTERNS:
        sanitized = pattern.sub("[WORKSPACE_PATH]", sanitized)

    return sanitized


SENSITIVE_KEYS = {
    "token", "access_token", "github_token", "oauth_token",
    "secret", "client_secret", "password", "api_key",
    "private_key", "encryption_key", "authorization"
}


def sanitize_metadata(data: Any) -> Any:
    """Recursively sanitizes dictionary or list metadata values."""
    if isinstance(data, dict):
        return {
            k: sanitize_metadata(v) for k, v in data.items()
            if k.lower() not in SENSITIVE_KEYS
        }
    elif isinstance(data, list):
        return [sanitize_metadata(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    else:
        return data


class EventBus:
    """
    In-memory asynchronous event bus managing active remediation jobs,
    event ring buffers, monotonic sequence generation, and SSE subscribers.
    """

    def __init__(self, ring_buffer_size: int = 50, max_jobs: int = 1000):
        self.ring_buffer_size = ring_buffer_size
        self.max_jobs = max_jobs
        
        self._jobs: Dict[str, RemediationJob] = {}
        self._sequences: Dict[str, int] = {}
        self._event_buffers: Dict[str, List[RemediationEvent]] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    def create_job(
        self,
        workflow_id: str,
        repository_url: str,
        target_commit_sha: str,
        target_rule_id: str,
    ) -> RemediationJob:
        """Initializes a new RemediationJob and allocates an event ring buffer."""
        self._cleanup_old_jobs()
        job = RemediationJob(
            workflow_id=workflow_id,
            repository_url=sanitize_text(repository_url),
            target_commit_sha=target_commit_sha,
            target_rule_id=target_rule_id,
            status=JobStatus.QUEUED,
            current_stage=RemediationStage.INITIALIZING,
            stage_index=0,
            total_stages=7,
        )
        self._jobs[workflow_id] = job
        self._sequences[workflow_id] = 0
        self._event_buffers[workflow_id] = []
        self._subscribers[workflow_id] = set()

        # Emit initial queue event
        self.publish_event(
            workflow_id=workflow_id,
            event_type=TelemetryEventType.WORKFLOW_QUEUED,
            stage=RemediationStage.INITIALIZING,
            stage_index=0,
            message="Remediation workflow queued.",
            metadata={"repository": job.repository_url, "rule_id": target_rule_id}
        )
        return job

    def get_job(self, workflow_id: str) -> Optional[RemediationJob]:
        """Retrieves current job state if it exists."""
        return self._jobs.get(workflow_id)

    def publish_event(
        self,
        workflow_id: str,
        event_type: TelemetryEventType,
        stage: RemediationStage,
        stage_index: int,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        final_status: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> Optional[RemediationEvent]:
        """
        Publishes a sanitized event with a monotonic sequence number, stores it in the
        workflow ring buffer, updates job status, and broadcasts to active subscribers.
        """
        if workflow_id not in self._jobs:
            logger.warning(f"Attempted to publish event for unknown workflow_id: {workflow_id}")
            return None

        # Monotonic sequence generation
        current_seq = self._sequences.get(workflow_id, 0) + 1
        self._sequences[workflow_id] = current_seq

        event_id = f"evt-{workflow_id[:8]}-{current_seq:03d}"
        sanitized_msg = sanitize_text(message)
        sanitized_meta = sanitize_metadata(metadata or {})

        event = RemediationEvent(
            event_id=event_id,
            workflow_id=workflow_id,
            sequence=current_seq,
            event_type=event_type,
            stage=stage,
            stage_index=stage_index,
            total_stages=7,
            message=sanitized_msg,
            metadata=sanitized_meta,
            final_status=final_status,
            error_code=error_code,
        )

        # Store in ring buffer
        buf = self._event_buffers[workflow_id]
        buf.append(event)
        if len(buf) > self.ring_buffer_size:
            buf.pop(0)

        # Update Job state
        job = self._jobs[workflow_id]
        job.current_stage = stage
        job.stage_index = stage_index
        now_iso = datetime.now(timezone.utc).isoformat()

        if event_type == TelemetryEventType.WORKFLOW_STARTED and not job.started_at:
            job.status = JobStatus.RUNNING
            job.started_at = now_iso
        elif event_type == TelemetryEventType.STAGE_FAILED:
            job.failure_stage = stage.value
            job.error_code = error_code
            job.error_message = sanitized_msg
        elif event_type == TelemetryEventType.WORKFLOW_COMPLETED:
            job.status = JobStatus.COMPLETED
            job.completed_at = now_iso
            job.final_status = final_status
        elif event_type == TelemetryEventType.WORKFLOW_FAILED:
            job.status = JobStatus.FAILED
            job.completed_at = now_iso
            if not job.failure_stage or stage != RemediationStage.FAILED:
                job.failure_stage = stage.value
            if error_code:
                job.error_code = error_code
            if sanitized_msg:
                job.error_message = sanitized_msg

        # Broadcast to active subscriber queues
        subs = self._subscribers.get(workflow_id, set())
        for q in subs:
            try:
                q.put_nowait(event)
            except Exception as e:
                logger.error(f"Failed to put event into subscriber queue: {e}")

        return event

    async def subscribe(
        self,
        workflow_id: str,
        last_event_id: Optional[int] = None
    ) -> AsyncGenerator[RemediationEvent, None]:
        """
        Yields historical events (filtered by last_event_id) followed by live events
        until a terminal event (WORKFLOW_COMPLETED or WORKFLOW_FAILED) is reached.
        """
        if workflow_id not in self._jobs:
            return

        job = self._jobs[workflow_id]
        buf = self._event_buffers.get(workflow_id, [])

        # 1. Replay historical events
        historical_events = []
        if last_event_id is not None:
            historical_events = [evt for evt in buf if evt.sequence > last_event_id]
        else:
            historical_events = list(buf)

        for evt in historical_events:
            yield evt

        # If job is already in a terminal state, we are done
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return

        # 2. Subscribe for live events
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[workflow_id].add(queue)

        try:
            while True:
                # Wait for next event
                event: RemediationEvent = await queue.get()
                yield event

                if event.event_type in (
                    TelemetryEventType.WORKFLOW_COMPLETED,
                    TelemetryEventType.WORKFLOW_FAILED,
                ):
                    break
        finally:
            subs = self._subscribers.get(workflow_id)
            if subs and queue in subs:
                subs.remove(queue)

    def _cleanup_old_jobs(self):
        """Prunes completed or failed jobs if memory limits are exceeded."""
        if len(self._jobs) <= self.max_jobs:
            return

        # Remove oldest completed/failed jobs
        finished_ids = [
            wid for wid, j in self._jobs.items()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        
        # Remove up to half of the finished jobs
        for wid in finished_ids[: max(1, len(finished_ids) // 2)]:
            self._jobs.pop(wid, None)
            self._sequences.pop(wid, None)
            self._event_buffers.pop(wid, None)
            self._subscribers.pop(wid, None)


# Default global instance for FastAPI application
global_event_bus = EventBus()
