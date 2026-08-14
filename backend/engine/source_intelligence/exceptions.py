class SourceIntelligenceError(Exception):
    """Base exception for Source Intelligence integration."""
    pass


class SourceIntelligenceConnectionError(SourceIntelligenceError):
    """Raised when the Node.js service cannot be reached."""
    pass


class SourceIntelligenceTimeoutError(SourceIntelligenceError):
    """Raised when the Node.js service does not respond in time."""
    pass


class SourceIntelligenceAPIError(SourceIntelligenceError):
    """Raised when the Node.js service returns an HTTP error (4xx/5xx)."""
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SourceIntelligenceMalformedResponseError(SourceIntelligenceError):
    """Raised when the Node.js service returns an invalid or unparseable response."""
    pass
