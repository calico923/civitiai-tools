#!/usr/bin/env python3
"""
Custom exceptions for CivitAI Downloader v2.
Provides specific exception types for better error handling and user experience.
"""


class CivitAIDownloaderError(Exception):
    """Base exception for all CivitAI Downloader errors."""
    pass


class SearchError(CivitAIDownloaderError):
    """Errors related to search operations."""
    pass


class APIError(CivitAIDownloaderError):
    """Errors related to API calls."""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
    
    def __str__(self):
        if self.status_code:
            return f"{super().__str__()} (HTTP {self.status_code})"
        return super().__str__()


class NetworkError(CivitAIDownloaderError):
    """Network-related errors."""
    pass


class AuthenticationError(CivitAIDownloaderError):
    """Authentication and authorization errors."""
    pass


class ValidationError(CivitAIDownloaderError):
    """Parameter validation errors."""
    pass


class DatabaseError(CivitAIDownloaderError):
    """Database operation errors."""
    pass


class FileError(CivitAIDownloaderError):
    """File operation errors."""
    pass


class DownloadError(CivitAIDownloaderError):
    """Download operation errors."""
    def __init__(self, message: str, url: str = None, file_path: str = None):
        super().__init__(message)
        self.url = url
        self.file_path = file_path
    
    def __str__(self):
        parts = [super().__str__()]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        return " - ".join(parts)


class ConfigError(CivitAIDownloaderError):
    """Configuration errors."""
    pass


class IntegrityError(CivitAIDownloaderError):
    """File integrity verification errors."""
    pass