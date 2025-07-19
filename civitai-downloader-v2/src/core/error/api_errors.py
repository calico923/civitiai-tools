"""
API-specific error definitions.

This module defines custom exceptions for API-related errors,
providing better categorization and handling of different API failure modes.
"""

from typing import Optional, Dict, Any


class APIError(Exception):
    """Base class for all API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class APIConnectionError(APIError):
    """Error connecting to the API service."""
    pass


class APITimeoutError(APIError):
    """API request timed out."""
    pass


class APIRateLimitError(APIError):
    """API rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIAuthenticationError(APIError):
    """API authentication failed."""
    pass


class APIAuthorizationError(APIError):
    """API authorization failed (insufficient permissions)."""
    pass


class APINotFoundError(APIError):
    """Requested API resource not found."""
    pass


class APIValidationError(APIError):
    """API request validation failed."""
    
    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or {}


class APIServerError(APIError):
    """API server internal error."""
    pass


class APIUnavailableError(APIError):
    """API service temporarily unavailable."""
    pass


class APIResponseError(APIError):
    """API returned invalid or unexpected response."""
    
    def __init__(self, message: str, expected_format: Optional[str] = None, 
                 actual_response: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.expected_format = expected_format
        self.actual_response = actual_response


class APIDeprecatedError(APIError):
    """API endpoint or feature has been deprecated."""
    
    def __init__(self, message: str, deprecated_since: Optional[str] = None, 
                 alternative: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.deprecated_since = deprecated_since
        self.alternative = alternative