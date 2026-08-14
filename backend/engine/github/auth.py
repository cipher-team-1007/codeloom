import os
import time
import secrets
import logging
from urllib.parse import urlencode, urlparse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, List
import httpx

from .config import GitHubConfig
from .vault import TokenVault
from .client import GitHubClient
from .models import GitHubCredential, TokenType
from .exceptions import (
    GitHubAuthNotConfiguredError,
    GitHubAuthorizationDeniedError,
    GitHubInvalidStateError,
    GitHubStateExpiredError,
    GitHubTokenExchangeError,
    GitHubIdentityLookupError,
    GitHubOpenRedirectError,
)

logger = logging.getLogger("codeloom.github.auth")

class GitHubAuthManager:
    """
    Manages GitHub OAuth authorization requests, CSRF state protection,
    server-side code exchange, user identity binding, and connection lifecycle.
    """

    STATE_TTL_SECONDS = 600  # 10 minutes

    def __init__(self, config: Optional[GitHubConfig] = None, vault: Optional[TokenVault] = None):
        self.config = config or GitHubConfig()
        self.vault = vault or TokenVault(encryption_key=self.config.encryption_key)
        # In-memory storage for active CSRF states: state -> {session_id, created_at, redirect_url}
        self._state_store: Dict[str, Dict[str, Any]] = {}
        # In-memory storage for session profile metadata: session_id -> {login, user_id, avatar_url}
        self._connections_store: Dict[str, Dict[str, Any]] = {}

    def _validate_redirect_url(self, target_url: str) -> None:
        """Validates that a custom redirect destination matches allowed hosts or relative path."""
        if not target_url:
            return
        parsed = urlparse(target_url)
        # Allow relative paths (e.g. "/app" or "/app?github=connected")
        if not parsed.netloc:
            return
        # If absolute URL, check hostname
        hostname = parsed.hostname
        if hostname not in self.config.allowed_redirect_hosts:
            logger.warning("Rejected open redirect attempt to hostname: %s", hostname)
            raise GitHubOpenRedirectError(f"Redirect destination host '{hostname}' is not authorized.")

    def generate_authorization_url(
        self,
        session_id: str,
        custom_redirect: Optional[str] = None
    ) -> str:
        """
        Generates a secure OAuth authorization URL with a single-use random CSRF state.
        """
        if not self.config.is_oauth_configured():
            raise GitHubAuthNotConfiguredError(
                "GitHub OAuth is not configured. Missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET."
            )

        target_redirect = custom_redirect or self.config.frontend_redirect_url
        self._validate_redirect_url(target_redirect)

        # Generate cryptographically strong random state token
        state = secrets.token_urlsafe(32)
        self._state_store[state] = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc),
            "redirect_url": target_redirect,
        }

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scopes,
            "state": state,
            "allow_signup": "true",
        }
        auth_url = f"{self.config.authorize_url}?{urlencode(params)}"
        logger.info("Generated OAuth authorization URL for session ID: %s", session_id[:8] + "...")
        return auth_url

    def validate_and_consume_state(self, state: Optional[str]) -> Dict[str, Any]:
        """
        Validates the state parameter and immediately consumes it to prevent replay attacks.
        """
        if not state or state not in self._state_store:
            logger.warning("CSRF validation failed: Missing or unrecognized state token.")
            raise GitHubInvalidStateError("Invalid or missing OAuth state parameter.")

        state_data = self._state_store.pop(state)
        created_at: datetime = state_data["created_at"]
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()

        if age_seconds > self.STATE_TTL_SECONDS:
            logger.warning("OAuth state expired (age: %.1fs, ttl: %ds).", age_seconds, self.STATE_TTL_SECONDS)
            raise GitHubStateExpiredError("OAuth state has expired. Please initiate authentication again.")

        return state_data

    async def exchange_code(self, code: Optional[str]) -> Dict[str, Any]:
        """
        Performs server-side token exchange with GitHub token endpoint.
        """
        if not code:
            raise GitHubTokenExchangeError("Authorization code is missing.")

        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "CodeLoom-Engine/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as http_client:
                response = await http_client.post(
                    self.config.token_url,
                    json=payload,
                    headers=headers,
                )

            data = response.json()
            if "error" in data:
                err_type = data.get("error", "token_exchange_failed")
                err_desc = data.get("error_description", "Unknown error exchanging authorization code.")
                logger.error("GitHub token exchange error: %s - %s", err_type, err_desc)
                raise GitHubTokenExchangeError(f"GitHub token exchange failed: {err_desc}")

            access_token = data.get("access_token")
            if not access_token:
                raise GitHubTokenExchangeError("GitHub response did not contain an access token.")

            return data

        except Exception as e:
            if isinstance(e, GitHubTokenExchangeError):
                raise
            logger.error("Network or parsing error during GitHub token exchange: %s", e)
            raise GitHubTokenExchangeError(f"Failed to communicate with GitHub token endpoint: {e}") from e

    async def process_callback(
        self,
        code: Optional[str],
        state: Optional[str],
        error: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> Tuple[GitHubCredential, str]:
        """
        Processes the complete OAuth redirect callback: validates state, exchanges code,
        queries user profile, stores encrypted credential in vault, and returns target redirect URL.
        """
        if error:
            logger.warning("OAuth authorization denied by user: %s (%s)", error, error_description)
            raise GitHubAuthorizationDeniedError(f"GitHub authorization was denied: {error_description or error}")

        # Validate and consume state token
        state_data = self.validate_and_consume_state(state)
        session_id = state_data["session_id"]
        redirect_url = state_data["redirect_url"]

        # Exchange code for access token
        token_data = await self.exchange_code(code)
        raw_access_token = token_data["access_token"]
        raw_scope = token_data.get("scope", "")
        scopes_list = [s.strip() for s in raw_scope.split(",") if s.strip()] if raw_scope else []

        # Query authenticated user profile
        try:
            gh_client = GitHubClient(config=self.config, access_token=raw_access_token)
            user = await gh_client.get_authenticated_user()
        except Exception as e:
            logger.error("Failed to query authenticated GitHub user identity: %s", e)
            raise GitHubIdentityLookupError(f"Failed to retrieve user profile from GitHub: {e}") from e

        # Construct and encrypt credential
        credential = GitHubCredential(
            credential_id=session_id,
            token_type=TokenType.OAUTH_ACCESS_TOKEN,
            account_login=user.login,
            scopes=scopes_list,
        )
        self.vault.store_credential(credential, raw_secret=raw_access_token)

        # Store session profile metadata
        self._connections_store[session_id] = {
            "login": user.login,
            "user_id": user.id,
            "avatar_url": user.avatar_url,
            "connected_at": datetime.now(timezone.utc),
        }

        logger.info("Successfully established GitHub connection for user '%s' (session %s)", user.login, session_id[:8])
        return credential, redirect_url

    def get_connection_status(self, session_id: Optional[str]) -> Dict[str, Any]:
        """
        Returns safe non-sensitive connection status metadata for a session ID.
        Strictly enforces session isolation: OAuth tokens belong only to their session.
        """
        is_oauth_cfg = self.config.is_oauth_configured() and not self.config.client_id.startswith("test_")

        if session_id:
            cred = self.vault.get_credential(session_id)
            if cred and not cred.is_expired():
                profile = self._connections_store.get(session_id, {})
                return {
                    "connected": True,
                    "oauth_configured": is_oauth_cfg,
                    "github_login": cred.account_login,
                    "account_login": cred.account_login,
                    "github_user_id": profile.get("user_id"),
                    "avatar_url": profile.get("avatar_url") or f"https://github.com/{cred.account_login}.png",
                    "scopes": cred.scopes,
                    "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                    "is_demo_fallback": False,
                }

        return {
            "connected": False,
            "oauth_configured": is_oauth_cfg,
            "github_login": None,
            "account_login": None,
            "github_user_id": None,
            "scopes": [],
            "expires_at": None,
            "is_demo_fallback": False,
        }

    def disconnect(self, session_id: Optional[str]) -> bool:
        """
        Removes the stored credential and connection session.
        Idempotent: Returns True if removed, False if already disconnected.
        """
        if not session_id:
            return False

        vault_deleted = self.vault.delete_credential(session_id)
        session_deleted = bool(self._connections_store.pop(session_id, None))
        
        if vault_deleted or session_deleted:
            logger.info("Disconnected GitHub connection for session: %s", session_id[:8])
            return True
        return False

    async def connect_with_token(self, session_id: str, raw_token: str) -> Tuple[GitHubCredential, Dict[str, Any]]:
        """
        Authenticates a user via GitHub Personal Access Token (PAT) or OAuth token.
        Queries profile from GitHub REST API, encrypts token into vault, and returns metadata.
        """
        raw_token = raw_token.strip()
        if not raw_token:
            raise ValueError("GitHub token is empty.")

        gh_client = GitHubClient(config=self.config, access_token=raw_token)
        try:
            user = await gh_client.get_authenticated_user()
        except Exception as e:
            logger.error("Failed to authenticate token with GitHub API: %s", e)
            raise ValueError(f"Invalid or expired GitHub token: {e}") from e

        credential = GitHubCredential(
            credential_id=session_id,
            token_type=TokenType.PERSONAL_ACCESS_TOKEN if raw_token.startswith("ghp_") else TokenType.OAUTH_ACCESS_TOKEN,
            account_login=user.login,
            scopes=["repo", "read:user"],
        )
        self.vault.store_credential(credential, raw_secret=raw_token)

        profile = {
            "login": user.login,
            "user_id": user.id,
            "avatar_url": user.avatar_url,
            "connected_at": datetime.now(timezone.utc),
        }
        self._connections_store[session_id] = profile

        logger.info("Successfully connected GitHub PAT token for user '%s' (session %s)", user.login, session_id[:8])
        return credential, profile

    async def get_user_repositories(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Fetches authentic repositories for the connected user session.
        Enforces strict multi-user session isolation: only returns repos for the active session.
        """
        raw_token = None
        if session_id:
            try:
                raw_token = self.vault.retrieve_secret(session_id)
            except Exception:
                raw_token = None
        
        if not raw_token:
            logger.info("No active session token found for session %s. Returning empty repo list.", (session_id or 'unknown')[:8])
            return []

        # Fast in-memory cache check (60s TTL)
        if not hasattr(self, "_repo_cache"):
            self._repo_cache = {}
        now = time.time()
        cached = self._repo_cache.get(session_id)
        if cached and (now - cached["timestamp"] < 60.0):
            return cached["repos"]

        headers = {
            "Authorization": f"Bearer {raw_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeLoom-Engine/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get("https://api.github.com/user/repos?sort=updated&per_page=50", headers=headers)
                if res.status_code == 200:
                    repos = res.json()
                    result = []
                    for r in repos:
                        result.append({
                            "name": r.get("name"),
                            "full_name": r.get("full_name"),
                            "html_url": r.get("html_url"),
                            "clone_url": r.get("clone_url"),
                            "default_branch": r.get("default_branch", "main"),
                            "private": r.get("private", False),
                            "owner": r.get("owner", {}).get("login"),
                        })
                    self._repo_cache[session_id] = {"timestamp": now, "repos": result}
                    return result
        except Exception as e:
            logger.warning("Failed to fetch user repositories from GitHub API: %s", e)

        return []

