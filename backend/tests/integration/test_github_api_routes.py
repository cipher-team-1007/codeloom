import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from engine.api.app import app
from engine.api.github import _auth_manager, _config, _vault

client = TestClient(app)

@pytest.fixture(autouse=True)
def configure_auth_manager():
    _config.client_id = "test_client_id_123"
    _config.client_secret = "test_client_secret_xyz"
    _config.encryption_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    _vault._key_bytes = _vault._derive_key_bytes(_config.encryption_key)

def test_1_api_authorize_redirect():
    response = client.get("/api/v1/github/authorize", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize")
    assert "client_id=test_client_id_123" in location
    assert "state=" in location
    assert "codeloom_session" in response.cookies

def test_2_api_authorize_json_mode():
    response = client.get("/api/v1/github/authorize?json=1")
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "session_id" in data
    assert "client_id=test_client_id_123" in data["authorization_url"]

def test_3_api_status_disconnected():
    response = client.get("/api/v1/github/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["github_login"] is None

def test_4_api_callback_success():
    # 1. Initiate authorization to seed state and cookie
    auth_resp = client.get("/api/v1/github/authorize?json=1")
    session_id = auth_resp.json()["session_id"]
    auth_url = auth_resp.json()["authorization_url"]
    state = auth_url.split("state=")[1].split("&")[0]

    mock_exchange_resp = httpx.Response(
        status_code=200,
        json={"access_token": "gho_api_test_token_999", "token_type": "bearer", "scope": "repo,read:user"}
    )
    mock_user_resp = httpx.Response(
        status_code=200,
        json={
            "login": "api-test-octocat",
            "id": 1234567,
            "avatar_url": "https://avatars.githubusercontent.com/u/1234567",
            "html_url": "https://github.com/api-test-octocat",
        }
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_exchange_resp), \
         patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_user_resp):

        callback_resp = client.get(
            f"/api/v1/github/callback?code=valid_code_123&state={state}",
            cookies={"codeloom_session": session_id},
            follow_redirects=False
        )

        assert callback_resp.status_code == 307
        redirect_url = callback_resp.headers["location"]
        assert "github=connected" in redirect_url
        assert "token" not in redirect_url
        assert "gho_" not in redirect_url

        # Check status endpoint with same session cookie
        status_resp = client.get("/api/v1/github/status", cookies={"codeloom_session": session_id})
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["connected"] is True
        assert status_data["github_login"] == "api-test-octocat"
        assert status_data["github_user_id"] == 1234567

def test_5_api_callback_user_denied():
    response = client.get("/api/v1/github/callback?error=access_denied&error_description=The+user+denied", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "github=denied" in location

def test_6_api_callback_missing_params():
    response = client.get("/api/v1/github/callback")
    assert response.status_code == 400
    assert "Missing required OAuth" in response.json()["detail"]

def test_7_api_callback_invalid_state():
    response = client.get("/api/v1/github/callback?code=mock_code&state=nonexistent_state")
    assert response.status_code == 400
    assert "Invalid or unrecognized OAuth state" in response.json()["detail"]

def test_8_api_disconnect():
    # Set up session with connected state
    session_id = "sess-api-disconnect-test"
    from engine.github.models import GitHubCredential, TokenType
    cred = GitHubCredential(credential_id=session_id, token_type=TokenType.OAUTH_ACCESS_TOKEN, account_login="octo-disc")
    _vault.store_credential(cred, "gho_token_value")
    _auth_manager._connections_store[session_id] = {"login": "octo-disc", "user_id": 999}

    # Verify connected
    status1 = client.get("/api/v1/github/status", cookies={"codeloom_session": session_id}).json()
    assert status1["connected"] is True

    # Disconnect
    disc_resp = client.post("/api/v1/github/disconnect", cookies={"codeloom_session": session_id})
    assert disc_resp.status_code == 200
    assert disc_resp.json()["connected"] is False
    assert disc_resp.json()["disconnected"] is True

    # Verify disconnected
    status2 = client.get("/api/v1/github/status", cookies={"codeloom_session": session_id}).json()
    assert status2["connected"] is False
