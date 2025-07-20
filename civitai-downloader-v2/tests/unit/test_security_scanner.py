#!/usr/bin/env python3
"""
Security Scanner tests.
Tests for malware detection, file validation, and security scanning capabilities.
"""

import pytest
import tempfile
import zipfile
import hashlib
import re
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.security.scanner import (
    SecurityScanner, ScanReport, SecurityIssue,
    ScanResult, ThreatType
)


class TestSecurityIssue:
    """Test SecurityIssue data class."""
    
    def test_security_issue_creation(self):
        """Test SecurityIssue creation."""
        issue = SecurityIssue(
            threat_type=ThreatType.MALICIOUS_CODE,
            severity="high",
            description="Test malicious code detected",
            location="/test/path",
            details={"pattern": "eval()"}
        )
        
        assert issue.threat_type == ThreatType.MALICIOUS_CODE
        assert issue.severity == "high"
        assert issue.description == "Test malicious code detected"
        assert issue.location == "/test/path"
        assert issue.details["pattern"] == "eval()"


class TestScanReport:
    """Test ScanReport data class."""
    
    def test_scan_report_creation(self):
        """Test ScanReport creation."""
        test_path = Path("/test/file.txt")
        
        issue1 = SecurityIssue(ThreatType.MALICIOUS_CODE, "high", "High severity issue")
        issue2 = SecurityIssue(ThreatType.SUSPICIOUS_IMPORTS, "critical", "Critical issue")
        issue3 = SecurityIssue(ThreatType.INVALID_FORMAT, "low", "Low severity issue")
        
        report = ScanReport(
            file_path=test_path,
            scan_result=ScanResult.MALICIOUS,
            file_type="text/plain",
            file_size=1024,
            hash_sha256="abcdef123456",
            scan_duration=1.5,
            issues=[issue1, issue2, issue3]
        )
        
        assert report.file_path == test_path
        assert report.scan_result == ScanResult.MALICIOUS
        assert report.file_type == "text/plain"
        assert report.file_size == 1024
        assert report.hash_sha256 == "abcdef123456"
        assert report.scan_duration == 1.5
        assert len(report.issues) == 3
    
    def test_is_safe_property(self):
        """Test is_safe property."""
        safe_report = ScanReport(
            file_path=Path("/test"),
            scan_result=ScanResult.SAFE,
            file_type="text",
            file_size=100,
            hash_sha256="hash",
            scan_duration=1.0
        )
        
        malicious_report = ScanReport(
            file_path=Path("/test"),
            scan_result=ScanResult.MALICIOUS,
            file_type="text",
            file_size=100,
            hash_sha256="hash",
            scan_duration=1.0
        )
        
        assert safe_report.is_safe is True
        assert malicious_report.is_safe is False
    
    def test_critical_and_high_issues_properties(self):
        """Test critical_issues and high_issues properties."""
        critical_issue = SecurityIssue(ThreatType.PICKLE_EXPLOIT, "critical", "Critical")
        high_issue = SecurityIssue(ThreatType.MALICIOUS_CODE, "high", "High")
        medium_issue = SecurityIssue(ThreatType.SUSPICIOUS_IMPORTS, "medium", "Medium")
        low_issue = SecurityIssue(ThreatType.INVALID_FORMAT, "low", "Low")
        
        report = ScanReport(
            file_path=Path("/test"),
            scan_result=ScanResult.MALICIOUS,
            file_type="text",
            file_size=100,
            hash_sha256="hash",
            scan_duration=1.0,
            issues=[critical_issue, high_issue, medium_issue, low_issue]
        )
        
        assert len(report.critical_issues) == 1
        assert report.critical_issues[0].severity == "critical"
        
        assert len(report.high_issues) == 1
        assert report.high_issues[0].severity == "high"


class TestSecurityScanner:
    """Test SecurityScanner functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Use temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Mock configuration
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'security.max_file_size': 1024 * 1024,  # 1MB
            'security.scan_timeout': 60,
            'security.deep_scan': True
        }.get(key, default)
        
        self.scanner = SecurityScanner(mock_config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scanner_initialization(self):
        """Test security scanner initialization."""
        assert self.scanner.max_file_size == 1024 * 1024
        assert self.scanner.scan_timeout == 60
        assert self.scanner.deep_scan is True
        assert len(self.scanner._malicious_patterns) > 0
        assert len(self.scanner._suspicious_imports) > 0
        assert len(self.scanner._allowed_file_types) > 0
    
    def test_scan_nonexistent_file(self):
        """Test scanning a file that doesn't exist."""
        nonexistent_path = self.temp_path / "nonexistent.txt"
        
        report = self.scanner.scan_file(nonexistent_path)
        
        assert report.scan_result == ScanResult.ERROR
        assert len(report.issues) == 1
        assert "does not exist" in report.issues[0].description
    
    def test_scan_safe_text_file(self):
        """Test scanning a safe text file."""
        test_file = self.temp_path / "safe.txt"
        test_content = "This is a safe text file with no malicious content."
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        report = self.scanner.scan_file(test_file)
        
        assert report.scan_result == ScanResult.SAFE
        assert report.file_size == len(test_content.encode())
        assert len(report.hash_sha256) == 64  # SHA256 hex length
        assert report.file_type.startswith("Unknown")  # Without magic library
        assert len(report.issues) == 0
    
    def test_scan_oversized_file(self):
        """Test scanning a file that exceeds size limit."""
        # Create scanner with small size limit
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'security.max_file_size': 100,  # 100 bytes limit
            'security.scan_timeout': 60,
            'security.deep_scan': True
        }.get(key, default)
        
        small_scanner = SecurityScanner(mock_config)
        
        # Create file larger than limit
        large_file = self.temp_path / "large.txt"
        with open(large_file, 'w') as f:
            f.write("x" * 200)  # 200 bytes
        
        report = small_scanner.scan_file(large_file)
        
        assert report.scan_result == ScanResult.SUSPICIOUS
        assert len(report.issues) == 1
        assert report.issues[0].threat_type == ThreatType.OVERSIZED_FILE
        assert "exceeds maximum" in report.issues[0].description
    
    def test_hash_verification(self):
        """Test hash verification functionality."""
        test_file = self.temp_path / "hash_test.txt"
        test_content = "test content"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content.encode()).hexdigest()
        
        # Test with correct hash
        report = self.scanner.scan_file(test_file, expected_hash)
        assert report.scan_result == ScanResult.SAFE
        
        # Test with incorrect hash
        wrong_hash = "wrong_hash_value"
        report = self.scanner.scan_file(test_file, wrong_hash)
        assert report.scan_result == ScanResult.SUSPICIOUS
        assert any(issue.threat_type == ThreatType.HASH_MISMATCH for issue in report.issues)
    
    def test_detect_malicious_patterns(self):
        """Test detection of malicious code patterns."""
        malicious_file = self.temp_path / "malicious.py"
        malicious_content = """
import os
import subprocess

def malicious_function():
    os.system("rm -rf /")
    eval("print('malicious code')")
    exec("import socket")
"""
        
        with open(malicious_file, 'w') as f:
            f.write(malicious_content)
        
        report = self.scanner.scan_file(malicious_file)
        
        assert report.scan_result in [ScanResult.SUSPICIOUS, ScanResult.MALICIOUS]
        
        # Should detect suspicious imports and malicious patterns
        threat_types = [issue.threat_type for issue in report.issues]
        assert ThreatType.SUSPICIOUS_IMPORTS in threat_types or ThreatType.MALICIOUS_CODE in threat_types
    
    def test_validate_zip_file(self):
        """Test ZIP file validation."""
        zip_file = self.temp_path / "test.zip"
        
        # Create a normal ZIP file
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("normal_file.txt", "safe content")
        
        report = self.scanner.scan_file(zip_file)
        assert report.scan_result == ScanResult.SAFE
        
        # Create ZIP with path traversal
        malicious_zip = self.temp_path / "malicious.zip"
        with zipfile.ZipFile(malicious_zip, 'w') as zf:
            zf.writestr("../../../etc/passwd", "malicious content")
        
        report = self.scanner.scan_file(malicious_zip)
        assert report.scan_result in [ScanResult.SUSPICIOUS, ScanResult.MALICIOUS]
        
        # Should detect path traversal
        descriptions = [issue.description for issue in report.issues]
        assert any("traversal" in desc.lower() for desc in descriptions)
    
    def test_file_type_detection_fallback(self):
        """Test file type detection fallback method."""
        # Test various file extensions
        test_files = [
            ("model.safetensors", "SafeTensors model"),
            ("checkpoint.ckpt", "PyTorch checkpoint"),
            ("embedding.pt", "PyTorch model"),
            ("unknown.xyz", "Unknown (.xyz)")
        ]
        
        for filename, expected_type in test_files:
            test_file = self.temp_path / filename
            test_file.write_text("test content")
            
            detected_type = self.scanner._detect_file_type(test_file)
            assert detected_type == expected_type
    
    def test_filename_sanitization_patterns(self):
        """Test malicious pattern detection."""
        patterns = self.scanner._load_malicious_patterns()
        
        # Test some patterns
        test_strings = [
            "os.system('malicious')",
            "eval(user_input)",
            "exec('dangerous code')",
            "subprocess.call(['rm', '-rf'])"
        ]
        
        for test_string in test_strings:
            pattern_matched = any(
                re.search(pattern, test_string, re.IGNORECASE)
                for pattern in patterns
            )
            assert pattern_matched, f"No pattern matched for: {test_string}"
    
    def test_allowed_file_types(self):
        """Test allowed file types configuration."""
        allowed = self.scanner._load_allowed_file_types()
        
        # Should include common AI model formats
        assert '.safetensors' in allowed
        assert '.ckpt' in allowed
        assert '.pt' in allowed
        assert '.pth' in allowed
        
        # Should not include dangerous formats
        assert '.exe' not in allowed
        assert '.bat' not in allowed
        assert '.sh' not in allowed
    
    def test_suspicious_imports_detection(self):
        """Test suspicious imports detection."""
        suspicious = self.scanner._load_suspicious_imports()
        
        # Should include dangerous imports
        assert 'import os' in suspicious
        assert 'import subprocess' in suspicious
        assert 'import socket' in suspicious
    
    def test_scan_model_file_with_metadata(self):
        """Test scanning model file with metadata validation."""
        model_file = self.temp_path / "model.safetensors"
        
        # Create a minimal valid SafeTensors file structure
        # SafeTensors starts with 8-byte header length, then JSON header
        header_json = b'{"tensor1":{"dtype":"F32","shape":[10],"data_offsets":[0,40]}}'
        header_len = len(header_json)
        
        with open(model_file, 'wb') as f:
            f.write(header_len.to_bytes(8, 'little'))  # Header length
            f.write(header_json)  # JSON header
            f.write(b'0' * 40)  # Fake tensor data
        
        model_metadata = {
            'id': 12345,
            'type': 'Checkpoint',
            'name': 'Test Model'
        }
        
        report = self.scanner.scan_model_file(model_file, model_metadata)
        
        assert 'model_info' in report.metadata
        assert report.metadata['model_id'] == 12345
        # The file should pass validation now with proper SafeTensors structure
    
    def test_model_type_validation(self):
        """Test model type validation against file extension."""
        # Valid combinations
        assert self.scanner._validate_model_type('checkpoint', '.ckpt') is None
        assert self.scanner._validate_model_type('checkpoint', '.safetensors') is None
        
        # Invalid combination
        issue = self.scanner._validate_model_type('checkpoint', '.txt')
        assert issue is not None
        assert issue.threat_type == ThreatType.INVALID_FORMAT
    
    def test_scan_statistics(self):
        """Test scan statistics tracking."""
        initial_stats = self.scanner.get_scan_statistics()
        assert initial_stats['total_scans'] == 0
        
        # Perform some scans
        test_file = self.temp_path / "stats_test.txt"
        test_file.write_text("test")
        
        # Safe file
        self.scanner.scan_file(test_file)
        
        # Malicious file
        malicious_file = self.temp_path / "malicious.py"
        malicious_file.write_text("import os\nos.system('dangerous')")
        self.scanner.scan_file(malicious_file)
        
        stats = self.scanner.get_scan_statistics()
        assert stats['total_scans'] == 2
        assert stats['safe_files'] >= 1
        assert stats['avg_scan_time'] > 0
    
    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        # Generate some statistics
        test_file = self.temp_path / "reset_test.txt"
        test_file.write_text("test")
        self.scanner.scan_file(test_file)
        
        # Verify stats exist
        stats = self.scanner.get_scan_statistics()
        assert stats['total_scans'] > 0
        
        # Reset and verify
        self.scanner.reset_statistics()
        stats = self.scanner.get_scan_statistics()
        assert stats['total_scans'] == 0
        assert stats['safe_files'] == 0


class TestEnums:
    """Test security-related enums."""
    
    def test_scan_result_enum(self):
        """Test ScanResult enum values."""
        assert ScanResult.SAFE.value == "safe"
        assert ScanResult.SUSPICIOUS.value == "suspicious"
        assert ScanResult.MALICIOUS.value == "malicious"
        assert ScanResult.ERROR.value == "error"
        assert ScanResult.UNKNOWN.value == "unknown"
    
    def test_threat_type_enum(self):
        """Test ThreatType enum values."""
        assert ThreatType.MALICIOUS_CODE.value == "malicious_code"
        assert ThreatType.PICKLE_EXPLOIT.value == "pickle_exploit"
        assert ThreatType.SUSPICIOUS_IMPORTS.value == "suspicious_imports"
        assert ThreatType.EMBEDDED_EXECUTABLE.value == "embedded_executable"
        assert ThreatType.OVERSIZED_FILE.value == "oversized_file"
        assert ThreatType.INVALID_FORMAT.value == "invalid_format"
        assert ThreatType.HASH_MISMATCH.value == "hash_mismatch"
        assert ThreatType.SCAN_TIMEOUT.value == "scan_timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])