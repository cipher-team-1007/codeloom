from typing import Optional, Any

class GitHubError(Exception):
    """Base exception for all GitHub integration errors."""
    pass

class GitHubAPIError(GitHubError):
    """Raised when GitHub API responds with an HTTP error."""

    def __init__(self, message: str, status_code: int, response_body: Optional[str] = None):
        # Redact any accidental tokens in message/body
        sanitized_msg = GitHubAPIError._redact_secrets(message)
        sanitized_body = GitHubAPIError._redact_secrets(response_body) if response_body else None
        super().__init__(sanitized_msg)
        self.status_code = status_code
        self.response_body = sanitized_body

    @staticmethod
    def _redact_secrets(text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        import re
        # Redact Authorization header values or token patterns (ghp_, gho_, ghu_, ghs_)
        redacted = re.sub(r'ghp_[A-Za-z0-9_]+', '[REDACTED_PAT]', text)
        redacted = re.sub(r'gho_[A-Za-z0-9_]+', '[REDACTED_OAUTH]', redacted)
        redacted = re.sub(r'ghu_[A-Za-z0-9_]+', '[REDACTED_USER_TOKEN]', redacted)
        redacted = re.sub(r'ghs_[A-Za-z0-9_]+', '[REDACTED_INSTALLATION_TOKEN]', redacted)
        redacted = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED_TOKEN]', redacted)
        return redacted

class GitHubAuthenticationError(GitHubAPIError):
    """Raised when GitHub API authentication fails (401 Bad Credentials)."""
    def __init__(self, message: str = "GitHub authentication failed.", status_code: int = 401, response_body: Optional[str] = None):
        super().__init__(message, status_code, response_body)

class GitHubAuthorizationError(GitHubAPIError):
    """Raised when GitHub API authorization fails (403 Permission Denied / Scope issue)."""
    def __init__(self, message: str = "GitHub permission denied.", status_code: int = 403, response_body: Optional[str] = None):
        super().__init__(message, status_code, response_body)

class GitHubNotFoundError(GitHubAPIError):
    """Raised when GitHub resource is not found (404 Not Found)."""
    def __init__(self, message: str = "GitHub resource not found.", status_code: int = 404, response_body: Optional[str] = None):
        super().__init__(message, status_code, response_body)

class GitHubConflictError(GitHubAPIError):
    """Raised on 409 Conflict (e.g. branch or ref collision)."""
    def __init__(self, message: str = "GitHub resource conflict.", status_code: int = 409, response_body: Optional[str] = None):
        super().__init__(message, status_code, response_body)

class GitHubValidationError(GitHubAPIError):
    """Raised on 422 Unprocessable Entity (e.g. invalid params)."""
    def __init__(self, message: str = "GitHub request validation failed.", status_code: int = 422, response_body: Optional[str] = None):
        super().__init__(message, status_code, response_body)

class GitHubRateLimitError(GitHubAPIError):
    """Raised on 429 / 403 Rate Limit Exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded.",
        status_code: int = 429,
        reset_timestamp: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        super().__init__(message, status_code, response_body)
        self.reset_timestamp = reset_timestamp
        self.limit = limit
        self.remaining = remaining

class GitHubTimeoutError(GitHubError):
    """Raised when a request to GitHub API times out."""
    pass

class GitHubNetworkError(GitHubError):
    """Raised on network / connectivity failure to GitHub API."""
    pass

# Vault Exceptions
class CredentialVaultError(GitHubError):
    """Base exception for token vault operations."""
    pass

class EncryptionKeyMissingError(CredentialVaultError):
    """Raised when GITHUB_TOKEN_ENCRYPTION_KEY is missing or invalid."""
    pass

class DecryptionError(CredentialVaultError):
    """Raised when token decryption fails (corrupted ciphertext or wrong key)."""
    pass

class CredentialExpiredError(CredentialVaultError):
    """Raised when an access token has passed its expiration time."""
    pass

# Authentication & Connection Flow Exceptions
class GitHubAuthError(GitHubError):
    """Base exception for OAuth / connection flow errors."""
    pass

class GitHubAuthNotConfiguredError(GitHubAuthError):
    """Raised when GitHub OAuth Client ID or Client Secret is missing."""
    pass

class GitHubAuthorizationDeniedError(GitHubAuthError):
    """Raised when user cancels or denies GitHub OAuth authorization."""
    pass

class GitHubInvalidStateError(GitHubAuthError):
    """Raised when OAuth state is invalid, mismatched, missing, or reused (CSRF violation)."""
    pass

class GitHubStateExpiredError(GitHubAuthError):
    """Raised when OAuth state has passed its expiration TTL."""
    pass

class GitHubTokenExchangeError(GitHubAuthError):
    """Raised when exchanging authorization code with GitHub token endpoint fails."""
    pass

class GitHubIdentityLookupError(GitHubAuthError):
    """Raised when querying authenticated user profile from GitHub API fails."""
    pass

class GitHubOpenRedirectError(GitHubAuthError):
    """Raised when an unauthorized redirect destination is requested."""
    pass

# Publication & Delivery Flow Exceptions
class PublicationError(GitHubError):
    """Base exception for verified patch publication errors."""
    pass

class RemediationNotFoundError(PublicationError):
    """Raised when the specified remediation ID does not exist in authoritative store."""
    pass

class RemediationNotVerifiedError(PublicationError):
    """Raised when attempting to publish a remediation whose status is not VERIFIED."""
    pass

class InvalidPatchFingerprintError(PublicationError):
    """Raised when the recomputed patch fingerprint does not match the authoritative report."""
    pass

class BaseCommitStaleError(PublicationError):
    """Raised when the remote target branch has advanced past the verified base commit SHA (TOCTOU)."""
    pass

class PatchApplicationError(PublicationError):
    """Raised when applying the unified diff to the base file fails."""
    pass

class GitHubBranchCreationError(PublicationError):
    """Raised when creating a remote branch reference fails."""
    pass

class GitHubCommitCreationError(PublicationError):
    """Raised when creating a Git blob/tree/commit object fails."""
    pass

class GitHubPullRequestCreationError(PublicationError):
    """Raised when creating a GitHub Pull Request fails."""
    pass

