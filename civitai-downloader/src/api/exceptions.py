"""Custom exceptions for CivitAI API operations."""


class CivitAIError(Exception):
    """Base exception for CivitAI API errors."""
    pass


class NetworkError(CivitAIError):
    """Network-related errors."""
    pass


class APIError(CivitAIError):
    """CivitAI API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


class AuthenticationError(APIError):
    """Authentication failed."""
    pass


class ValidationError(CivitAIError):
    """Data validation error."""
    pass


class DownloadError(CivitAIError):
    """File download error."""
    pass


class StorageError(CivitAIError):
    """Local storage error."""
    pass