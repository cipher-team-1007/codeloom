from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field

class TokenType(str, Enum):
    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    GITHUB_APP_USER_TOKEN = "github_app_user_token"
    GITHUB_APP_INSTALLATION_TOKEN = "github_app_installation_token"
    FINE_GRAINED_PAT = "fine_grained_pat"

class GitHubCredential(BaseModel):
    """
    Model representing a stored GitHub credential metadata and its encrypted payload.
    The raw secret token is NEVER exposed in repr, str, or standard JSON dumps.
    """
    credential_id: str = Field(description="Unique credential identifier")
    token_type: TokenType = Field(default=TokenType.OAUTH_ACCESS_TOKEN)
    account_login: Optional[str] = Field(default=None, description="GitHub user login associated with credential")
    installation_id: Optional[int] = Field(default=None, description="GitHub App Installation ID if applicable")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time if token is temporary")
    scopes: List[str] = Field(default_factory=list, description="Granted OAuth scopes or App permissions")
    
    # Encrypted payload containing the secret token (Base64 AES-256-GCM string)
    encrypted_secret: Optional[str] = Field(default=None, exclude=True, description="AES-256-GCM encrypted token string")

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        # Normalize comparison to timezone-aware if needed
        now = datetime.now(timezone.utc)
        target = self.expires_at if self.expires_at.tzinfo is not None else self.expires_at.replace(tzinfo=timezone.utc)
        return now >= target

    def __repr__(self) -> str:
        return (
            f"GitHubCredential(id='{self.credential_id}', type='{self.token_type.value}', "
            f"account='{self.account_login}', scopes={self.scopes}, token=***REDACTED***)"
        )

    def __str__(self) -> str:
        return self.__repr__()

class GitHubUser(BaseModel):
    login: str
    id: int
    avatar_url: Optional[str] = None
    html_url: str
    name: Optional[str] = None
    email: Optional[str] = None

class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    owner_login: str
    clone_url: str
    default_branch: str = "main"
    is_private: bool = False
    html_url: str

class GitHubBranch(BaseModel):
    name: str
    commit_sha: str

class GitHubCommit(BaseModel):
    sha: str
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    committed_date: Optional[str] = None

class GitHubRateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_timestamp: int

class PublicationStatus(str, Enum):
    READY = "READY"
    PRECHECKING = "PRECHECKING"
    BASE_SHA_VERIFIED = "BASE_SHA_VERIFIED"
    BRANCH_CREATING = "BRANCH_CREATING"
    PATCH_APPLYING = "PATCH_APPLYING"
    COMMIT_CREATING = "COMMIT_CREATING"
    PUSHING = "PUSHING"
    PR_CREATING = "PR_CREATING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

class PublicationResult(BaseModel):
    status: str = Field(default="PUBLISHED", description="Publication status")
    remediation_id: str = Field(description="Remediation identifier")
    repository: str = Field(description="Target repository 'owner/repo'")
    target_repository_url: Optional[str] = Field(default=None, description="Full GitHub HTTPS repository URL")
    base_branch: Optional[str] = Field(default="main", description="Target base branch for PR merge")
    branch: str = Field(description="Created remote branch name")
    commit_sha: str = Field(description="Created commit SHA")
    pull_request_url: str = Field(description="URL of opened Pull Request")
    pull_request_number: Optional[int] = Field(default=None, description="Pull Request number")
    files_changed: List[str] = Field(default_factory=list, description="Target source files modified")
    pr_title: Optional[str] = Field(default=None, description="Title of the created Pull Request")
    pr_description_summary: Optional[str] = Field(default=None, description="Formatted description summary")
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


