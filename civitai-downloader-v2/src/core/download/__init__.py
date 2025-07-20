#!/usr/bin/env python3
"""
Download module for CivitAI Downloader.
Provides concurrent downloads with resume capability, progress tracking, and integrity verification.
"""

from .manager import (
    DownloadManager,
    DownloadTask,
    FileInfo,
    ProgressUpdate,
    DownloadStatus,
    DownloadPriority,
    download_model_file,
    create_file_info_from_api
)

__all__ = [
    'DownloadManager',
    'DownloadTask',
    'FileInfo',
    'ProgressUpdate',
    'DownloadStatus',
    'DownloadPriority',
    'download_model_file',
    'create_file_info_from_api'
]