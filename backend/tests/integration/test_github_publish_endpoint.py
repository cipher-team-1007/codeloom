import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from engine.api.app import app
from engine.api.github import _auth_manager, _config, _vault, _publisher
from engine.github.models import GitHubCredential, TokenType
from engine.github.publisher import store_authoritative_remediation, compute_patch_fingerprint
from engine.models.report import (
    RemediationReport,
    ReportIdentity,
    ReportFinding,
    ReportRootCause,
    ReportSourceLocation,
    ReportPatch,
    ReportValidation,
    ReportValidationCheck,
    ReportSandbox,
    ReportBeforeAfter,
)

client = TestClient(app)

TEST_BASE_SHA = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
TEST_SESSION = "sess-api-publish-test"

SAMPLE_DIFF = """--- a/src/App.tsx
+++ b/src/App.tsx
@@ -1,3 +1,3 @@
 <div>
-  <button>Click</button>
+  <button aria-label="Submit Form">Click</button>
 </div>
"""

SAMPLE_CODE = """<div>
  <button>Click</button>
</div>
"""

@pytest.fixture(autouse=True)
def setup_environment():
    _config.client_id = "test_client_id"
    _config.client_secret = "test_secret"
    _config.encryption_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    _vault._key_bytes = _vault._derive_key_bytes(_config.encryption_key)
    
    # Store authenticated session in vault
    cred = GitHubCredential(
        credential_id=TEST_SESSION,
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        account_login="api-octocat",
        scopes=["repo"],
    )
    _vault.store_credential(cred, "gho_api_test_token_12345")

def create_report(rem_id: str, status: str = "VERIFIED") -> RemediationReport:
    fp = compute_patch_fingerprint("octocat/hello-world", TEST_BASE_SHA, SAMPLE_DIFF)
    return RemediationReport(
        identity=ReportIdentity(
            workflow_id=rem_id,
            repository="https://github.com/octocat/hello-world",
            commit_sha=TEST_BASE_SHA,
        ),
        finding=ReportFinding(
            rule_id="button-name",
            description="Buttons must have discernible text",
            impact="critical",
            target_selector="button",
        ),
        source_location=ReportSourceLocation(
            file="src/App.tsx",
            start_line=1,
            end_line=3,
            match_status="EXACT",
        ),
        patch=ReportPatch(
            patch_id="p1",
            files_changed=["src/App.tsx"],
            unified_diff=SAMPLE_DIFF,
            rationale="Added aria-label to button.",
            patch_fingerprint=fp,
        ),
        validation=ReportValidation(
            status="VALID",
            checks=[ReportValidationCheck(name="syntax", status="PASS", message="Valid syntax")],
        ),
        sandbox_execution=ReportSandbox(
            status="VERIFIED",
            verification_reason="Resolved on re-scan",
        ),
        final_status=status,
    )

def test_1_publish_unauthenticated():
    response = client.post("/api/v1/github/remediations/rem-unauth/publish")
    assert response.status_code == 401
    assert "GITHUB_NOT_CONNECTED" in str(response.json())

def test_2_publish_not_found():
    response = client.post(
        "/api/v1/github/remediations/nonexistent-uuid/publish",
        cookies={"codeloom_session": TEST_SESSION}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "REMEDIATION_NOT_FOUND"

def test_3_publish_not_verified():
    report = create_report("rem-failed-status", status="FAILED")
    store_authoritative_remediation(report)

    response = client.post(
        "/api/v1/github/remediations/rem-failed-status/publish",
        cookies={"codeloom_session": TEST_SESSION}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "NOT_VERIFIED"

def test_4_publish_base_commit_stale():
    report = create_report("rem-stale-api")
    store_authoritative_remediation(report)

    mock_repo_resp = httpx.Response(status_code=200, json={"id": 1, "name": "hello-world", "full_name": "octocat/hello-world", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/hello-world.git", "default_branch": "main", "html_url": "https://github.com/octocat/hello-world"})
    mock_branch_resp = httpx.Response(status_code=200, json={"name": "main", "commit": {"sha": "advanced_sha_88888"}})

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [mock_repo_resp, mock_branch_resp]
        response = client.post(
            "/api/v1/github/remediations/rem-stale-api/publish",
            cookies={"codeloom_session": TEST_SESSION}
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "BASE_COMMIT_STALE"

def test_5_publish_success_flow():
    report = create_report("rem-api-success")
    store_authoritative_remediation(report)

    import base64
    b64_code = base64.b64encode(SAMPLE_CODE.encode('utf-8')).decode('utf-8')

    mock_responses = [
        httpx.Response(status_code=200, json={"id": 1, "name": "hello-world", "full_name": "octocat/hello-world", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/hello-world.git", "default_branch": "main", "html_url": "https://github.com/octocat/hello-world"}),
        httpx.Response(status_code=200, json={"name": "main", "commit": {"sha": TEST_BASE_SHA}}),
        httpx.Response(status_code=404, json={"message": "Not Found"}),
        httpx.Response(status_code=200, json={"content": b64_code, "encoding": "base64"}),
        httpx.Response(status_code=201, json={"sha": "blob_sha_abc"}),
        httpx.Response(status_code=200, json={"tree": {"sha": "tree_sha_base"}}),
        httpx.Response(status_code=201, json={"sha": "tree_sha_new"}),
        httpx.Response(status_code=201, json={"sha": "commit_sha_new"}),
        httpx.Response(status_code=201, json={"ref": "refs/heads/codeloom/fix-button-name-rem-api-", "object": {"sha": "commit_sha_new"}}),
        httpx.Response(status_code=200, json=[]),
        httpx.Response(status_code=201, json={"html_url": "https://github.com/octocat/hello-world/pull/77", "number": 77}),
    ]

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = mock_responses
        response = client.post(
            "/api/v1/github/remediations/rem-api-success/publish",
            cookies={"codeloom_session": TEST_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PUBLISHED"
        assert data["pull_request_url"] == "https://github.com/octocat/hello-world/pull/77"
        assert data["pull_request_number"] == 77
        assert data["commit_sha"] == "commit_sha_new"
