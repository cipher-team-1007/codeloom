import pytest
from fastapi.testclient import TestClient
from engine.api.app import app

client = TestClient(app)


def test_queue_api_404_on_nonexistent():
    response = client.get("/api/v1/queues/q_nonexistent123")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_queue_api_async_mode():
    payload = {
        "repository_url": "https://github.com/octocat/Hello-World",
        "base_commit_sha": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        "findings": [
            {
                "source": "axe",
                "category": "accessibility",
                "rule_id": "image-alt",
                "title": "Image missing alt",
                "description": "Add alt",
                "severity": "critical",
                "selectors": ["img.hero"],
                "html_snippets": ["<img />"]
            },
            {
                "source": "axe",
                "category": "accessibility",
                "rule_id": "button-name",
                "title": "Button name",
                "description": "Add label",
                "severity": "serious",
                "selectors": ["button.menu"],
                "html_snippets": ["<button />"]
            }
        ],
        "async_mode": True
    }

    response = client.post("/api/v1/queues", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "queue_id" in data
    assert data["total_findings"] == 2
    assert data["status"] in ("CREATED", "RUNNING")

    # Fetch status via GET
    get_res = client.get(f"/api/v1/queues/{data['queue_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["queue_id"] == data["queue_id"]
