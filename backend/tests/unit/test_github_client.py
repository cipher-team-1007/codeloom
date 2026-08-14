import pytest
import httpx
from unittest.mock import patch, AsyncMock

from engine.github.client import GitHubClient
from engine.github.config import GitHubConfig
from engine.github.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubAuthorizationError,
    GitHubNotFoundError,
    GitHubConflictError,
    GitHubValidationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
    GitHubNetworkError,
)

TEST_TOKEN = "ghp_mock_token_1234567890abcdef"

@pytest.fixture
def client():
    config = GitHubConfig(api_base_url="https://api.github.com", timeout=2.0)
    return GitHubClient(config=config, access_token=TEST_TOKEN)

@pytest.mark.asyncio
async def test_1_successful_authenticated_user(client):
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "login": "octocat",
            "id": 1,
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "html_url": "https://github.com/octocat",
            "name": "monalisa octocat",
            "email": "octocat@github.com"
        },
        headers={"x-ratelimit-remaining": "4999"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp) as mock_req:
        user = await client.get_authenticated_user()
        assert user.login == "octocat"
        assert user.id == 1
        assert user.name == "monalisa octocat"
        
        # Verify request call headers
        mock_req.assert_called_once()
        headers = mock_req.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {TEST_TOKEN}"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

@pytest.mark.asyncio
async def test_2_401_authentication_failure(client):
    mock_resp = httpx.Response(
        status_code=401,
        json={"message": "Bad credentials", "documentation_url": "https://docs.github.com/rest"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubAuthenticationError) as exc_info:
            await client.get_authenticated_user()
        assert exc_info.value.status_code == 401
        assert TEST_TOKEN not in str(exc_info.value)

@pytest.mark.asyncio
async def test_3_403_authorization_failure(client):
    mock_resp = httpx.Response(
        status_code=403,
        json={"message": "Resource not accessible by integration"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubAuthorizationError) as exc_info:
            await client.get_repository("org", "private-repo")
        assert exc_info.value.status_code == 403

@pytest.mark.asyncio
async def test_4_404_not_found(client):
    mock_resp = httpx.Response(
        status_code=404,
        json={"message": "Not Found"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubNotFoundError) as exc_info:
            await client.get_repository("nonexistent", "repo")
        assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_5_409_conflict(client):
    mock_resp = httpx.Response(
        status_code=409,
        json={"message": "Git ref collision"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubConflictError) as exc_info:
            await client.get_branch("owner", "repo", "conflict-branch")
        assert exc_info.value.status_code == 409

@pytest.mark.asyncio
async def test_6_422_validation_error(client):
    mock_resp = httpx.Response(
        status_code=422,
        json={"message": "Validation Failed", "errors": [{"resource": "Issue", "field": "title", "code": "missing"}]}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubValidationError) as exc_info:
            await client._request("POST", "/repos/owner/repo/issues", json_data={})
        assert exc_info.value.status_code == 422

@pytest.mark.asyncio
async def test_7_429_rate_limit_exceeded(client):
    mock_resp = httpx.Response(
        status_code=429,
        json={"message": "API rate limit exceeded"},
        headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.get_repository("owner", "repo")
        assert exc_info.value.remaining == 0
        assert exc_info.value.limit == 5000

@pytest.mark.asyncio
async def test_8_timeout_exception(client):
    with patch.object(httpx.AsyncClient, "request", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(GitHubTimeoutError):
            await client.get_authenticated_user()

@pytest.mark.asyncio
async def test_9_network_error(client):
    with patch.object(httpx.AsyncClient, "request", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(GitHubNetworkError):
            await client.get_authenticated_user()

@pytest.mark.asyncio
async def test_10_headers_verification(client):
    mock_resp = httpx.Response(
        status_code=200, 
        json={"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": 1700000000}}}
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp) as mock_req:
        await client.get_rate_limit()
        headers = mock_req.call_args.kwargs["headers"]
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

@pytest.mark.asyncio
async def test_11_token_redacted_in_exceptions(client):
    mock_resp = httpx.Response(
        status_code=400,
        text=f"Error processing request with token {TEST_TOKEN}"
    )
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(GitHubAPIError) as exc_info:
            await client._request("GET", "/user")
        
        err_msg = str(exc_info.value)
        body_msg = str(exc_info.value.response_body)
        assert TEST_TOKEN not in err_msg
        assert TEST_TOKEN not in body_msg
        assert "[REDACTED_PAT]" in body_msg or "[REDACTED_TOKEN]" in body_msg
