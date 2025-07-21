#!/usr/bin/env python3
"""
Security module for CivitAI Downloader.
Implements requirements 9 and 14: Security scanning, license management, and privacy protection.
"""

from .license_manager import (
    LicenseManager,
    LicenseInfo,
    LicenseFilterConfig,
    LicenseType,
    LicenseStatus
)

from .security_scanner import (
    SecurityScanner,
    SecurityScanResult,
    FileIntegrityCheck,
    PrivacyAssessment,
    ScanStatus,
    HashAlgorithm,
    PrivacyRisk
)

# Legacy imports for backward compatibility
from .scanner import (
    SecurityScanner as LegacyScanner,
    ScanReport,
    SecurityIssue,
    ScanResult,
    ThreatType
)

__all__ = [
    # New security components (Phase 5)
    'LicenseManager',
    'LicenseInfo',
    'LicenseFilterConfig', 
    'LicenseType',
    'LicenseStatus',
    'SecurityScanner',
    'SecurityScanResult',
    'FileIntegrityCheck',
    'PrivacyAssessment',
    'ScanStatus',
    'HashAlgorithm',
    'PrivacyRisk',
    # Legacy components
    'LegacyScanner',
    'ScanReport',
    'SecurityIssue',
    'ScanResult',
    'ThreatType'
]