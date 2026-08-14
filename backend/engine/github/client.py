import re
import httpx
import logging
from typing import Optional, List, Dict, Any

from .config import GitHubConfig
from .models import (
    GitHubUser,
    GitHubRepository,
    GitHubBranch,
    GitHubCommit,
    GitHubRateLimitInfo,
    GitHubCredential,
)
from .exceptions import (
    GitHubError,
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

logger = logging.getLogger("codeloom.github.client")

class GitHubClient:
    """
    Async REST Client for GitHub API v3/v4 interactions.
    Handles transport, authentication headers, error classification, 
    rate limits, and secret redaction.
    """

    def __init__(
        self,
        config: Optional[GitHubConfig] = None,
        access_token: Optional[str] = None,
        credential: Optional[GitHubCredential] = None,
        vault_secret_token: Optional[str] = None,
    ):
        self.config = config or GitHubConfig()
        self.base_url = self.config.api_base_url.rstrip("/")
        self.api_version = self.config.api_version
        self.timeout = self.config.timeout
        
        # Token extraction
        self._token = access_token or vault_secret_token
        if not self._token and credential and hasattr(credential, "_raw_secret"):
            self._token = getattr(credential, "_raw_secret")

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "CodeLoom-Engine/1.0",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )

            # Check rate limits
            self._check_rate_limit_headers(response)

            if response.is_error:
                self._handle_error_response(response)

            return response

        except httpx.TimeoutException as e:
            logger.error("GitHub request timed out after %.1fs to %s", self.timeout, endpoint)
            raise GitHubTimeoutError(f"Request to GitHub endpoint '{endpoint}' timed out.") from e

        except httpx.ConnectError as e:
            logger.error("GitHub connection failed to %s: %s", endpoint, e)
            raise GitHubNetworkError(f"Failed to connect to GitHub endpoint '{endpoint}'.") from e

        except Exception as e:
            if isinstance(e, GitHubError):
                raise
            logger.error("Unexpected GitHub client error: %s", e)
            raise GitHubError(f"Unexpected error communicating with GitHub API: {e}") from e

    def _check_rate_limit_headers(self, response: httpx.Response) -> None:
        remaining_str = response.headers.get("x-ratelimit-remaining")
        reset_str = response.headers.get("x-ratelimit-reset")
        limit_str = response.headers.get("x-ratelimit-limit")

        if remaining_str is not None and remaining_str == "0":
            limit = int(limit_str) if limit_str and limit_str.isdigit() else 0
            remaining = int(remaining_str) if remaining_str and remaining_str.isdigit() else 0
            reset = int(reset_str) if reset_str and reset_str.isdigit() else 0
            raise GitHubRateLimitError(
                message="GitHub API rate limit exceeded.",
                status_code=response.status_code,
                reset_timestamp=reset,
                limit=limit,
                remaining=remaining,
                response_body=response.text,
            )

    def _handle_error_response(self, response: httpx.Response) -> None:
        status = response.status_code
        text = response.text

        # Sanitize body before exception construction
        sanitized_body = GitHubAPIError._redact_secrets(text)

        if status == 401:
            raise GitHubAuthenticationError(
                message="Bad GitHub credentials or invalid token.",
                status_code=401,
                response_body=sanitized_body,
            )
        elif status == 403:
            if "rate limit" in text.lower():
                raise GitHubRateLimitError(
                    message="GitHub API rate limit exceeded.",
                    status_code=403,
                    response_body=sanitized_body,
                )
            raise GitHubAuthorizationError(
                message="Resource permission denied by GitHub API.",
                status_code=403,
                response_body=sanitized_body,
            )
        elif status == 404:
            raise GitHubNotFoundError(
                message="GitHub resource not found.",
                status_code=404,
                response_body=sanitized_body,
            )
        elif status == 409:
            raise GitHubConflictError(
                message="GitHub resource conflict.",
                status_code=409,
                response_body=sanitized_body,
            )
        elif status == 422:
            raise GitHubValidationError(
                message="GitHub API payload validation failed.",
                status_code=422,
                response_body=sanitized_body,
            )
        else:
            raise GitHubAPIError(
                message=f"GitHub API returned HTTP status {status}.",
                status_code=status,
                response_body=sanitized_body,
            )

    async def get_authenticated_user(self) -> GitHubUser:
        """Retrieves details of the currently authenticated user (`GET /user`)."""
        response = await self._request("GET", "/user")
        data = response.json()
        return GitHubUser(
            login=data["login"],
            id=data["id"],
            avatar_url=data.get("avatar_url"),
            html_url=data.get("html_url", ""),
            name=data.get("name"),
            email=data.get("email"),
        )

    async def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        """Retrieves details of a specific repository (`GET /repos/{owner}/{repo}`)."""
        response = await self._request("GET", f"/repos/{owner}/{repo}")
        data = response.json()
        return GitHubRepository(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            owner_login=data["owner"]["login"],
            clone_url=data["clone_url"],
            default_branch=data.get("default_branch", "main"),
            is_private=data.get("private", False),
            html_url=data.get("html_url", ""),
        )

    async def list_user_repositories(self, visibility: str = "all") -> List[GitHubRepository]:
        """Lists repositories accessible to authenticated user (`GET /user/repos`)."""
        response = await self._request("GET", "/user/repos", params={"visibility": visibility, "per_page": 100})
        data = response.json()
        return [
            GitHubRepository(
                id=item["id"],
                name=item["name"],
                full_name=item["full_name"],
                owner_login=item["owner"]["login"],
                clone_url=item["clone_url"],
                default_branch=item.get("default_branch", "main"),
                is_private=item.get("private", False),
                html_url=item.get("html_url", ""),
            )
            for item in data
        ]

    async def get_branch(self, owner: str, repo: str, branch_name: str) -> GitHubBranch:
        """Retrieves a specific branch (`GET /repos/{owner}/{repo}/branches/{branch}`)."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/branches/{branch_name}")
        data = response.json()
        return GitHubBranch(
            name=data["name"],
            commit_sha=data["commit"]["sha"],
        )

    async def get_commit(self, owner: str, repo: str, commit_sha: str) -> GitHubCommit:
        """Retrieves a single commit (`GET /repos/{owner}/{repo}/commits/{sha}`)."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/commits/{commit_sha}")
        data = response.json()
        commit_info = data.get("commit", {})
        author_info = commit_info.get("author", {})
        return GitHubCommit(
            sha=data["sha"],
            message=commit_info.get("message", ""),
            author_name=author_info.get("name"),
            author_email=author_info.get("email"),
            committed_date=author_info.get("date"),
        )

    async def get_rate_limit(self) -> GitHubRateLimitInfo:
        """Retrieves rate limit status (`GET /rate_limit`)."""
        response = await self._request("GET", "/rate_limit")
        data = response.json()
        core = data["resources"]["core"]
        return GitHubRateLimitInfo(
            limit=core["limit"],
            remaining=core["remaining"],
            reset_timestamp=core["reset"],
        )

    # Git Data & Pull Request API Methods for Publication

    async def get_file_content(self, owner: str, repo: str, file_path: str, ref: str) -> str:
        """Retrieves file content from repository at a specific ref/commit SHA (`GET /repos/{owner}/{repo}/contents/{file_path}`)."""
        import base64
        clean_path = file_path.lstrip("/")
        response = await self._request("GET", f"/repos/{owner}/{repo}/contents/{clean_path}", params={"ref": ref})
        data = response.json()
        raw_content = data.get("content", "")
        encoding = data.get("encoding", "")
        if encoding == "base64":
            return base64.b64decode(raw_content).decode("utf-8")
        return raw_content

    async def get_commit_tree_sha(self, owner: str, repo: str, commit_sha: str) -> str:
        """Retrieves the tree SHA associated with a commit (`GET /repos/{owner}/{repo}/git/commits/{commit_sha}`)."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/git/commits/{commit_sha}")
        data = response.json()
        return data["tree"]["sha"]

    async def create_blob(self, owner: str, repo: str, content: str) -> str:
        """Creates a new Git blob object (`POST /repos/{owner}/{repo}/git/blobs`)."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json_data={"content": content, "encoding": "utf-8"}
        )
        data = response.json()
        return data["sha"]

    async def create_tree(self, owner: str, repo: str, base_tree_sha: str, tree_items: List[Dict[str, Any]]) -> str:
        """Creates a new Git tree object based on an existing tree (`POST /repos/{owner}/{repo}/git/trees`)."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json_data={"base_tree": base_tree_sha, "tree": tree_items}
        )
        data = response.json()
        return data["sha"]

    async def create_commit_object(self, owner: str, repo: str, message: str, tree_sha: str, parents: List[str]) -> str:
        """Creates a new Git commit object (`POST /repos/{owner}/{repo}/git/commits`)."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json_data={"message": message, "tree": tree_sha, "parents": parents}
        )
        data = response.json()
        return data["sha"]

    async def create_reference(self, owner: str, repo: str, ref: str, sha: str) -> Dict[str, Any]:
        """Creates a new Git reference (e.g. branch) (`POST /repos/{owner}/{repo}/git/refs`)."""
        clean_ref = ref if ref.startswith("refs/") else f"refs/heads/{ref}"
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json_data={"ref": clean_ref, "sha": sha}
        )
        return response.json()

    async def get_reference(self, owner: str, repo: str, ref: str) -> Optional[Dict[str, Any]]:
        """Retrieves a Git reference (`GET /repos/{owner}/{repo}/git/ref/{ref}`). Returns None if 404."""
        clean_ref = ref if not ref.startswith("refs/") else ref[len("refs/"):]
        try:
            response = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/{clean_ref}")
            return response.json()
        except GitHubNotFoundError:
            return None

    async def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        """Creates a Pull Request (`POST /repos/{owner}/{repo}/pulls`)."""
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json_data={"title": title, "body": body, "head": head, "base": base}
        )
        return response.json()

    async def list_pull_requests(self, owner: str, repo: str, head: Optional[str] = None, state: str = "open") -> List[Dict[str, Any]]:
        """Lists Pull Requests filtered by head branch (`GET /repos/{owner}/{repo}/pulls`)."""
        params: Dict[str, Any] = {"state": state}
        if head:
            params["head"] = f"{owner}:{head}" if ":" not in head else head
        response = await self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
        return response.json()

    def __repr__(self) -> str:
        token_status = "AUTHENTICATED" if self._token else "UNAUTHENTICATED"
        return f"<GitHubClient base_url='{self.base_url}' status={token_status}>"

