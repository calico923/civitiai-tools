#!/usr/bin/env python3
"""
Security module for CivitAI Downloader.
Implements requirements 9, 14, and 18: Security scanning, license management, privacy protection, and enhanced security.
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

# Phase 6.3: Enhanced Security Components
from .audit import SecurityAuditor, AuditEvent, AuditLevel
from .sandbox import SecureSandbox, SandboxConfig
from .encryption import DataEncryption, EncryptionLevel
from .access_control import AccessController, Permission, SecurityPolicy

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
    'ThreatType',
    # Phase 6.3: Enhanced Security
    'SecurityAuditor',
    'AuditEvent',
    'AuditLevel',
    'SecureSandbox',
    'SandboxConfig',
    'DataEncryption',
    'EncryptionLevel',
    'AccessController',
    'Permission',
    'SecurityPolicy'
]