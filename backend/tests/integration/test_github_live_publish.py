import os
import pytest
from datetime import datetime, timezone

from engine.github.config import GitHubConfig
from engine.github.vault import TokenVault
from engine.github.models import GitHubCredential, TokenType, PublicationStatus
from engine.github.client import GitHubClient
from engine.github.publisher import (
    GitHubPublisher,
    store_authoritative_remediation,
    compute_patch_fingerprint,
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

LIVE_PUBLISH_SKIP_REASON = (
    "Live GitHub write integration tests are disabled by default for safety. "
    "Set RUN_GITHUB_PUBLISH_INTEGRATION_TESTS=1 along with disposable repository variables: "
    "GITHUB_TEST_TOKEN, GITHUB_TEST_OWNER, GITHUB_TEST_REPOSITORY."
)

@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("RUN_GITHUB_PUBLISH_INTEGRATION_TESTS"), reason=LIVE_PUBLISH_SKIP_REASON)
async def test_live_verified_patch_publication_flow():
    """
    HIGH-RISK LIVE INTEGRATION TEST:
    Executes a real branch creation, commit creation, and Pull Request creation against
    a dedicated, disposable GitHub repository explicitly provided in the environment.
    """
    token = os.environ.get("GITHUB_TEST_TOKEN") or os.environ.get("GITHUB_TOKEN")
    owner = os.environ.get("GITHUB_TEST_OWNER")
    repo_name = os.environ.get("GITHUB_TEST_REPOSITORY")
    target_file = os.environ.get("GITHUB_TEST_FILE", "src/components/ProductCard.tsx")
    base_branch = os.environ.get("GITHUB_TEST_BASE_BRANCH", "main")

    if not token or not owner or not repo_name:
        pytest.skip(
            "Missing required live test environment variables. "
            "Please provide GITHUB_TEST_TOKEN, GITHUB_TEST_OWNER, and GITHUB_TEST_REPOSITORY."
        )

    # 1. Initialize client & fetch live base commit SHA
    test_key = os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY") or "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    config = GitHubConfig(encryption_key=test_key)
    client = GitHubClient(config=config, access_token=token)

    repo_info = await client.get_repository(owner, repo_name)
    assert repo_info.name.lower() == repo_name.lower()

    branch_info = await client.get_branch(owner, repo_name, base_branch)
    base_sha = branch_info.commit_sha
    assert len(base_sha) == 40

    # 2. Fetch live file content from the base SHA
    target_files_to_try = [target_file, "README.md", "package.json"]
    base_content = None
    actual_file = target_file
    for tf in target_files_to_try:
        try:
            content = await client.get_file_content(owner, repo_name, tf, ref=base_sha)
            if content and len(content.strip()) > 0:
                base_content = content
                actual_file = tf
                break
        except Exception:
            continue

    if not base_content:
        pytest.fail(f"Could not find any readable target file in {owner}/{repo_name} (tried: {target_files_to_try})")

    target_file = actual_file

    # 3. Create controlled unified diff for the accessibility fix
    # e.g. adding alt attribute to img
    if '<img src="' in base_content and 'alt="' not in base_content:
        old_line = '<img src="/img/product.png" />'
        new_line = '<img src="/img/product.png" alt="Product Image" />'
    else:
        # Generic deterministic single-line replacement for live testing
        first_line = base_content.splitlines()[0] if base_content.splitlines() else "<div>"
        old_line = first_line
        new_line = f"{first_line} <!-- a11y verified fix -->"

    unified_diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,1 +1,1 @@\n-{old_line}\n+{new_line}"

    repo_full_name = f"{owner}/{repo_name}"
    workflow_id = f"live-test-{int(datetime.now(timezone.utc).timestamp())}"
    fingerprint = compute_patch_fingerprint(repo_full_name, base_sha, unified_diff)

    # 4. Construct authoritative VERIFIED RemediationReport
    report = RemediationReport(
        identity=ReportIdentity(
            workflow_id=workflow_id,
            repository=f"https://github.com/{repo_full_name}",
            commit_sha=base_sha,
            plan_id="plan-live-01",
            patch_id="patch-live-01",
        ),
        finding=ReportFinding(
            rule_id="image-alt",
            description="Images must have alternate text",
            impact="critical",
            target_selector="img",
        ),
        root_cause=ReportRootCause(description="Missing alt attribute on element."),
        source_location=ReportSourceLocation(
            file=target_file,
            start_line=1,
            end_line=2,
            match_status="EXACT",
        ),
        patch=ReportPatch(
            patch_id="patch-live-01",
            files_changed=[target_file],
            unified_diff=unified_diff,
            rationale="Added accessible alternative text.",
            patch_fingerprint=fingerprint,
        ),
        validation=ReportValidation(
            status="VALID",
            checks=[
                ReportValidationCheck(name="syntax_check", status="PASS", message="Clean syntax"),
                ReportValidationCheck(name="single_file_bound", status="PASS", message="Constrained to single file"),
            ],
        ),
        sandbox_execution=ReportSandbox(
            status="VERIFIED",
            verification_reason="Violation resolved on runtime Axe-core re-scan in sandbox.",
        ),
        before_after=ReportBeforeAfter(
            rule_id="image-alt",
            target_selector="img",
            before_status="VIOLATION_PRESENT",
            after_status="VIOLATION_RESOLVED",
        ),
        final_status="VERIFIED",
    )

    store_authoritative_remediation(report)

    # 5. Seed vault with test session
    session_id = f"sess-live-{workflow_id}"
    vault = TokenVault(encryption_key=config.encryption_key)
    cred = GitHubCredential(
        credential_id=session_id,
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        account_login=owner,
        scopes=["repo"],
    )
    vault.store_credential(cred, token)

    # 6. Execute Live Publication via GitHubPublisher
    publisher = GitHubPublisher(config=config, vault=vault)
    result = await publisher.publish_verified_remediation(workflow_id, session_id)

    # 7. Verify Publication Result
    assert result.status == PublicationStatus.PUBLISHED.value
    assert result.remediation_id == workflow_id
    assert result.repository.lower() == repo_full_name.lower()
    assert result.branch.startswith("codeloom/fix-image-alt-")
    assert len(result.commit_sha) == 40
    assert result.pull_request_url.startswith("https://github.com/")
    assert result.pull_request_number is not None

    # 8. Read back from GitHub API to verify remote state
    created_branch_ref = await client.get_reference(owner, repo_name, f"heads/{result.branch}")
    assert created_branch_ref is not None
    assert created_branch_ref["object"]["sha"] == result.commit_sha

    created_commit = await client.get_commit(owner, repo_name, result.commit_sha)
    assert created_commit.sha == result.commit_sha
    assert "Remediation-ID:" in created_commit.message
    assert "Verified-Base-SHA:" in created_commit.message
    assert "Patch-Fingerprint:" in created_commit.message
    assert token not in created_commit.message
    assert config.encryption_key not in created_commit.message

    # 9. Verify Idempotency against live GitHub repository
    idempotent_result = await publisher.publish_verified_remediation(workflow_id, session_id)
    assert idempotent_result.pull_request_url == result.pull_request_url
    assert idempotent_result.commit_sha == result.commit_sha
    assert idempotent_result.branch == result.branch
