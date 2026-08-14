import os
from typing import Optional, List

class GitHubConfig:
    """Configuration for GitHub Integration, OAuth Authentication & Token Vault."""

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[float] = None,
        encryption_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        authorize_url: Optional[str] = None,
        token_url: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[str] = None,
        frontend_redirect_url: Optional[str] = None,
        allowed_redirect_hosts: Optional[List[str]] = None,
    ):
        self.api_base_url = api_base_url or os.environ.get("GITHUB_API_BASE_URL", "https://api.github.com")
        self.api_version = api_version or os.environ.get("GITHUB_API_VERSION", "2022-11-28")
        self.timeout = timeout if timeout is not None else float(os.environ.get("GITHUB_HTTP_TIMEOUT", "20.0"))
        
        # Fallback to a safe random key for local development to prevent 503 errors if unconfigured
        default_key = os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY")
        if not default_key:
            import secrets
            default_key = secrets.token_hex(32)
        self.encryption_key = encryption_key or default_key
        
        # OAuth Configuration
        self.client_id = client_id or os.environ.get("GITHUB_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("GITHUB_CLIENT_SECRET", "")
        self.authorize_url = authorize_url or os.environ.get("GITHUB_AUTHORIZE_URL", "https://github.com/login/oauth/authorize")
        self.token_url = token_url or os.environ.get("GITHUB_TOKEN_URL", "https://github.com/login/oauth/access_token")
        self.redirect_uri = redirect_uri or os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:8000/api/v1/github/callback")
        self.scopes = scopes or os.environ.get("GITHUB_AUTH_SCOPES", "repo read:user")
        self.frontend_redirect_url = frontend_redirect_url or os.environ.get("GITHUB_FRONTEND_REDIRECT_URL", "http://localhost:8000/audit-code.html")
        self.allowed_redirect_hosts = allowed_redirect_hosts or ["localhost", "127.0.0.1"]

    def is_oauth_configured(self) -> bool:
        """Returns True if client_id and client_secret are provided."""
        return bool(self.client_id and self.client_secret)

    def __repr__(self) -> str:
        key_status = "SET" if self.encryption_key else "NOT_SET"
        secret_status = "SET" if self.client_secret else "NOT_SET"
        return (
            f"<GitHubConfig api_base_url='{self.api_base_url}' api_version='{self.api_version}' "
            f"timeout={self.timeout} client_id='{self.client_id}' client_secret={secret_status} "
            f"encryption_key={key_status}>"
        )
