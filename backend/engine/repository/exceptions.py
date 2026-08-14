class RepositoryError(Exception):
    """Base exception for repository acquisition."""
    pass

class InvalidRepositoryURLError(RepositoryError):
    """Raised when the repository URL scheme or format is unsupported or invalid."""
    pass

class UnsupportedRepositoryProviderError(RepositoryError):
    """Raised when the requested provider is not supported."""
    pass

class RepositoryAcquisitionFailedError(RepositoryError):
    """Raised when cloning or fetching the repository fails."""
    pass

class RepositoryNotFoundError(RepositoryError):
    """Raised when the remote repository cannot be found (e.g., 404)."""
    pass

class CommitNotFoundError(RepositoryError):
    """Raised when the requested commit SHA does not exist in the repository."""
    pass

class CheckoutFailedError(RepositoryError):
    """Raised when checking out the commit fails."""
    pass

class CommitIntegrityFailureError(RepositoryError):
    """Raised when the checked out HEAD does not match the requested commit SHA."""
    pass

class WorkspaceFailureError(RepositoryError):
    """Raised when creating or preparing the temporary workspace fails."""
    pass

class RepositoryTimeoutError(RepositoryError):
    """Raised when repository operations exceed the allowed time limit."""
    pass
