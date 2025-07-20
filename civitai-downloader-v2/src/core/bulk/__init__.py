#!/usr/bin/env python3
"""
Bulk download module for CivitAI Downloader.
Provides batch download capabilities with advanced queue management.
"""

from .download_manager import (
    BulkDownloadManager,
    BulkDownloadJob,
    BulkStatus,
    BatchStrategy,
    BatchConfig,
    create_bulk_download_from_search,
    create_bulk_download_from_ids
)

__all__ = [
    'BulkDownloadManager',
    'BulkDownloadJob',
    'BulkStatus',
    'BatchStrategy',
    'BatchConfig',
    'create_bulk_download_from_search',
    'create_bulk_download_from_ids'
]