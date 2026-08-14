import pytest
import httpx
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

from engine.github.config import GitHubConfig
from engine.github.vault import TokenVault
from engine.github.models import GitHubCredential, TokenType, PublicationStatus
from engine.github.publisher import (
    GitHubPublisher,
    canonicalize_diff,
    compute_patch_fingerprint,
    apply_unified_diff,
    store_authoritative_remediation,
    _REMEDIATIONS_CACHE,
)
from engine.github.exceptions import (
    RemediationNotFoundError,
    RemediationNotVerifiedError,
    InvalidPatchFingerprintError,
    BaseCommitStaleError,
    PatchApplicationError,
    GitHubAuthenticationError,
)
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

TEST_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
TEST_BASE_SHA = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
TEST_SESSION_ID = "sess-publisher-test"

SAMPLE_BASE_CODE = """import React from 'react';

export const ProductCard = () => {
    return (
        <div className="card">
            <img src="/img/product.png" />
            <h3>Product Title</h3>
        </div>
    );
};
"""

SAMPLE_UNIFIED_DIFF = """--- a/src/components/ProductCard.tsx
+++ b/src/components/ProductCard.tsx
@@ -5,3 +5,3 @@
         <div className="card">
-            <img src="/img/product.png" />
+            <img src="/img/product.png" alt="Product Image" />
             <h3>Product Title</h3>
"""

@pytest.fixture
def publisher():
    _REMEDIATIONS_CACHE.clear()
    config = GitHubConfig(encryption_key=TEST_ENCRYPTION_KEY)
    vault = TokenVault(encryption_key=TEST_ENCRYPTION_KEY)
    # Seed authenticated session in vault
    cred = GitHubCredential(
        credential_id=TEST_SESSION_ID,
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        account_login="octocat-pub",
        scopes=["repo"],
    )
    vault.store_credential(cred, "gho_test_token_12345")
    return GitHubPublisher(config=config, vault=vault)

def create_mock_report(
    workflow_id: str = "rem-test-001",
    final_status: str = "VERIFIED",
    files_changed: list = None,
    unified_diff: str = SAMPLE_UNIFIED_DIFF,
    rule_id: str = "image-alt",
) -> RemediationReport:
    if files_changed is None:
        files_changed = ["src/components/ProductCard.tsx"]

    fingerprint = compute_patch_fingerprint("octocat/hello-world", TEST_BASE_SHA, unified_diff)

    return RemediationReport(
        identity=ReportIdentity(
            workflow_id=workflow_id,
            repository="https://github.com/octocat/hello-world",
            commit_sha=TEST_BASE_SHA,
            plan_id="plan-1",
            patch_id="patch-1",
        ),
        finding=ReportFinding(
            rule_id=rule_id,
            description="Images must have alternate text",
            impact="critical",
            target_selector="img[src='/img/product.png']",
        ),
        root_cause=ReportRootCause(description="Missing alt attribute on product image."),
        source_location=ReportSourceLocation(
            file=files_changed[0],
            start_line=5,
            end_line=7,
            match_status="EXACT",
        ),
        patch=ReportPatch(
            patch_id="patch-1",
            files_changed=files_changed,
            unified_diff=unified_diff,
            rationale="Added alt attribute to product image.",
            patch_fingerprint=fingerprint,
        ),
        validation=ReportValidation(
            status="VALID",
            checks=[
                ReportValidationCheck(name="syntax_check", status="PASS", message="Syntax parsed cleanly."),
                ReportValidationCheck(name="scope_check", status="PASS", message="Patch constrained to single file."),
            ],
        ),
        sandbox_execution=ReportSandbox(
            status="VERIFIED",
            verification_reason="Violation resolved on runtime re-scan.",
        ),
        before_after=ReportBeforeAfter(
            rule_id=rule_id,
            target_selector="img[src='/img/product.png']",
            before_status="VIOLATION_PRESENT",
            after_status="VIOLATION_RESOLVED",
        ),
        final_status=final_status,
    )

# ----------------- Diff & Fingerprint Unit Tests -----------------

def test_1_canonicalize_diff():
    crlf_diff = "--- a/file\r\n+++ b/file\r\n@@ -1,1 +1,1 @@\r\n-old  \r\n+new\r\n\r\n"
    lf_diff = "--- a/file\n+++ b/file\n@@ -1,1 +1,1 @@\n-old\n+new"
    assert canonicalize_diff(crlf_diff) == canonicalize_diff(lf_diff)

def test_2_fingerprint_determinism():
    fp1 = compute_patch_fingerprint("https://github.com/octocat/hello-world.git", TEST_BASE_SHA, SAMPLE_UNIFIED_DIFF)
    fp2 = compute_patch_fingerprint("octocat/hello-world", TEST_BASE_SHA, SAMPLE_UNIFIED_DIFF)
    assert fp1 == fp2
    assert len(fp1) == 64

def test_3_fingerprint_sensitivity():
    fp_base = compute_patch_fingerprint("octocat/hello-world", TEST_BASE_SHA, SAMPLE_UNIFIED_DIFF)
    fp_diff_repo = compute_patch_fingerprint("other/hello-world", TEST_BASE_SHA, SAMPLE_UNIFIED_DIFF)
    fp_diff_sha = compute_patch_fingerprint("octocat/hello-world", "0000000000000000000000000000000000000000", SAMPLE_UNIFIED_DIFF)
    fp_diff_code = compute_patch_fingerprint("octocat/hello-world", TEST_BASE_SHA, SAMPLE_UNIFIED_DIFF + "\n+// extra")

    assert fp_base != fp_diff_repo
    assert fp_base != fp_diff_sha
    assert fp_base != fp_diff_code

def test_4_apply_unified_diff():
    updated = apply_unified_diff(SAMPLE_BASE_CODE, SAMPLE_UNIFIED_DIFF)
    assert '<img src="/img/product.png" alt="Product Image" />' in updated
    assert '<img src="/img/product.png" />' not in updated

# ----------------- Publication Gate Tests -----------------

@pytest.mark.asyncio
async def test_5_gate1_missing_remediation(publisher):
    with pytest.raises(RemediationNotFoundError):
        await publisher.publish_verified_remediation("nonexistent-id", TEST_SESSION_ID)

@pytest.mark.asyncio
async def test_6_gate2_disconnected_session(publisher):
    report = create_mock_report("rem-disc")
    store_authoritative_remediation(report)
    with pytest.raises(GitHubAuthenticationError):
        await publisher.publish_verified_remediation("rem-disc", "unauthenticated-session-id")

@pytest.mark.asyncio
async def test_7_gate3_not_verified_remediation(publisher):
    report = create_mock_report("rem-failed", final_status="FAILED")
    store_authoritative_remediation(report)
    with pytest.raises(RemediationNotVerifiedError):
        await publisher.publish_verified_remediation("rem-failed", TEST_SESSION_ID)

@pytest.mark.asyncio
async def test_8_gate7_fingerprint_mismatch(publisher):
    report = create_mock_report("rem-tampered")
    # Tamper with stored fingerprint
    report.patch.patch_fingerprint = "0000000000000000000000000000000000000000000000000000000000000000"
    store_authoritative_remediation(report)
    with pytest.raises(InvalidPatchFingerprintError):
        await publisher.publish_verified_remediation("rem-tampered", TEST_SESSION_ID)

@pytest.mark.asyncio
async def test_9_gate8_stale_base_commit_toctou(publisher):
    report = create_mock_report("rem-stale")
    store_authoritative_remediation(report)

    # Mock remote branch HEAD at a newer commit
    mock_repo_resp = httpx.Response(status_code=200, json={"id": 1, "name": "hello-world", "full_name": "octocat/hello-world", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/hello-world.git", "default_branch": "main", "html_url": "https://github.com/octocat/hello-world"})
    mock_branch_resp = httpx.Response(status_code=200, json={"name": "main", "commit": {"sha": "newer_commit_sha_9999999999"}})

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [mock_repo_resp, mock_branch_resp]
        with pytest.raises(BaseCommitStaleError) as exc_info:
            await publisher.publish_verified_remediation("rem-stale", TEST_SESSION_ID)
        assert "advanced" in str(exc_info.value)

@pytest.mark.asyncio
async def test_10_multi_file_policy_rejection(publisher):
    report = create_mock_report("rem-multi", files_changed=["src/A.tsx", "src/B.tsx"])
    store_authoritative_remediation(report)
    with pytest.raises(PatchApplicationError):
        await publisher.publish_verified_remediation("rem-multi", TEST_SESSION_ID)

# ----------------- Successful End-to-End Publication Flow -----------------

@pytest.mark.asyncio
async def test_11_successful_publication_flow(publisher):
    report = create_mock_report("rem-success-001")
    store_authoritative_remediation(report)

    # Mock responses for all Git Data APIs in sequence
    mock_repo_resp = httpx.Response(status_code=200, json={"id": 1, "name": "hello-world", "full_name": "octocat/hello-world", "owner": {"login": "octocat"}, "clone_url": "https://github.com/octocat/hello-world.git", "default_branch": "main", "html_url": "https://github.com/octocat/hello-world"})
    mock_branch_resp = httpx.Response(status_code=200, json={"name": "main", "commit": {"sha": TEST_BASE_SHA}})
    mock_ref_get_resp = httpx.Response(status_code=404, json={"message": "Not Found"}) # Branch does not exist yet
    import base64
    b64_base_code = base64.b64encode(SAMPLE_BASE_CODE.encode('utf-8')).decode('utf-8')
    mock_content_resp = httpx.Response(status_code=200, json={"content": b64_base_code, "encoding": "base64"})
    mock_blob_resp = httpx.Response(status_code=201, json={"sha": "blob_sha_12345"})
    mock_tree_get_resp = httpx.Response(status_code=200, json={"tree": {"sha": "base_tree_sha_12345"}})
    mock_tree_post_resp = httpx.Response(status_code=201, json={"sha": "new_tree_sha_12345"})
    mock_commit_resp = httpx.Response(status_code=201, json={"sha": "new_commit_sha_12345"})
    mock_ref_post_resp = httpx.Response(status_code=201, json={"ref": "refs/heads/codeloom/fix-image-alt-rem-succ", "object": {"sha": "new_commit_sha_12345"}})
    mock_list_prs_resp = httpx.Response(status_code=200, json=[]) # No existing PRs
    mock_pr_resp = httpx.Response(status_code=201, json={"html_url": "https://github.com/octocat/hello-world/pull/42", "number": 42})

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            mock_repo_resp,
            mock_branch_resp,
            mock_ref_get_resp,
            mock_content_resp,
            mock_blob_resp,
            mock_tree_get_resp,
            mock_tree_post_resp,
            mock_commit_resp,
            mock_ref_post_resp,
            mock_list_prs_resp,
            mock_pr_resp,
        ]

        result = await publisher.publish_verified_remediation("rem-success-001", TEST_SESSION_ID)

        assert result.status == PublicationStatus.PUBLISHED.value
        assert result.remediation_id == "rem-success-001"
        assert result.repository == "octocat/hello-world"
        assert result.branch.startswith("codeloom/fix-image-alt-")
        assert result.commit_sha == "new_commit_sha_12345"
        assert result.pull_request_url == "https://github.com/octocat/hello-world/pull/42"
        assert result.pull_request_number == 42

@pytest.mark.asyncio
async def test_12_idempotent_publication(publisher):
    report = create_mock_report("rem-idempotent")
    store_authoritative_remediation(report)

    # Seed an already published result
    from engine.github.models import PublicationResult
    publisher._publications_store["rem-idempotent"] = PublicationResult(
        status="PUBLISHED",
        remediation_id="rem-idempotent",
        repository="octocat/hello-world",
        branch="codeloom/fix-image-alt-rem-idem",
        commit_sha="existing_commit_sha",
        pull_request_url="https://github.com/octocat/hello-world/pull/99",
        pull_request_number=99,
        published_at=datetime.now(timezone.utc),
    )

    # Calling publish immediately returns the cached result without making HTTP requests
    result = await publisher.publish_verified_remediation("rem-idempotent", TEST_SESSION_ID)
    assert result.pull_request_url == "https://github.com/octocat/hello-world/pull/99"
    assert result.pull_request_number == 99
