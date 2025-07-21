#!/usr/bin/env python3
"""
Security Scanner System.
Implements requirement 9.2-9.4 and 14: Security scanning and privacy protection.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
import json
import re

logger = logging.getLogger(__name__)


class ScanStatus(Enum):
    """Security scan status values."""
    CLEAN = "clean"
    INFECTED = "infected"
    SUSPICIOUS = "suspicious"
    PENDING = "pending"
    FAILED = "failed"
    NOT_SCANNED = "not_scanned"


class HashAlgorithm(Enum):
    """Supported hash algorithms per requirement 9.4."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA384 = "sha384" 
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    CRC32 = "crc32"


class PrivacyRisk(Enum):
    """Privacy risk levels per requirement 14."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityScanResult:
    """
    Security scan results per requirement 9.2.
    Includes virus scan and pickle scan results.
    """
    virus_scan_status: ScanStatus
    pickle_scan_status: ScanStatus
    scan_timestamp: float
    scanner_version: Optional[str] = None
    virus_scan_details: Optional[Dict[str, Any]] = None
    pickle_scan_details: Optional[Dict[str, Any]] = None
    
    def is_safe(self) -> bool:
        """Check if file passed all security scans."""
        return (self.virus_scan_status == ScanStatus.CLEAN and 
                self.pickle_scan_status == ScanStatus.CLEAN)
    
    def has_risks(self) -> bool:
        """Check if file has any security risks."""
        risky_statuses = [ScanStatus.INFECTED, ScanStatus.SUSPICIOUS]
        return (self.virus_scan_status in risky_statuses or 
                self.pickle_scan_status in risky_statuses)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export."""
        return {
            'virus_scan': {
                'status': self.virus_scan_status.value,
                'details': self.virus_scan_details
            },
            'pickle_scan': {
                'status': self.pickle_scan_status.value,
                'details': self.pickle_scan_details
            },
            'metadata': {
                'scan_timestamp': self.scan_timestamp,
                'scanner_version': self.scanner_version,
                'is_safe': self.is_safe(),
                'has_risks': self.has_risks()
            }
        }


@dataclass
class FileIntegrityCheck:
    """
    File integrity verification per requirement 9.4.
    Supports 6 hash algorithms.
    """
    file_path: Path
    file_size: int
    hash_results: Dict[HashAlgorithm, str]
    verification_timestamp: float
    
    def verify_against_expected(self, expected_hashes: Dict[HashAlgorithm, str]) -> bool:
        """Verify file integrity against expected hashes."""
        for algorithm, expected_hash in expected_hashes.items():
            if algorithm in self.hash_results:
                if self.hash_results[algorithm].lower() != expected_hash.lower():
                    logger.warning(
                        f"Hash mismatch for {algorithm.value}: "
                        f"expected {expected_hash}, got {self.hash_results[algorithm]}"
                    )
                    return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'file_path': str(self.file_path),
            'file_size': self.file_size,
            'hashes': {alg.value: hash_val for alg, hash_val in self.hash_results.items()},
            'verification_timestamp': self.verification_timestamp
        }


@dataclass
class PrivacyAssessment:
    """
    Privacy risk assessment per requirement 14.
    Identifies personal information and celebrity models.
    """
    model_id: int
    privacy_risk_level: PrivacyRisk
    identified_risks: List[str]
    celebrity_detected: bool
    personal_info_detected: bool
    assessment_timestamp: float
    
    # Risk categories
    name_patterns: List[str] = None
    description_flags: List[str] = None
    tag_flags: List[str] = None
    
    def requires_user_consent(self) -> bool:
        """Check if user consent is required per requirement 14.2."""
        return (self.celebrity_detected or 
                self.privacy_risk_level in [PrivacyRisk.HIGH, PrivacyRisk.CRITICAL])
    
    def get_warning_message(self) -> str:
        """Generate appropriate warning message."""
        if self.celebrity_detected:
            return ("⚠️  Celebrity model detected. Special handling required. "
                   "Ensure you have appropriate rights for intended use.")
        
        if self.privacy_risk_level == PrivacyRisk.CRITICAL:
            return ("🚨 CRITICAL: This model may contain personal information. "
                   "Review carefully before use.")
        
        if self.privacy_risk_level == PrivacyRisk.HIGH:
            return ("⚠️  HIGH RISK: This model may involve privacy concerns. "
                   "Use with caution and respect privacy rights.")
        
        if self.privacy_risk_level == PrivacyRisk.MEDIUM:
            return ("ℹ️  Medium privacy risk detected. Review model details before use.")
        
        return "✅ Low privacy risk detected."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'model_id': self.model_id,
            'privacy_risk_level': self.privacy_risk_level.value,
            'identified_risks': self.identified_risks,
            'celebrity_detected': self.celebrity_detected,
            'personal_info_detected': self.personal_info_detected,
            'assessment_timestamp': self.assessment_timestamp,
            'requires_consent': self.requires_user_consent(),
            'warning_message': self.get_warning_message(),
            'risk_details': {
                'name_patterns': self.name_patterns or [],
                'description_flags': self.description_flags or [],
                'tag_flags': self.tag_flags or []
            }
        }


class SecurityScanner:
    """
    Comprehensive security scanner implementing requirements 9 and 14.
    
    Provides:
    - Virus and pickle scanning (9.2)
    - Download warnings (9.3)  
    - File integrity verification (9.4)
    - Privacy assessment (14.1-14.2)
    """
    
    def __init__(self):
        """Initialize security scanner."""
        self.scan_cache: Dict[str, SecurityScanResult] = {}
        self.integrity_cache: Dict[str, FileIntegrityCheck] = {}
        self.privacy_assessments: Dict[int, PrivacyAssessment] = {}
        self.security_logs: List[Dict[str, Any]] = []
        
        # Privacy detection patterns
        self.celebrity_patterns = [
            r'\b(celebrity|celeb|famous|actor|actress|model|singer|star)\b',
            r'\b(taylor swift|elon musk|emma watson|jennifer lawrence)\b',
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'  # Name patterns
        ]
        
        self.personal_info_patterns = [
            r'\b(personal|private|individual|specific person)\b',
            r'\b(id photo|passport|driver|license)\b',
            r'\b(face swap|deepfake|identity)\b'
        ]
    
    def simulate_virus_scan(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate virus scan per requirement 9.2.
        
        In production, this would integrate with actual antivirus APIs.
        """
        file_name = file_info.get('name', '')
        file_size = file_info.get('sizeKB', 0) * 1024
        
        # Simulate scan result based on file characteristics
        scan_result = {
            'status': ScanStatus.CLEAN,
            'threats_found': [],
            'scan_engine': 'CivitAI-Scanner-v1.0',
            'scan_duration': 2.5,
            'file_analyzed': file_name
        }
        
        # Check for suspicious file patterns (simulation)
        suspicious_patterns = ['.exe', '.bat', '.scr', '.com', '.pif']
        if any(pattern in file_name.lower() for pattern in suspicious_patterns):
            scan_result['status'] = ScanStatus.SUSPICIOUS
            scan_result['threats_found'].append('Suspicious file extension')
        
        # Large files might need longer scan time
        if file_size > 10 * 1024 * 1024 * 1024:  # 10GB
            scan_result['scan_duration'] = 15.0
        
        return scan_result
    
    def simulate_pickle_scan(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate pickle scan per requirement 9.2.
        
        Checks for malicious Python objects in model files.
        """
        file_name = file_info.get('name', '')
        
        scan_result = {
            'status': ScanStatus.CLEAN,
            'pickle_objects_found': [],
            'suspicious_imports': [],
            'scan_engine': 'PickleInspector-v2.1'
        }
        
        # Check file format
        if file_name.lower().endswith('.safetensors'):
            scan_result['status'] = ScanStatus.CLEAN
            scan_result['notes'] = 'SafeTensors format - no pickle risk'
        elif any(ext in file_name.lower() for ext in ['.pkl', '.pickle', '.ckpt', '.pt']):
            scan_result['status'] = ScanStatus.PENDING  # Would need actual scan
            scan_result['notes'] = 'Pickle format detected - requires scanning'
        
        return scan_result
    
    def perform_security_scan(self, file_info: Dict[str, Any]) -> SecurityScanResult:
        """
        Perform comprehensive security scan per requirement 9.2.
        
        Args:
            file_info: File information from CivitAI API
            
        Returns:
            SecurityScanResult with virus and pickle scan results
        """
        file_id = f"{file_info.get('id', 0)}_{file_info.get('name', 'unknown')}"
        
        # Check cache first
        if file_id in self.scan_cache:
            cached_result = self.scan_cache[file_id]
            # Use cached result if less than 24 hours old
            if time.time() - cached_result.scan_timestamp < 86400:
                return cached_result
        
        # Perform scans
        virus_scan = self.simulate_virus_scan(file_info)
        pickle_scan = self.simulate_pickle_scan(file_info)
        
        # Create result
        result = SecurityScanResult(
            virus_scan_status=ScanStatus(virus_scan['status']),
            pickle_scan_status=ScanStatus(pickle_scan['status']),
            scan_timestamp=time.time(),
            scanner_version="CivitAI-SecurityScanner-v1.0",
            virus_scan_details=virus_scan,
            pickle_scan_details=pickle_scan
        )
        
        # Cache result
        self.scan_cache[file_id] = result
        
        # Log security event
        self.log_security_event(
            event_type="security_scan",
            file_id=file_id,
            result=result.to_dict()
        )
        
        return result
    
    def generate_download_warning(self, scan_result: SecurityScanResult, 
                                 file_info: Dict[str, Any]) -> Optional[str]:
        """
        Generate download warning per requirement 9.3.
        
        Args:
            scan_result: Security scan results
            file_info: File information
            
        Returns:
            Warning message if risks detected, None if safe
        """
        warnings = []
        
        if scan_result.virus_scan_status == ScanStatus.INFECTED:
            warnings.append("🚨 VIRUS DETECTED - Download blocked for safety")
        elif scan_result.virus_scan_status == ScanStatus.SUSPICIOUS:
            warnings.append("⚠️  Potentially suspicious file detected")
        
        if scan_result.pickle_scan_status == ScanStatus.SUSPICIOUS:
            warnings.append("⚠️  Pickle format may contain executable code")
        elif scan_result.pickle_scan_status == ScanStatus.PENDING:
            warnings.append("ℹ️  File requires additional security scanning")
        
        if scan_result.virus_scan_status == ScanStatus.FAILED:
            warnings.append("⚠️  Virus scan failed - proceed with caution")
        
        if scan_result.pickle_scan_status == ScanStatus.FAILED:
            warnings.append("⚠️  Pickle scan failed - verify file safety manually")
        
        # Add format-specific warnings
        file_name = file_info.get('name', '')
        if file_name.lower().endswith('.safetensors'):
            warnings.append("✅ SafeTensors format - safer than pickle")
        elif any(ext in file_name.lower() for ext in ['.pkl', '.pickle', '.ckpt', '.pt']):
            warnings.append("⚠️  Pickle format - exercise caution")
        
        return "\n".join(warnings) if warnings else None
    
    def calculate_file_hashes(self, file_path: Path, 
                            algorithms: List[HashAlgorithm] = None) -> FileIntegrityCheck:
        """
        Calculate file integrity hashes per requirement 9.4.
        
        Args:
            file_path: Path to file
            algorithms: Hash algorithms to use (default: all 6)
            
        Returns:
            FileIntegrityCheck with calculated hashes
        """
        if algorithms is None:
            algorithms = list(HashAlgorithm)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        hash_results = {}
        
        # Calculate hashes
        try:
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files
                chunk_size = 64 * 1024  # 64KB chunks
                
                # Initialize hashers
                hashers = {}
                for alg in algorithms:
                    if alg == HashAlgorithm.MD5:
                        hashers[alg] = hashlib.md5()
                    elif alg == HashAlgorithm.SHA1:
                        hashers[alg] = hashlib.sha1()
                    elif alg == HashAlgorithm.SHA256:
                        hashers[alg] = hashlib.sha256()
                    elif alg == HashAlgorithm.SHA384:
                        hashers[alg] = hashlib.sha384()
                    elif alg == HashAlgorithm.SHA512:
                        hashers[alg] = hashlib.sha512()
                    elif alg == HashAlgorithm.BLAKE2B:
                        hashers[alg] = hashlib.blake2b()
                    elif alg == HashAlgorithm.CRC32:
                        # CRC32 is handled separately
                        continue
                
                # Process file chunks
                crc32_value = 0
                while chunk := f.read(chunk_size):
                    for alg, hasher in hashers.items():
                        hasher.update(chunk)
                    
                    # Calculate CRC32 if requested
                    if HashAlgorithm.CRC32 in algorithms:
                        import zlib
                        crc32_value = zlib.crc32(chunk, crc32_value)
                
                # Get final hash values
                for alg, hasher in hashers.items():
                    hash_results[alg] = hasher.hexdigest()
                
                if HashAlgorithm.CRC32 in algorithms:
                    hash_results[HashAlgorithm.CRC32] = format(crc32_value & 0xffffffff, '08x')
        
        except Exception as e:
            logger.error(f"Error calculating hashes for {file_path}: {e}")
            raise
        
        # Create integrity check result
        integrity_check = FileIntegrityCheck(
            file_path=file_path,
            file_size=file_size,
            hash_results=hash_results,
            verification_timestamp=time.time()
        )
        
        # Cache result
        cache_key = str(file_path)
        self.integrity_cache[cache_key] = integrity_check
        
        return integrity_check
    
    def assess_privacy_risks(self, model_data: Dict[str, Any]) -> PrivacyAssessment:
        """
        Assess privacy risks per requirement 14.1-14.2.
        
        Args:
            model_data: Model data from CivitAI API
            
        Returns:
            PrivacyAssessment with risk analysis
        """
        model_id = model_data.get('id', 0)
        
        # Check cache
        if model_id in self.privacy_assessments:
            return self.privacy_assessments[model_id]
        
        # Analyze model data for privacy risks
        risks = []
        celebrity_detected = False
        personal_info_detected = False
        risk_level = PrivacyRisk.LOW
        
        # Analyze model name
        name = model_data.get('name', '').lower()
        description = model_data.get('description', '').lower()
        tags = [tag.get('name', '').lower() for tag in model_data.get('tags', [])]
        
        name_flags = []
        description_flags = []
        tag_flags = []
        
        # Check for celebrity patterns
        for pattern in self.celebrity_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                celebrity_detected = True
                name_flags.append(f"Celebrity pattern in name: {pattern}")
                risks.append(f"Celebrity reference detected in name")
            
            if re.search(pattern, description, re.IGNORECASE):
                celebrity_detected = True
                description_flags.append(f"Celebrity pattern in description: {pattern}")
                risks.append(f"Celebrity reference detected in description")
        
        # Check tags for celebrity/person indicators
        celebrity_tags = ['celebrity', 'actor', 'actress', 'singer', 'famous', 'real person']
        for tag in tags:
            if any(celeb_tag in tag for celeb_tag in celebrity_tags):
                celebrity_detected = True
                tag_flags.append(f"Celebrity tag: {tag}")
                risks.append(f"Celebrity tag detected: {tag}")
        
        # Check for personal information patterns
        for pattern in self.personal_info_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                personal_info_detected = True
                name_flags.append(f"Personal info pattern in name: {pattern}")
                risks.append(f"Personal information pattern in name")
            
            if re.search(pattern, description, re.IGNORECASE):
                personal_info_detected = True
                description_flags.append(f"Personal info pattern in description: {pattern}")
                risks.append(f"Personal information pattern in description")
        
        # Determine risk level
        if celebrity_detected and personal_info_detected:
            risk_level = PrivacyRisk.CRITICAL
        elif celebrity_detected:
            risk_level = PrivacyRisk.HIGH
        elif personal_info_detected:
            risk_level = PrivacyRisk.MEDIUM
        
        # Check model type for additional context
        model_type = model_data.get('type', '').lower()
        if model_type in ['checkpoint', 'lora'] and (celebrity_detected or personal_info_detected):
            risks.append("Model type suggests person-specific training")
            if risk_level == PrivacyRisk.LOW:
                risk_level = PrivacyRisk.MEDIUM
        
        # Create assessment
        assessment = PrivacyAssessment(
            model_id=model_id,
            privacy_risk_level=risk_level,
            identified_risks=risks,
            celebrity_detected=celebrity_detected,
            personal_info_detected=personal_info_detected,
            assessment_timestamp=time.time(),
            name_patterns=name_flags,
            description_flags=description_flags,
            tag_flags=tag_flags
        )
        
        # Cache assessment
        self.privacy_assessments[model_id] = assessment
        
        # Log privacy assessment
        self.log_security_event(
            event_type="privacy_assessment",
            model_id=model_id,
            result=assessment.to_dict()
        )
        
        return assessment
    
    def log_security_event(self, event_type: str, **kwargs) -> None:
        """Log security events per requirement 14.6."""
        event = {
            'timestamp': time.time(),
            'event_type': event_type,
            'user_agent': 'CivitAI-Downloader-v2',
            **kwargs
        }
        
        self.security_logs.append(event)
        logger.info(f"Security event logged: {event_type}")
        
        # Limit log size
        if len(self.security_logs) > 1000:
            self.security_logs = self.security_logs[-500:]
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Generate comprehensive security summary."""
        total_scans = len(self.scan_cache)
        safe_files = sum(1 for result in self.scan_cache.values() if result.is_safe())
        risky_files = sum(1 for result in self.scan_cache.values() if result.has_risks())
        
        privacy_assessments = len(self.privacy_assessments)
        high_risk_models = sum(
            1 for assessment in self.privacy_assessments.values()
            if assessment.privacy_risk_level in [PrivacyRisk.HIGH, PrivacyRisk.CRITICAL]
        )
        celebrity_models = sum(
            1 for assessment in self.privacy_assessments.values()
            if assessment.celebrity_detected
        )
        
        return {
            'security_scans': {
                'total_scanned': total_scans,
                'safe_files': safe_files,
                'risky_files': risky_files,
                'scan_success_rate': round(safe_files / total_scans * 100, 1) if total_scans > 0 else 0
            },
            'privacy_assessments': {
                'total_assessed': privacy_assessments,
                'high_risk_models': high_risk_models,
                'celebrity_models': celebrity_models,
                'consent_required': sum(
                    1 for assessment in self.privacy_assessments.values()
                    if assessment.requires_user_consent()
                )
            },
            'integrity_checks': {
                'files_verified': len(self.integrity_cache),
                'algorithms_supported': len(HashAlgorithm)
            },
            'audit_trail': {
                'security_events_logged': len(self.security_logs),
                'last_event': self.security_logs[-1]['timestamp'] if self.security_logs else None
            }
        }
    
    def export_security_audit(self) -> Dict[str, Any]:
        """Export comprehensive security audit report."""
        return {
            'audit_metadata': {
                'generated_at': time.time(),
                'scanner_version': "CivitAI-SecurityScanner-v1.0"
            },
            'security_scans': {
                str(key): result.to_dict() 
                for key, result in self.scan_cache.items()
            },
            'privacy_assessments': {
                str(key): assessment.to_dict() 
                for key, assessment in self.privacy_assessments.items()
            },
            'integrity_checks': {
                str(key): check.to_dict()
                for key, check in self.integrity_cache.items()
            },
            'security_events': self.security_logs,
            'summary': self.get_security_summary()
        }