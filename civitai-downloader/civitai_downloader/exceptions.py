"""Custom exceptions for CivitAI downloader."""

from typing import Optional


class CivitAIError(Exception):
    """Base exception for CivitAI downloader errors."""
    pass


class APIError(CivitAIError):
    """API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class NetworkError(APIError):
    """Network-related errors."""
    pass


class RateLimitError(APIError):
    """Rate limit errors."""
    
    def __init__(self, retry_after: Optional[int] = None):
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class ValidationError(CivitAIError):
    """Data validation errors."""
    pass


class SessionError(CivitAIError):
    """Session management errors."""
    pass


class TimeoutError(CivitAIError):
    """Request timeout errors."""
    pass


class ParseError(CivitAIError):
    """Data parsing errors."""
    pass