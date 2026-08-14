from typing import Optional
from pydantic import BaseModel, HttpUrl

class RepositoryCoordinate(BaseModel):
    """Identifies the source repository and the requested revision."""
    repository_url: str
    requested_commit_sha: str
    provider: str = "git"  # Extensible for future providers

class SourceSnapshot(BaseModel):
    """Represents a verified, immutable local checkout of a repository."""
    local_path: str
    commit_sha: str
    repository_identity: str
