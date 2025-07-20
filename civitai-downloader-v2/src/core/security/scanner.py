#!/usr/bin/env python3
"""
Security Scanner for CivitAI Downloader.
Provides malware detection, file validation, and security scanning capabilities.
"""

import os
import hashlib
import zipfile
import pickle
import ast
import re
import tempfile

# Optional dependency
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
import time
import threading

try:
    from ...core.config.system_config import SystemConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.config.system_config import SystemConfig


class ScanResult(Enum):
    """Security scan result types."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    ERROR = "error"
    UNKNOWN = "unknown"


class ThreatType(Enum):
    """Types of security threats."""
    MALICIOUS_CODE = "malicious_code"
    PICKLE_EXPLOIT = "pickle_exploit"
    SUSPICIOUS_IMPORTS = "suspicious_imports"
    EMBEDDED_EXECUTABLE = "embedded_executable"
    OVERSIZED_FILE = "oversized_file"
    INVALID_FORMAT = "invalid_format"
    HASH_MISMATCH = "hash_mismatch"
    SCAN_TIMEOUT = "scan_timeout"


@dataclass
class SecurityIssue:
    """Security issue found during scanning."""
    threat_type: ThreatType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    location: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ScanReport:
    """Comprehensive security scan report."""
    file_path: Path
    scan_result: ScanResult
    file_type: str
    file_size: int
    hash_sha256: str
    scan_duration: float
    issues: List[SecurityIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scan_timestamp: float = field(default_factory=time.time)
    
    @property
    def is_safe(self) -> bool:
        """Check if file is considered safe."""
        return self.scan_result == ScanResult.SAFE
    
    @property
    def critical_issues(self) -> List[SecurityIssue]:
        """Get critical security issues."""
        return [issue for issue in self.issues if issue.severity == "critical"]
    
    @property
    def high_issues(self) -> List[SecurityIssue]:
        """Get high severity issues."""
        return [issue for issue in self.issues if issue.severity == "high"]


class SecurityScanner:
    """Advanced security scanner for AI model files."""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize security scanner.
        
        Args:
            config: System configuration
        """
        self.config = config or SystemConfig()
        
        # Scanner configuration
        self.max_file_size = self.config.get('security.max_file_size', 10 * 1024 * 1024 * 1024)  # 10GB
        self.scan_timeout = self.config.get('security.scan_timeout', 300)  # 5 minutes
        self.deep_scan = self.config.get('security.deep_scan', True)
        
        # Threat patterns
        self._malicious_patterns = self._load_malicious_patterns()
        self._suspicious_imports = self._load_suspicious_imports()
        self._allowed_file_types = self._load_allowed_file_types()
        
        # Statistics
        self.scan_stats = {
            'total_scans': 0,
            'safe_files': 0,
            'suspicious_files': 0,
            'malicious_files': 0,
            'scan_errors': 0,
            'total_scan_time': 0.0
        }
        
        # Thread safety
        self._lock = threading.Lock()
    
    def scan_file(self, file_path: Path, expected_hash: Optional[str] = None) -> ScanReport:
        """
        Perform comprehensive security scan on a file.
        
        Args:
            file_path: Path to file to scan
            expected_hash: Expected SHA256 hash for verification
            
        Returns:
            Detailed scan report
        """
        start_time = time.time()
        
        try:
            # Basic file validation
            if not file_path.exists():
                return self._create_error_report(file_path, "File does not exist")
            
            if not file_path.is_file():
                return self._create_error_report(file_path, "Path is not a file")
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                issue = SecurityIssue(
                    threat_type=ThreatType.OVERSIZED_FILE,
                    severity="medium",
                    description=f"File size ({file_size:,} bytes) exceeds maximum allowed ({self.max_file_size:,} bytes)"
                )
                return self._create_report(file_path, ScanResult.SUSPICIOUS, [issue], scan_duration=time.time() - start_time)
            
            # Calculate hash
            file_hash = self._calculate_file_hash(file_path)
            
            # Verify hash if provided
            issues = []
            if expected_hash and file_hash.lower() != expected_hash.lower():
                issues.append(SecurityIssue(
                    threat_type=ThreatType.HASH_MISMATCH,
                    severity="medium",
                    description=f"File hash mismatch. Expected: {expected_hash}, Got: {file_hash}"
                ))
            
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            # Validate file format
            format_issues = self._validate_file_format(file_path, file_type)
            issues.extend(format_issues)
            
            # Perform content scans based on file type
            if self.deep_scan:
                content_issues = self._scan_file_content(file_path, file_type)
                issues.extend(content_issues)
            
            # Determine overall scan result
            scan_result = self._determine_scan_result(issues)
            
            # Create report
            scan_duration = time.time() - start_time
            report = self._create_report(
                file_path=file_path,
                scan_result=scan_result,
                issues=issues,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                scan_duration=scan_duration
            )
            
            # Update statistics
            self._update_scan_stats(scan_result, scan_duration)
            
            return report
            
        except Exception as e:
            scan_duration = time.time() - start_time
            self._update_scan_stats(ScanResult.ERROR, scan_duration)
            return self._create_error_report(file_path, f"Scan error: {str(e)}")
    
    def scan_model_file(self, file_path: Path, model_metadata: Optional[Dict[str, Any]] = None) -> ScanReport:
        """
        Scan AI model file with specialized checks.
        
        Args:
            file_path: Path to model file
            model_metadata: Model metadata from API
            
        Returns:
            Scan report with model-specific analysis
        """
        # Perform standard scan
        report = self.scan_file(file_path)
        
        # Add model-specific metadata
        if model_metadata:
            report.metadata['model_info'] = model_metadata
            
            # Check against known safe models (if available)
            if 'id' in model_metadata:
                report.metadata['model_id'] = model_metadata['id']
            
            # Validate model type against file extension
            expected_type = model_metadata.get('type', '').lower()
            actual_extension = file_path.suffix.lower()
            
            type_validation = self._validate_model_type(expected_type, actual_extension)
            if type_validation:
                report.issues.append(type_validation)
                report.scan_result = self._determine_scan_result(report.issues)
        
        return report
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type using magic bytes."""
        try:
            # Use python-magic if available
            if MAGIC_AVAILABLE:
                return magic.from_file(str(file_path))
        except Exception:
            pass
        
        # Fallback to extension-based detection
        extension = file_path.suffix.lower()
        return {
            '.safetensors': 'SafeTensors model',
            '.ckpt': 'PyTorch checkpoint',
            '.pt': 'PyTorch model',
            '.pth': 'PyTorch model',
            '.bin': 'Binary model file',
            '.pkl': 'Python pickle file',
            '.zip': 'ZIP archive'
        }.get(extension, f'Unknown ({extension})')
    
    def _validate_file_format(self, file_path: Path, file_type: str) -> List[SecurityIssue]:
        """Validate file format integrity."""
        issues = []
        extension = file_path.suffix.lower()
        
        # Check for allowed file types
        if extension not in self._allowed_file_types:
            issues.append(SecurityIssue(
                threat_type=ThreatType.INVALID_FORMAT,
                severity="medium",
                description=f"File extension '{extension}' is not in allowed types: {list(self._allowed_file_types)}"
            ))
        
        # Specific format validations
        if extension == '.zip':
            zip_issues = self._validate_zip_file(file_path)
            issues.extend(zip_issues)
        elif extension in ['.pkl', '.pickle']:
            pickle_issues = self._validate_pickle_file(file_path)
            issues.extend(pickle_issues)
        elif extension == '.safetensors':
            safetensors_issues = self._validate_safetensors_file(file_path)
            issues.extend(safetensors_issues)
        
        return issues
    
    def _scan_file_content(self, file_path: Path, file_type: str) -> List[SecurityIssue]:
        """Perform deep content scanning."""
        issues = []
        extension = file_path.suffix.lower()
        
        # Scan for embedded executables
        executable_issues = self._scan_for_executables(file_path)
        issues.extend(executable_issues)
        
        # Scan pickle files for malicious code
        if extension in ['.pkl', '.pickle', '.ckpt', '.pt', '.pth']:
            pickle_issues = self._scan_pickle_content(file_path)
            issues.extend(pickle_issues)
        
        # Scan text content for suspicious patterns
        if self._is_text_based_format(extension):
            text_issues = self._scan_text_content(file_path)
            issues.extend(text_issues)
        
        return issues
    
    def _validate_zip_file(self, file_path: Path) -> List[SecurityIssue]:
        """Validate ZIP file integrity and contents."""
        issues = []
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Check for zip bombs
                total_uncompressed = sum(info.file_size for info in zip_file.infolist())
                compressed_size = file_path.stat().st_size
                
                if total_uncompressed > compressed_size * 100:  # 100x compression ratio threshold
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.MALICIOUS_CODE,
                        severity="high",
                        description=f"Potential zip bomb detected (compression ratio: {total_uncompressed/compressed_size:.1f}x)"
                    ))
                
                # Check for path traversal
                for info in zip_file.infolist():
                    if '..' in info.filename or info.filename.startswith('/'):
                        issues.append(SecurityIssue(
                            threat_type=ThreatType.MALICIOUS_CODE,
                            severity="high",
                            description=f"Path traversal detected in zip entry: {info.filename}"
                        ))
                
        except Exception as e:
            issues.append(SecurityIssue(
                threat_type=ThreatType.INVALID_FORMAT,
                severity="medium",
                description=f"ZIP file validation failed: {str(e)}"
            ))
        
        return issues
    
    def _validate_pickle_file(self, file_path: Path) -> List[SecurityIssue]:
        """Validate pickle file for security issues."""
        issues = []
        
        try:
            # Read raw pickle data to analyze opcodes
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)  # Read first 1MB
            
            # Check for dangerous pickle opcodes
            dangerous_opcodes = [
                b'c__builtin__\neval\n',  # eval function
                b'c__builtin__\nexec\n',  # exec function
                b'cos\nsystem\n',         # os.system
                b'csubprocess\n',         # subprocess module
            ]
            
            for opcode in dangerous_opcodes:
                if opcode in data:
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.PICKLE_EXPLOIT,
                        severity="critical",
                        description=f"Dangerous pickle opcode detected: {opcode.decode('ascii', errors='replace')}"
                    ))
            
        except Exception as e:
            issues.append(SecurityIssue(
                threat_type=ThreatType.INVALID_FORMAT,
                severity="low",
                description=f"Pickle validation failed: {str(e)}"
            ))
        
        return issues
    
    def _validate_safetensors_file(self, file_path: Path) -> List[SecurityIssue]:
        """Validate SafeTensors file format."""
        issues = []
        
        try:
            with open(file_path, 'rb') as f:
                # Read header length (first 8 bytes)
                header_len_bytes = f.read(8)
                if len(header_len_bytes) < 8:
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.INVALID_FORMAT,
                        severity="medium",
                        description="SafeTensors file too small to contain valid header"
                    ))
                    return issues
                
                # SafeTensors header length is little-endian 64-bit integer
                header_len = int.from_bytes(header_len_bytes, 'little')
                
                # Validate header length is reasonable
                if header_len > 10 * 1024 * 1024:  # 10MB header limit
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.SUSPICIOUS_IMPORTS,
                        severity="medium",
                        description=f"SafeTensors header unusually large: {header_len:,} bytes"
                    ))
                
        except Exception as e:
            issues.append(SecurityIssue(
                threat_type=ThreatType.INVALID_FORMAT,
                severity="low",
                description=f"SafeTensors validation failed: {str(e)}"
            ))
        
        return issues
    
    def _scan_for_executables(self, file_path: Path) -> List[SecurityIssue]:
        """Scan for embedded executable content."""
        issues = []
        
        try:
            with open(file_path, 'rb') as f:
                # Read file in chunks to scan for executable signatures
                chunk_size = 1024 * 1024  # 1MB chunks
                
                while chunk := f.read(chunk_size):
                    # Check for PE/ELF/Mach-O headers
                    if (b'MZ' in chunk or  # PE header
                        b'\x7fELF' in chunk or  # ELF header
                        b'\xfe\xed\xfa' in chunk):  # Mach-O header
                        
                        issues.append(SecurityIssue(
                            threat_type=ThreatType.EMBEDDED_EXECUTABLE,
                            severity="high",
                            description="Embedded executable code detected in file"
                        ))
                        break
                    
                    # Check for script headers
                    if (b'#!/bin/sh' in chunk or
                        b'#!/bin/bash' in chunk or
                        b'@echo off' in chunk):
                        
                        issues.append(SecurityIssue(
                            threat_type=ThreatType.MALICIOUS_CODE,
                            severity="medium",
                            description="Embedded script content detected"
                        ))
                        break
        
        except Exception:
            pass  # Silently skip if file reading fails
        
        return issues
    
    def _scan_pickle_content(self, file_path: Path) -> List[SecurityIssue]:
        """Scan pickle-based files for malicious content."""
        issues = []
        
        try:
            # Use a safe, restricted unpickler
            with open(file_path, 'rb') as f:
                # Read and analyze pickle stream without executing
                pickletools_available = True
                try:
                    import pickletools
                except ImportError:
                    pickletools_available = False
                
                if pickletools_available:
                    # Analyze pickle opcodes
                    f.seek(0)
                    try:
                        opcodes = []
                        
                        # Create a temporary file to capture pickletools output
                        with tempfile.NamedTemporaryFile(mode='w+') as temp_f:
                            pickletools.dis(f, temp_f)
                            temp_f.seek(0)
                            analysis = temp_f.read()
                        
                        # Check for suspicious operations in analysis
                        if 'GLOBAL' in analysis and ('eval' in analysis or 'exec' in analysis):
                            issues.append(SecurityIssue(
                                threat_type=ThreatType.PICKLE_EXPLOIT,
                                severity="critical",
                                description="Pickle file contains dangerous global references"
                            ))
                        
                    except Exception:
                        # If pickletools analysis fails, file might be corrupted or malicious
                        issues.append(SecurityIssue(
                            threat_type=ThreatType.INVALID_FORMAT,
                            severity="medium",
                            description="Unable to analyze pickle file structure"
                        ))
        
        except Exception as e:
            issues.append(SecurityIssue(
                threat_type=ThreatType.SCAN_TIMEOUT,
                severity="low",
                description=f"Pickle content scan failed: {str(e)}"
            ))
        
        return issues
    
    def _scan_text_content(self, file_path: Path) -> List[SecurityIssue]:
        """Scan text-based files for suspicious patterns."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024 * 1024)  # Read first 1MB
            
            # Check for suspicious imports
            for suspicious_import in self._suspicious_imports:
                if suspicious_import in content:
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.SUSPICIOUS_IMPORTS,
                        severity="medium",
                        description=f"Suspicious import detected: {suspicious_import}"
                    ))
            
            # Check for malicious patterns
            for pattern in self._malicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        threat_type=ThreatType.MALICIOUS_CODE,
                        severity="high",
                        description=f"Malicious pattern detected: {pattern}"
                    ))
        
        except Exception:
            pass  # Silently skip if text reading fails
        
        return issues
    
    def _validate_model_type(self, expected_type: str, actual_extension: str) -> Optional[SecurityIssue]:
        """Validate model type against file extension."""
        type_mapping = {
            'checkpoint': ['.ckpt', '.safetensors'],
            'lora': ['.safetensors', '.ckpt'],
            'embedding': ['.pt', '.safetensors'],
            'hypernetwork': ['.pt'],
            'controlnet': ['.safetensors', '.ckpt']
        }
        
        expected_extensions = type_mapping.get(expected_type.lower(), [])
        
        if expected_extensions and actual_extension not in expected_extensions:
            return SecurityIssue(
                threat_type=ThreatType.INVALID_FORMAT,
                severity="low",
                description=f"Model type '{expected_type}' typically uses {expected_extensions}, but file has '{actual_extension}'"
            )
        
        return None
    
    def _determine_scan_result(self, issues: List[SecurityIssue]) -> ScanResult:
        """Determine overall scan result based on issues."""
        if not issues:
            return ScanResult.SAFE
        
        # Check for critical issues
        if any(issue.severity == "critical" for issue in issues):
            return ScanResult.MALICIOUS
        
        # Check for high severity issues
        if any(issue.severity == "high" for issue in issues):
            return ScanResult.MALICIOUS
        
        # Check for medium severity issues
        if any(issue.severity == "medium" for issue in issues):
            return ScanResult.SUSPICIOUS
        
        # Only low severity issues remain
        if any(issue.severity == "low" for issue in issues):
            return ScanResult.SUSPICIOUS
        
        # Should not reach here, but default to safe if no issues
        return ScanResult.SAFE
    
    def _create_report(self, file_path: Path, scan_result: ScanResult, issues: List[SecurityIssue],
                      file_type: str = "unknown", file_size: int = 0, file_hash: str = "",
                      scan_duration: float = 0.0) -> ScanReport:
        """Create a scan report."""
        return ScanReport(
            file_path=file_path,
            scan_result=scan_result,
            file_type=file_type,
            file_size=file_size,
            hash_sha256=file_hash,
            scan_duration=scan_duration,
            issues=issues
        )
    
    def _create_error_report(self, file_path: Path, error_message: str) -> ScanReport:
        """Create an error report."""
        return ScanReport(
            file_path=file_path,
            scan_result=ScanResult.ERROR,
            file_type="unknown",
            file_size=0,
            hash_sha256="",
            scan_duration=0.0,
            issues=[SecurityIssue(
                threat_type=ThreatType.SCAN_TIMEOUT,
                severity="medium",
                description=error_message
            )]
        )
    
    def _update_scan_stats(self, scan_result: ScanResult, scan_duration: float) -> None:
        """Update scan statistics."""
        with self._lock:
            self.scan_stats['total_scans'] += 1
            self.scan_stats['total_scan_time'] += scan_duration
            
            if scan_result == ScanResult.SAFE:
                self.scan_stats['safe_files'] += 1
            elif scan_result == ScanResult.SUSPICIOUS:
                self.scan_stats['suspicious_files'] += 1
            elif scan_result == ScanResult.MALICIOUS:
                self.scan_stats['malicious_files'] += 1
            elif scan_result == ScanResult.ERROR:
                self.scan_stats['scan_errors'] += 1
    
    def _is_text_based_format(self, extension: str) -> bool:
        """Check if file extension indicates text-based format."""
        text_extensions = {'.py', '.txt', '.json', '.yaml', '.yml', '.xml', '.html'}
        return extension.lower() in text_extensions
    
    def _load_malicious_patterns(self) -> List[str]:
        """Load malicious code patterns to detect."""
        return [
            r'__import__\s*\(\s*[\'"]os[\'"]',
            r'exec\s*\(',
            r'eval\s*\(',
            r'subprocess\.',
            r'os\.system',
            r'open\s*\([^)]*[\'"]w[\'"]',  # File writing
            r'urllib\.request',
            r'requests\.get',
            r'socket\.',
            r'threading\.Thread',
            r'multiprocessing\.',
        ]
    
    def _load_suspicious_imports(self) -> Set[str]:
        """Load suspicious import statements."""
        return {
            'import os',
            'import subprocess',
            'import socket',
            'import urllib',
            'import requests',
            'from os import',
            'from subprocess import',
            '__import__',
        }
    
    def _load_allowed_file_types(self) -> Set[str]:
        """Load allowed file extensions."""
        return {
            '.safetensors',
            '.ckpt',
            '.pt',
            '.pth',
            '.bin',
            '.json',
            '.yaml',
            '.yml',
            '.txt',
            '.md',
            '.zip'  # Allow ZIP files but validate contents
        }
    
    def get_scan_statistics(self) -> Dict[str, Any]:
        """Get scan statistics."""
        with self._lock:
            stats = self.scan_stats.copy()
            if stats['total_scans'] > 0:
                stats['avg_scan_time'] = stats['total_scan_time'] / stats['total_scans']
            else:
                stats['avg_scan_time'] = 0.0
            return stats
    
    def reset_statistics(self) -> None:
        """Reset scan statistics."""
        with self._lock:
            self.scan_stats = {
                'total_scans': 0,
                'safe_files': 0,
                'suspicious_files': 0,
                'malicious_files': 0,
                'scan_errors': 0,
                'total_scan_time': 0.0
            }


if __name__ == "__main__":
    # Test security scanner
    print("Testing Security Scanner...")
    
    scanner = SecurityScanner()
    
    # Create a test file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b"This is a test file for security scanning.")
        temp_path = Path(temp_file.name)
    
    try:
        # Scan the test file
        report = scanner.scan_file(temp_path)
        
        print(f"Scan result: {report.scan_result.value}")
        print(f"File type: {report.file_type}")
        print(f"File size: {report.file_size} bytes")
        print(f"Hash: {report.hash_sha256}")
        print(f"Scan duration: {report.scan_duration:.3f}s")
        print(f"Issues found: {len(report.issues)}")
        
        for issue in report.issues:
            print(f"  - {issue.severity.upper()}: {issue.description}")
        
        stats = scanner.get_scan_statistics()
        print(f"Scanner statistics: {stats}")
        
    finally:
        # Clean up test file
        temp_path.unlink()
        
    print("Security Scanner test completed.")