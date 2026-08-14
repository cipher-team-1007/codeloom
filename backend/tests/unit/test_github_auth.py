import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import httpx

from engine.github.config import GitHubConfig
from engine.github.vault import TokenVault
from engine.github.auth import GitHubAuthManager
from engine.github.exceptions import (
    GitHubAuthNotConfiguredError,
    GitHubAuthorizationDeniedError,
    GitHubInvalidStateError,
    GitHubStateExpiredError,
    GitHubTokenExchangeError,
    GitHubIdentityLookupError,
    GitHubOpenRedirectError,
)

TEST_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
TEST_CLIENT_ID = "mock_client_id_123"
TEST_CLIENT_SECRET = "mock_client_secret_xyz_999"

@pytest.fixture
def auth_manager():
    config = GitHubConfig(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
        encryption_key=TEST_ENCRYPTION_KEY,
        redirect_uri="http://localhost:8000/api/v1/github/callback",
        frontend_redirect_url="http://localhost:5173/app",
        allowed_redirect_hosts=["localhost", "127.0.0.1", "app.codeloom.io"],
    )
    vault = TokenVault(encryption_key=TEST_ENCRYPTION_KEY)
    return GitHubAuthManager(config=config, vault=vault)

# ----------------- Authorization Tests -----------------

def test_1_generate_authorization_url(auth_manager):
    session_id = "sess-12345"
    url = auth_manager.generate_authorization_url(session_id=session_id)
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert f"client_id={TEST_CLIENT_ID}" in url
    assert "state=" in url
    assert "scope=" in url
    # Client secret MUST NOT be in the URL
    assert TEST_CLIENT_SECRET not in url

def test_2_state_is_cryptographically_random(auth_manager):
    url1 = auth_manager.generate_authorization_url("s1")
    url2 = auth_manager.generate_authorization_url("s2")
    state1 = url1.split("state=")[1].split("&")[0]
    state2 = url2.split("state=")[1].split("&")[0]
    assert state1 != state2
    assert len(state1) >= 32

def test_3_missing_configuration_fails_safely():
    bad_config = GitHubConfig(client_id="", client_secret="", encryption_key=TEST_ENCRYPTION_KEY)
    mgr = GitHubAuthManager(config=bad_config)
    with pytest.raises(GitHubAuthNotConfiguredError):
        mgr.generate_authorization_url("s1")

def test_4_open_redirect_rejected(auth_manager):
    with pytest.raises(GitHubOpenRedirectError):
        auth_manager.generate_authorization_url("s1", custom_redirect="https://evil-phishing-site.com/steal")

def test_5_allowed_custom_redirect(auth_manager):
    url = auth_manager.generate_authorization_url("s1", custom_redirect="https://app.codeloom.io/dashboard")
    assert url is not None

# ----------------- CSRF & State Tests -----------------

def test_6_valid_state_consumed_once(auth_manager):
    url = auth_manager.generate_authorization_url("sess-single-use")
    state = url.split("state=")[1].split("&")[0]

    # First consumption succeeds
    data = auth_manager.validate_and_consume_state(state)
    assert data["session_id"] == "sess-single-use"

    # Second consumption fails (replay attack prevented)
    with pytest.raises(GitHubInvalidStateError):
        auth_manager.validate_and_consume_state(state)

def test_7_missing_or_invalid_state_fails(auth_manager):
    with pytest.raises(GitHubInvalidStateError):
        auth_manager.validate_and_consume_state("invalid_random_state_xyz")
    with pytest.raises(GitHubInvalidStateError):
        auth_manager.validate_and_consume_state(None)

def test_8_expired_state_fails(auth_manager):
    url = auth_manager.generate_authorization_url("sess-expired")
    state = url.split("state=")[1].split("&")[0]

    # Manually backdate the created_at timestamp
    auth_manager._state_store[state]["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=15)

    with pytest.raises(GitHubStateExpiredError):
        auth_manager.validate_and_consume_state(state)

# ----------------- Token Exchange & Callback Tests -----------------

@pytest.mark.asyncio
async def test_9_successful_token_exchange(auth_manager):
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "access_token": "gho_mock_access_token_1234567890",
            "token_type": "bearer",
            "scope": "repo,read:user",
        }
    )
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        token_data = await auth_manager.exchange_code("mock_auth_code_123")
        assert token_data["access_token"] == "gho_mock_access_token_1234567890"

@pytest.mark.asyncio
async def test_10_token_exchange_github_error(auth_manager):
    mock_resp = httpx.Response(
        status_code=200,
        json={"error": "bad_verification_code", "error_description": "The code passed is incorrect or expired."}
    )
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubTokenExchangeError) as exc_info:
            await auth_manager.exchange_code("bad_code")
        assert "bad_verification_code" in str(exc_info.value) or "incorrect" in str(exc_info.value)

@pytest.mark.asyncio
async def test_11_full_callback_flow_success(auth_manager):
    session_id = "sess-full-flow"
    auth_url = auth_manager.generate_authorization_url(session_id)
    state = auth_url.split("state=")[1].split("&")[0]

    mock_exchange_resp = httpx.Response(
        status_code=200,
        json={"access_token": "gho_mock_token_abcde12345", "token_type": "bearer", "scope": "repo,read:user"}
    )
    mock_user_resp = httpx.Response(
        status_code=200,
        json={
            "login": "octocat-dev",
            "id": 583231,
            "avatar_url": "https://avatars.githubusercontent.com/u/583231",
            "html_url": "https://github.com/octocat-dev",
            "name": "Octocat Developer",
        }
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_exchange_resp), \
         patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_user_resp):

        cred, redirect_url = await auth_manager.process_callback(code="auth_code_999", state=state)

        assert cred.account_login == "octocat-dev"
        assert cred.credential_id == session_id
        assert "repo" in cred.scopes
        assert redirect_url == "http://localhost:5173/app"

        # Verify vault contains encrypted token
        stored = auth_manager.vault.get_credential(session_id)
        assert stored is not None
        decrypted = auth_manager.vault.retrieve_secret(session_id)
        assert decrypted == "gho_mock_token_abcde12345"

        # Verify connection status
        status = auth_manager.get_connection_status(session_id)
        assert status["connected"] is True
        assert status["github_login"] == "octocat-dev"
        assert status["github_user_id"] == 583231

@pytest.mark.asyncio
async def test_12_user_denied_callback(auth_manager):
    with pytest.raises(GitHubAuthorizationDeniedError):
        await auth_manager.process_callback(code=None, state=None, error="access_denied", error_description="User denied access")

# ----------------- Status & Disconnect Tests -----------------

def test_13_status_disconnected_by_default(auth_manager):
    status = auth_manager.get_connection_status("unknown-session")
    assert status["connected"] is False
    assert status["github_login"] is None

def test_14_disconnect_flow(auth_manager):
    session_id = "sess-disconnect"
    # Seed credential in vault
    from engine.github.models import GitHubCredential, TokenType
    cred = GitHubCredential(
        credential_id=session_id,
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        account_login="octo-disconnect"
    )
    auth_manager.vault.store_credential(cred, "gho_secret_token")
    auth_manager._connections_store[session_id] = {"login": "octo-disconnect", "user_id": 123}

    assert auth_manager.get_connection_status(session_id)["connected"] is True

    # Disconnect
    assert auth_manager.disconnect(session_id) is True
    assert auth_manager.get_connection_status(session_id)["connected"] is False

    # Disconnect is idempotent
    assert auth_manager.disconnect(session_id) is False
