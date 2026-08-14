import pytest
import asyncio
from fastapi.testclient import TestClient
from engine.api.app import app
from engine.telemetry.event_bus import global_event_bus
from engine.telemetry.models import RemediationStage, TelemetryEventType, JobStatus

client = TestClient(app)


def test_sse_endpoint_404_on_missing_job():
    response = client.get("/api/v1/remediations/nonexistent-wid-12345/events")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_job_status_endpoint_lookup():
    job = global_event_bus.create_job(
        workflow_id="wf-api-test-01",
        repository_url="https://github.com/octocat/Hello-World",
        target_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        target_rule_id="image-alt",
    )
    response = client.get("/api/v1/remediations/wf-api-test-01")
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "wf-api-test-01"
    assert data["status"] == "QUEUED"
    assert data["target_rule_id"] == "image-alt"


def test_sse_stream_historical_and_terminal_events():
    wid = "wf-sse-stream-02"
    global_event_bus.create_job(
        workflow_id=wid,
        repository_url="https://github.com/octocat/Hello-World",
        target_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        target_rule_id="image-alt",
    )

    global_event_bus.publish_event(
        workflow_id=wid,
        event_type=TelemetryEventType.STAGE_STARTED,
        stage=RemediationStage.REPOSITORY_ACQUISITION,
        stage_index=1,
        message="Acquiring repository..."
    )
    global_event_bus.publish_event(
        workflow_id=wid,
        event_type=TelemetryEventType.WORKFLOW_COMPLETED,
        stage=RemediationStage.COMPLETED,
        stage_index=7,
        message="Workflow complete.",
        final_status="VERIFIED"
    )

    response = client.get(f"/api/v1/remediations/{wid}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    content = response.text
    assert ": connected" in content
    assert "event: WORKFLOW_QUEUED" in content
    assert "event: STAGE_STARTED" in content
    assert "event: WORKFLOW_COMPLETED" in content
    assert "id: 1" in content
    assert "id: 2" in content
    assert "id: 3" in content


def test_sse_stream_last_event_id_replay_via_header():
    wid = "wf-sse-stream-03"
    global_event_bus.create_job(
        workflow_id=wid,
        repository_url="https://github.com/octocat/Hello-World",
        target_commit_sha="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        target_rule_id="image-alt",
    )

    global_event_bus.publish_event(
        workflow_id=wid,
        event_type=TelemetryEventType.STAGE_STARTED,
        stage=RemediationStage.ROOT_CAUSE_CLUSTERING,
        stage_index=2,
        message="Clustering findings..."
    )
    global_event_bus.publish_event(
        workflow_id=wid,
        event_type=TelemetryEventType.WORKFLOW_COMPLETED,
        stage=RemediationStage.COMPLETED,
        stage_index=7,
        message="Finished.",
        final_status="VERIFIED"
    )

    # Replay with Last-Event-ID: 2 (should skip sequence 1 and 2, return 3)
    response = client.get(
        f"/api/v1/remediations/{wid}/events",
        headers={"Last-Event-ID": "2"}
    )
    assert response.status_code == 200
    content = response.text

    assert "event: WORKFLOW_COMPLETED" in content
    assert "id: 3" in content
    assert "id: 1" not in content  # Skipped because sequence <= 2


def test_async_workflow_initiation():
    payload = {
        "repository_url": "https://github.com/octocat/Hello-World",
        "commit_sha": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        "finding": {
            "source": "axe",
            "category": "accessibility",
            "rule_id": "image-alt",
            "title": "Image missing alt attribute",
            "description": "Image elements must have an alternate text attribute.",
            "severity": "critical",
            "selectors": ["img.hero"],
            "html_snippets": ["<img src='/hero.png' />"]
        },
        "async_mode": True
    }

    response = client.post("/api/v1/remediations/workflow", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "workflow_id" in data
    assert data["status"] == "QUEUED"
    assert f"/api/v1/remediations/{data['workflow_id']}/events" in data["events_url"]
    assert f"/api/v1/remediations/{data['workflow_id']}" in data["status_url"]
