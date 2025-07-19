"""
SecurityChecker - Abstract interface for security analysis implementations.

This module defines the abstract base class for implementing security checks
on models, including license analysis, security scanning, and privacy risk assessment.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WarningType(Enum):
    """Security warning types."""
    VIRUS_DETECTED = "virus_detected"
    PICKLE_UNSAFE = "pickle_unsafe"
    LICENSE_RESTRICTION = "license_restriction"
    PRIVACY_CONCERN = "privacy_concern"
    CELEBRITY_CONTENT = "celebrity_content"
    NSFW_CONTENT = "nsfw_content"
    SUSPICIOUS_METADATA = "suspicious_metadata"


@dataclass
class LicenseInfo:
    """License information for a model."""
    allow_commercial_use: List[str]
    allow_derivatives: bool
    allow_different_license: bool
    allow_no_credit: bool
    license_name: Optional[str] = None
    license_url: Optional[str] = None


@dataclass
class SecurityScanResult:
    """Security scan results for model files."""
    virus_scan_result: str
    virus_scan_message: Optional[str]
    pickle_scan_result: str
    pickle_scan_message: Optional[str]
    scanned_at: datetime
    scan_engine: Optional[str] = None


@dataclass
class PrivacyRiskAssessment:
    """Privacy risk assessment for model content."""
    contains_celebrity: bool
    contains_personal_data: bool
    nsfw_level: str
    privacy_risk_score: float  # 0.0 to 1.0
    privacy_warnings: List[str]


@dataclass
class SecurityWarning:
    """Security warning for user notification."""
    warning_type: WarningType
    risk_level: RiskLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False


@dataclass
class SecurityAnalysis:
    """Complete security analysis result."""
    license_info: LicenseInfo
    security_scans: SecurityScanResult
    privacy_risks: PrivacyRiskAssessment
    warnings: List[SecurityWarning]
    overall_risk_level: RiskLevel
    safe_to_download: bool


class SecurityChecker(ABC):
    """
    Abstract base class for security checking implementations.
    
    This interface defines the contract for implementing security analysis
    of models, including license checking, security scanning, and privacy assessment.
    """
    
    @abstractmethod
    def check_security(self, model_data: Dict[str, Any]) -> SecurityAnalysis:
        """
        Perform comprehensive security check on model data.
        
        Args:
            model_data: Complete model information dictionary
            
        Returns:
            SecurityAnalysis with all security findings
            
        Raises:
            SecurityError: If security check fails
            ValidationError: If model data is invalid
        """
        pass
    
    @abstractmethod
    def analyze_license(self, model_data: Dict[str, Any]) -> LicenseInfo:
        """
        Analyze license information for the model.
        
        Args:
            model_data: Model data containing license fields
            
        Returns:
            LicenseInfo with parsed license details
            
        Raises:
            LicenseError: If license analysis fails
        """
        pass
    
    @abstractmethod
    def assess_privacy_risk(self, model_data: Dict[str, Any]) -> PrivacyRiskAssessment:
        """
        Assess privacy risks associated with the model.
        
        Args:
            model_data: Model data including tags, description, images
            
        Returns:
            PrivacyRiskAssessment with privacy analysis
            
        Raises:
            PrivacyError: If privacy assessment fails
        """
        pass
    
    @abstractmethod
    def validate_file_security(self, file_data: Dict[str, Any]) -> SecurityScanResult:
        """
        Validate security scan results for model files.
        
        Args:
            file_data: File information including scan results
            
        Returns:
            SecurityScanResult with validated scan information
            
        Raises:
            SecurityError: If scan validation fails
        """
        pass
    
    @abstractmethod
    def get_security_warnings(self, analysis: SecurityAnalysis) -> List[SecurityWarning]:
        """
        Generate user-facing security warnings based on analysis.
        
        Args:
            analysis: Complete security analysis
            
        Returns:
            List of SecurityWarning objects for user notification
        """
        pass
    
    @abstractmethod
    def should_block_download(self, analysis: SecurityAnalysis) -> bool:
        """
        Determine if download should be blocked based on security analysis.
        
        Args:
            analysis: Security analysis results
            
        Returns:
            True if download should be blocked for security reasons
        """
        pass
    
    def calculate_risk_score(self, analysis: SecurityAnalysis) -> float:
        """
        Calculate overall risk score (0.0 to 1.0).
        
        Args:
            analysis: Security analysis results
            
        Returns:
            Risk score from 0.0 (safe) to 1.0 (dangerous)
        """
        # Default implementation - can be overridden
        base_score = 0.0
        
        # License restrictions add to risk
        if not analysis.license_info.allow_commercial_use:
            base_score += 0.1
        
        # Security scan results
        if analysis.security_scans.virus_scan_result != "clean":
            base_score += 0.4
        if analysis.security_scans.pickle_scan_result != "safe":
            base_score += 0.3
        
        # Privacy risks
        base_score += analysis.privacy_risks.privacy_risk_score * 0.2
        
        return min(base_score, 1.0)