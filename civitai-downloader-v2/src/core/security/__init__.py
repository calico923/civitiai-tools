#!/usr/bin/env python3
"""
Security module for CivitAI Downloader.
Provides malware detection, file validation, and security scanning capabilities.
"""

from .scanner import (
    SecurityScanner,
    ScanReport,
    SecurityIssue,
    ScanResult,
    ThreatType
)

__all__ = [
    'SecurityScanner',
    'ScanReport',
    'SecurityIssue',
    'ScanResult',
    'ThreatType'
]