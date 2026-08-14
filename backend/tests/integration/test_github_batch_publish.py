import pytest
import base64
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from engine.api.app import app
from engine.api.github import _config, _vault
from engine.github.models import GitHubCredential, TokenType
from engine.github.publisher import (
    store_authoritative_remediation,
    store_authoritative_batch_report,
    compute_patch_fingerprint,
)
from engine.queue.models import (
    RemediationBatchReport,
    CanonicalFinding,
    FindingStatus,
    BatchStatus,
)
from engine.models.report import (
    RemediationReport,
    ReportIdentity,
    ReportFinding,
    ReportSourceLocation,
    ReportPatch,
    ReportValidation,
    ReportValidationCheck,
    ReportSandbox,
)

client = TestClient(app)

TEST_BASE_SHA = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
TEST_SESSION = "sess-batch-publish-test"

DIFF_1 = """--- a/src/Button.tsx
+++ b/src/Button.tsx
@@ -1,3 +1,3 @@
 <div>
-  <button>Click</button>
+  <button aria-label="Submit">Click</button>
 </div>
"""

CODE_1 = """<div>
  <button>Click</button>
</div>
"""

DIFF_2 = """--- a/src/Hero.tsx
+++ b/src/Hero.tsx
@@ -1,3 +1,3 @@
 <div>
-  <img src="hero.png" />
+  <img src="hero.png" alt="Hero banner" />
 </div>
"""

CODE_2 = """<div>
  <img src="hero.png" />
</div>
"""

@pytest.fixture(autouse=True)
def setup_environment():
    _config.client_id = "test_client_id"
    _config.client_secret = "test_secret"
    _config.encryption_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    _vault._key_bytes = _vault._derive_key_bytes(_config.encryption_key)

    cred = GitHubCredential(
        credential_id=TEST_SESSION,
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        account_login="octocat-batch",
        scopes=["repo"],
    )
    _vault.store_credential(cred, "gho_batch_test_token_12345")


def make_single_report(rem_id: str, file_path: str, diff_text: str, status: str = "VERIFIED") -> RemediationReport:
    fp = compute_patch_fingerprint("octocat/batch-repo", TEST_BASE_SHA, diff_text)
    return RemediationReport(
        identity=ReportIdentity(
            workflow_id=rem_id,
            repository="https://github.com/octocat/batch-repo",
            commit_sha=TEST_BASE_SHA,
        ),
        finding=ReportFinding(
            rule_id="a11y-rule",
            description="Accessibility violation",
            impact="critical",
            target_selector="element",
        ),
        source_location=ReportSourceLocation(
            file=file_path,
            start_line=1,
            end_line=3,
            match_status="EXACT",
        ),
        patch=ReportPatch(
            patch_id="p_" + rem_id,
            files_changed=[file_path],
            unified_diff=diff_text,
            rationale="Fix applied",
            patch_fingerprint=fp,
        ),
        validation=ReportValidation(
            status="VALID",
            checks=[ReportValidationCheck(name="syntax", status="PASS", message="Valid")],
        ),
        sandbox_execution=ReportSandbox(
            status="VERIFIED",
            verification_reason="Resolved on re-scan",
        ),
        final_status=status,
    )


def make_batch_report(
    queue_id: str,
    verified_count: int = 2,
    failed_count: int = 1,
    base_sha: str = TEST_BASE_SHA,
) -> RemediationBatchReport:
    r1 = make_single_report("wf_1", "src/Button.tsx", DIFF_1, "VERIFIED")
    r2 = make_single_report("wf_2", "src/Hero.tsx", DIFF_2, "VERIFIED")
    r3 = make_single_report("wf_3", "src/Input.tsx", "", "FAILED")

    f1 = CanonicalFinding(
        finding_id="cf_1",
        rule_id="button-name",
        category="accessibility",
        severity="critical",
        title="Buttons must have name",
        description="Missing button name",
        selectors=["button"],
        html_snippets=["<button>Click</button>"],
        status=FindingStatus.VERIFIED,
        retry_count=0,
        remediation_workflow_id="wf_1",
        report_id="wf_1",
    )
    f2 = CanonicalFinding(
        finding_id="cf_2",
        rule_id="image-alt",
        category="accessibility",
        severity="serious",
        title="Images must have alt",
        description="Missing image alt",
        selectors=["img.hero"],
        html_snippets=['<img src="hero.png" />'],
        status=FindingStatus.VERIFIED,
        retry_count=0,
        remediation_workflow_id="wf_2",
        report_id="wf_2",
    )
    f3 = CanonicalFinding(
        finding_id="cf_3",
        rule_id="label",
        category="accessibility",
        severity="moderate",
        title="Form elements must have label",
        description="Missing form label",
        selectors=["input"],
        html_snippets=['<input />'],
        status=FindingStatus.NOT_VERIFIED,
        retry_count=1,
        remediation_workflow_id="wf_3",
        report_id="wf_3",
        error_message="Sandbox verification failed",
    )

    findings = []
    reports = {}
    if verified_count >= 1:
        findings.append(f1)
        reports["cf_1"] = r1.model_dump()
    if verified_count >= 2:
        findings.append(f2)
        reports["cf_2"] = r2.model_dump()
    if failed_count >= 1:
        findings.append(f3)
        reports["cf_3"] = r3.model_dump()

    agg_status = BatchStatus.ALL_VERIFIED if failed_count == 0 else BatchStatus.PARTIALLY_VERIFIED
    if verified_count == 0:
        agg_status = BatchStatus.NONE_VERIFIED

    return RemediationBatchReport(
        batch_id="b_" + queue_id,
        queue_id=queue_id,
        repository="https://github.com/octocat/batch-repo",
        base_commit_sha=base_sha,
        final_working_sha="final_working_sha_abc123",
        aggregate_status=agg_status,
        total_findings=len(findings),
        verified_count=verified_count,
        failed_count=failed_count,
        skipped_count=0,
        blocked_count=0,
        findings=findings,
        reports=reports,
    )


def test_1_publish_batch_unauthenticated():
    response = client.post("/api/v1/github/queues/q_unauth/publish")
    assert response.status_code == 401
    assert "GITHUB_NOT_CONNECTED" in str(response.json())


def test_2_publish_batch_not_found():
    response = client.post(
        "/api/v1/github/queues/q_nonexistent/publish",
        cookies={"codeloom_session": TEST_SESSION},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "REMEDIATION_NOT_FOUND"


def test_3_publish_batch_none_verified():
    batch_report = make_batch_report("q_none_verified", verified_count=0, failed_count=2)
    store_authoritative_batch_report(batch_report)

    response = client.post(
        "/api/v1/github/queues/q_none_verified/publish",
        cookies={"codeloom_session": TEST_SESSION},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "NOT_VERIFIED"


def test_4_publish_batch_stale_base_sha():
    batch_report = make_batch_report("q_stale_base", verified_count=2, failed_count=1)
    store_authoritative_batch_report(batch_report)

    mock_repo_resp = httpx.Response(
        status_code=200,
        json={"id": 1, "name": "batch-repo", "full_name": "octocat/batch-repo", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/batch-repo.git", "default_branch": "main", "html_url": "https://github.com/octocat/batch-repo"},
    )
    mock_branch_resp = httpx.Response(
        status_code=200,
        json={"name": "main", "commit": {"sha": "advanced_sha_remote_999"}},
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [mock_repo_resp, mock_branch_resp]
        response = client.post(
            "/api/v1/github/queues/q_stale_base/publish",
            cookies={"codeloom_session": TEST_SESSION},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "BASE_COMMIT_STALE"


def test_5_publish_batch_success_flow():
    batch_report = make_batch_report("q_success_batch", verified_count=2, failed_count=1)
    store_authoritative_batch_report(batch_report)

    b64_code_1 = base64.b64encode(CODE_1.encode("utf-8")).decode("utf-8")
    b64_code_2 = base64.b64encode(CODE_2.encode("utf-8")).decode("utf-8")

    mock_responses = [
        # 1. get_repository
        httpx.Response(status_code=200, json={"id": 1, "name": "batch-repo", "full_name": "octocat/batch-repo", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/batch-repo.git", "default_branch": "main", "html_url": "https://github.com/octocat/batch-repo"}),
        # 2. get_branch default
        httpx.Response(status_code=200, json={"name": "main", "commit": {"sha": TEST_BASE_SHA}}),
        # 3. get_reference branch check
        httpx.Response(status_code=404, json={"message": "Not Found"}),
        # 4. Item 1: get_file_content (Button.tsx)
        httpx.Response(status_code=200, json={"content": b64_code_1, "encoding": "base64"}),
        # 5. Item 1: create_blob
        httpx.Response(status_code=201, json={"sha": "blob_sha_1"}),
        # 6. Item 1: get_commit_tree_sha
        httpx.Response(status_code=200, json={"tree": {"sha": "tree_sha_base"}}),
        # 7. Item 1: create_tree
        httpx.Response(status_code=201, json={"sha": "tree_sha_1"}),
        # 8. Item 1: create_commit_object
        httpx.Response(status_code=201, json={"sha": "commit_sha_1"}),
        # 9. Item 2: get_file_content (Hero.tsx)
        httpx.Response(status_code=200, json={"content": b64_code_2, "encoding": "base64"}),
        # 10. Item 2: create_blob
        httpx.Response(status_code=201, json={"sha": "blob_sha_2"}),
        # 11. Item 2: get_commit_tree_sha
        httpx.Response(status_code=200, json={"tree": {"sha": "tree_sha_1"}}),
        # 12. Item 2: create_tree
        httpx.Response(status_code=201, json={"sha": "tree_sha_2"}),
        # 13. Item 2: create_commit_object
        httpx.Response(status_code=201, json={"sha": "commit_sha_2"}),
        # 14. create_reference (branch codeloom/batch-fix-success_)
        httpx.Response(status_code=201, json={"ref": "refs/heads/codeloom/batch-fix-success_", "object": {"sha": "commit_sha_2"}}),
        # 15. list_pull_requests
        httpx.Response(status_code=200, json=[]),
        # 16. create_pull_request
        httpx.Response(status_code=201, json={"html_url": "https://github.com/octocat/batch-repo/pull/99", "number": 99}),
    ]

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = mock_responses
        response = client.post(
            "/api/v1/github/queues/q_success_batch/publish",
            cookies={"codeloom_session": TEST_SESSION},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PUBLISHED"
        assert data["pull_request_url"] == "https://github.com/octocat/batch-repo/pull/99"
        assert data["pull_request_number"] == 99
        assert data["commit_sha"] == "commit_sha_2"

        # Verify PR creation call contained body table with excluded finding
        pr_call = mock_req.call_args_list[-1]
        payload = pr_call.kwargs.get("json", {})
        body = payload.get("body", "")
        assert "Included Verified Remediations" in body
        assert "Excluded Findings" in body
        assert "button-name" in body
        assert "image-alt" in body
        assert "label" in body
