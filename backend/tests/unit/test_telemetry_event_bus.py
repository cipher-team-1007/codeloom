import pytest
import asyncio
from engine.telemetry.models import (
    JobStatus,
    RemediationStage,
    TelemetryEventType,
    RemediationEvent,
    RemediationJob,
)
from engine.telemetry.event_bus import (
    EventBus,
    sanitize_text,
    sanitize_metadata,
)


def test_job_creation():
    bus = EventBus()
    job = bus.create_job(
        workflow_id="wf-test-01",
        repository_url="https://github.com/octocat/Hello-World",
        target_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        target_rule_id="image-alt",
    )
    assert job.workflow_id == "wf-test-01"
    assert job.status == JobStatus.QUEUED
    assert job.current_stage == RemediationStage.INITIALIZING
    assert job.stage_index == 0
    assert job.total_stages == 7
    assert bus.get_job("wf-test-01") is not None


def test_monotonic_sequence_generation():
    bus = EventBus()
    bus.create_job("wf-test-02", "https://github.com/org/repo", "sha123", "image-alt")
    
    # 1 event was generated on creation (WORKFLOW_QUEUED)
    e1 = bus.publish_event(
        "wf-test-02",
        TelemetryEventType.WORKFLOW_STARTED,
        RemediationStage.INITIALIZING,
        0,
        "Workflow started."
    )
    e2 = bus.publish_event(
        "wf-test-02",
        TelemetryEventType.STAGE_STARTED,
        RemediationStage.REPOSITORY_ACQUISITION,
        1,
        "Acquiring repository..."
    )
    e3 = bus.publish_event(
        "wf-test-02",
        TelemetryEventType.STAGE_COMPLETED,
        RemediationStage.REPOSITORY_ACQUISITION,
        1,
        "Acquisition complete."
    )

    assert e1.sequence == 2
    assert e2.sequence == 3
    assert e3.sequence == 4
    assert e1.sequence < e2.sequence < e3.sequence


def test_ring_buffer_eviction():
    bus = EventBus(ring_buffer_size=5)
    bus.create_job("wf-test-03", "https://github.com/org/repo", "sha123", "image-alt")

    for i in range(10):
        bus.publish_event(
            "wf-test-03",
            TelemetryEventType.STAGE_PROGRESS,
            RemediationStage.SOURCE_INTELLIGENCE,
            3,
            f"Step {i}"
        )

    buf = bus._event_buffers["wf-test-03"]
    assert len(buf) == 5
    # Latest events should be in buffer
    assert buf[-1].message == "Step 9"
    assert buf[0].message == "Step 5"


def test_secret_and_path_sanitization():
    raw_message = (
        "Fetching repo using ghp_1234567890abcdefghijklmnopqrstuvwxyz "
        "and key sk-1234567890abcdefghijklmnopqrstuvwxyz at C:\\Users\\secret\\repo"
    )
    sanitized = sanitize_text(raw_message)
    assert "ghp_" not in sanitized
    assert "sk-" not in sanitized
    assert "C:\\Users" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized
    assert "[WORKSPACE_PATH]" in sanitized

    meta = {
        "token": "ghp_supersecrettoken1234567890",
        "api_key": "AIzaSySecretApiKey12345678901234",
        "file": "/home/user/workspace/app.tsx",
        "safe_key": "value"
    }
    sanitized_meta = sanitize_metadata(meta)
    assert "token" not in sanitized_meta
    assert "api_key" not in sanitized_meta
    assert sanitized_meta["safe_key"] == "value"
    assert "/home/user" not in sanitized_meta["file"]
    assert "[WORKSPACE_PATH]" in sanitized_meta["file"]


@pytest.mark.asyncio
async def test_subscription_live_stream():
    bus = EventBus()
    bus.create_job("wf-test-04", "https://github.com/org/repo", "sha123", "image-alt")

    received = []

    async def consumer():
        async for evt in bus.subscribe("wf-test-04"):
            received.append(evt)

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)

    bus.publish_event(
        "wf-test-04",
        TelemetryEventType.STAGE_STARTED,
        RemediationStage.PATCH_GENERATION,
        5,
        "Generating patch..."
    )
    bus.publish_event(
        "wf-test-04",
        TelemetryEventType.WORKFLOW_COMPLETED,
        RemediationStage.COMPLETED,
        7,
        "Completed successfully.",
        final_status="VERIFIED"
    )

    await asyncio.wait_for(task, timeout=2.0)

    event_types = [e.event_type for e in received]
    assert TelemetryEventType.WORKFLOW_QUEUED in event_types
    assert TelemetryEventType.STAGE_STARTED in event_types
    assert TelemetryEventType.WORKFLOW_COMPLETED in event_types

    job = bus.get_job("wf-test-04")
    assert job.status == JobStatus.COMPLETED
    assert job.final_status == "VERIFIED"


@pytest.mark.asyncio
async def test_last_event_id_replay():
    bus = EventBus()
    bus.create_job("wf-test-05", "https://github.com/org/repo", "sha123", "image-alt")

    # Sequence 1 is WORKFLOW_QUEUED
    bus.publish_event("wf-test-05", TelemetryEventType.STAGE_STARTED, RemediationStage.REPOSITORY_ACQUISITION, 1, "S1") # Seq 2
    bus.publish_event("wf-test-05", TelemetryEventType.STAGE_STARTED, RemediationStage.ROOT_CAUSE_CLUSTERING, 2, "S2")   # Seq 3
    bus.publish_event("wf-test-05", TelemetryEventType.WORKFLOW_COMPLETED, RemediationStage.COMPLETED, 7, "Done")       # Seq 4

    # Replay with Last-Event-ID = 2 (should receive sequence 3 and 4)
    replayed = []
    async for evt in bus.subscribe("wf-test-05", last_event_id=2):
        replayed.append(evt)

    assert len(replayed) == 2
    assert replayed[0].sequence == 3
    assert replayed[1].sequence == 4


@pytest.mark.asyncio
async def test_workflow_failed_terminal_event():
    bus = EventBus()
    bus.create_job("wf-test-06", "https://github.com/org/repo", "sha123", "image-alt")

    bus.publish_event(
        "wf-test-06",
        TelemetryEventType.STAGE_FAILED,
        RemediationStage.SOURCE_INTELLIGENCE,
        3,
        "Ambiguous match",
        error_code="SOURCE_MAPPING_AMBIGUOUS"
    )
    bus.publish_event(
        "wf-test-06",
        TelemetryEventType.WORKFLOW_FAILED,
        RemediationStage.FAILED,
        3,
        "Workflow failed at source intelligence.",
        error_code="SOURCE_MAPPING_AMBIGUOUS"
    )

    events = []
    async for evt in bus.subscribe("wf-test-06"):
        events.append(evt)

    assert len(events) == 3
    assert events[-1].event_type == TelemetryEventType.WORKFLOW_FAILED
    
    job = bus.get_job("wf-test-06")
    assert job.status == JobStatus.FAILED
    assert job.failure_stage == "SOURCE_INTELLIGENCE"
    assert job.error_code == "SOURCE_MAPPING_AMBIGUOUS"
