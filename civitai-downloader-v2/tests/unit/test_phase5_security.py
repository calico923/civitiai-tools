#!/usr/bin/env python3
"""
Tests for Phase 5 Security System (Requirements 9 & 14).
Comprehensive testing for license management and security scanning.
"""

import unittest
import tempfile
import time
from unittest.mock import Mock, patch
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.security.license_manager import (
    LicenseManager, LicenseInfo, LicenseFilterConfig,
    LicenseType, LicenseStatus
)
from core.security.security_scanner import (
    SecurityScanner, SecurityScanResult, FileIntegrityCheck, PrivacyAssessment,
    ScanStatus, HashAlgorithm, PrivacyRisk
)


class TestLicenseManagerPhase5(unittest.TestCase):
    """Test Phase 5 license manager implementation per requirement 9."""
    
    def setUp(self):
        """Set up test environment."""
        self.manager = LicenseManager()
    
    def test_requirement_9_1_license_field_extraction(self):
        """Test extraction of 4 license fields per requirement 9.1."""
        # Test model data with all license fields
        model_data = {
            'id': 123,
            'name': 'Test Model',
            'allowCommercialUse': True,
            'allowDerivatives': False,
            'allowDifferentLicense': 'allowed',
            'allowNoCredit': 'disallowed',
            'license': 'Custom License',
            'licenseUrl': 'https://example.com/license',
            'licenseDescription': 'A custom license for testing'
        }
        
        license_info = self.manager.extract_license_info(model_data)
        
        # Verify all 4 required fields are extracted
        self.assertEqual(license_info.allow_commercial_use, LicenseStatus.ALLOWED)
        self.assertEqual(license_info.allow_derivatives, LicenseStatus.DISALLOWED)
        self.assertEqual(license_info.allow_different_license, LicenseStatus.ALLOWED)
        self.assertEqual(license_info.allow_no_credit, LicenseStatus.DISALLOWED)
        
        # Verify metadata
        self.assertEqual(license_info.license_name, 'Custom License')
        self.assertEqual(license_info.license_url, 'https://example.com/license')
        self.assertEqual(license_info.license_description, 'A custom license for testing')
        self.assertEqual(license_info.source_model_id, 123)
        
        # Verify cached
        self.assertIn(123, self.manager.license_cache)
    
    def test_requirement_9_6_commercial_filtering(self):
        """Test commercial use filtering per requirement 9.6."""
        models = [
            {
                'id': 1,
                'name': 'Commercial Model',
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': False
            },
            {
                'id': 2,
                'name': 'Non-Commercial Model',
                'allowCommercialUse': False,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True
            },
            {
                'id': 3,
                'name': 'Unknown License Model',
                'allowCommercialUse': None,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True
            }
        ]
        
        commercial_models = self.manager.filter_commercial_models(models)
        
        # Only commercially safe model should pass
        self.assertEqual(len(commercial_models), 1)
        self.assertEqual(commercial_models[0]['id'], 1)
        
        # Verify compliance metadata added
        self.assertIn('license_compliance', commercial_models[0])
        self.assertTrue(commercial_models[0]['license_compliance']['commercial_safe'])


class TestSecurityScannerPhase5(unittest.TestCase):
    """Test Phase 5 security scanner implementation per requirements 9 and 14."""
    
    def setUp(self):
        """Set up test environment."""
        self.scanner = SecurityScanner()
    
    def test_requirement_9_2_virus_and_pickle_scanning(self):
        """Test virus and pickle scanning per requirement 9.2."""
        # Test safe file
        safe_file = {
            'id': 1,
            'name': 'model.safetensors',
            'sizeKB': 5000
        }
        
        result = self.scanner.perform_security_scan(safe_file)
        
        # Verify scan result structure
        self.assertIsInstance(result, SecurityScanResult)
        self.assertIsInstance(result.scan_timestamp, float)
        self.assertIsNotNone(result.scanner_version)
        
        # SafeTensors should be clean for pickle scan
        self.assertEqual(result.pickle_scan_status, ScanStatus.CLEAN)
        
        # Test suspicious file
        suspicious_file = {
            'id': 2,
            'name': 'malware.exe',
            'sizeKB': 100
        }
        
        result = self.scanner.perform_security_scan(suspicious_file)
        
        # Should be flagged as suspicious
        self.assertEqual(result.virus_scan_status, ScanStatus.SUSPICIOUS)
        self.assertIsNotNone(result.virus_scan_details)
        
        # Test pickle file
        pickle_file = {
            'id': 3,
            'name': 'model.pkl',
            'sizeKB': 2000
        }
        
        result = self.scanner.perform_security_scan(pickle_file)
        
        # Pickle files should require scanning
        self.assertEqual(result.pickle_scan_status, ScanStatus.PENDING)
        self.assertIn('pickle', result.pickle_scan_details['notes'].lower())
    
    def test_requirement_9_4_file_integrity_verification(self):
        """Test file integrity verification with 6 hash algorithms per requirement 9.4."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Hello, World!")
            temp_path = Path(f.name)
        
        try:
            # Test hash calculation with all algorithms
            integrity_check = self.scanner.calculate_file_hashes(temp_path)
            
            # Verify all 6 algorithms are supported
            expected_algorithms = [
                HashAlgorithm.MD5,
                HashAlgorithm.SHA1,
                HashAlgorithm.SHA256,
                HashAlgorithm.SHA384,
                HashAlgorithm.SHA512,
                HashAlgorithm.BLAKE2B
            ]
            
            for algorithm in expected_algorithms:
                self.assertIn(algorithm, integrity_check.hash_results)
                self.assertIsInstance(integrity_check.hash_results[algorithm], str)
                self.assertGreater(len(integrity_check.hash_results[algorithm]), 0)
        
        finally:
            # Clean up
            temp_path.unlink()
    
    def test_requirement_14_1_privacy_risk_assessment(self):
        """Test privacy risk assessment per requirement 14.1."""
        # Test celebrity model
        celebrity_model = {
            'id': 1,
            'name': 'Taylor Swift LoRA',
            'description': 'A model trained on celebrity photos',
            'tags': [
                {'name': 'celebrity'},
                {'name': 'famous'},
                {'name': 'singer'}
            ]
        }
        
        assessment = self.scanner.assess_privacy_risks(celebrity_model)
        
        self.assertEqual(assessment.model_id, 1)
        self.assertTrue(assessment.celebrity_detected)
        self.assertEqual(assessment.privacy_risk_level, PrivacyRisk.HIGH)
        self.assertGreater(len(assessment.identified_risks), 0)
        self.assertTrue(any('celebrity' in risk.lower() for risk in assessment.identified_risks))
    
    def test_requirement_14_2_user_consent_requirements(self):
        """Test user consent requirements per requirement 14.2."""
        # High risk model should require consent
        high_risk_model = {
            'id': 1,
            'name': 'Celebrity Model',
            'description': 'Famous person model',
            'tags': [{'name': 'celebrity'}]
        }
        
        assessment = self.scanner.assess_privacy_risks(high_risk_model)
        
        self.assertTrue(assessment.requires_user_consent())
        
        warning_message = assessment.get_warning_message()
        self.assertIn('Celebrity model detected', warning_message)
        self.assertIn('Special handling required', warning_message)


class TestIntegratedSecuritySystem(unittest.TestCase):
    """Test integrated security system with both license and security components."""
    
    def setUp(self):
        """Set up integrated test environment."""
        self.license_manager = LicenseManager()
        self.security_scanner = SecurityScanner()
    
    def test_integrated_model_processing(self):
        """Test integrated processing of model with license and security checks."""
        # Test model with both license and security concerns
        test_model = {
            'id': 1,
            'name': 'Celebrity Commercial Model',
            'description': 'A commercial celebrity model for advertising',
            'allowCommercialUse': True,
            'allowDerivatives': False,
            'allowDifferentLicense': False,
            'allowNoCredit': False,
            'tags': [
                {'name': 'celebrity'},
                {'name': 'commercial'}
            ]
        }
        
        # Extract license information
        license_info = self.license_manager.extract_license_info(test_model)
        
        # Assess privacy risks
        privacy_assessment = self.security_scanner.assess_privacy_risks(test_model)
        
        # Check compliance warnings
        warnings = self.license_manager.check_compliance_warnings(license_info, "commercial")
        
        # Verify integrated results
        self.assertTrue(license_info.is_commercial_safe())  # Commercial use allowed
        self.assertTrue(privacy_assessment.celebrity_detected)  # Celebrity detected
        self.assertTrue(privacy_assessment.requires_user_consent())  # Consent required
        
        # Should have attribution warning (allowNoCredit = False)
        self.assertTrue(any('Attribution required' in w for w in warnings))
        
        # Create comprehensive report
        integrated_report = {
            'model_id': test_model['id'],
            'license_compliance': license_info.to_dict(),
            'privacy_assessment': privacy_assessment.to_dict(),
            'compliance_warnings': warnings,
            'recommended_actions': []
        }
        
        # Add recommendations based on findings
        if privacy_assessment.requires_user_consent():
            integrated_report['recommended_actions'].append(
                "Obtain user consent before using this celebrity model"
            )
        
        if license_info.requires_attribution():
            integrated_report['recommended_actions'].append(
                "Ensure proper attribution is provided as required by license"
            )
        
        # Verify integrated report structure
        self.assertIn('license_compliance', integrated_report)
        self.assertIn('privacy_assessment', integrated_report)
        self.assertIn('recommended_actions', integrated_report)
        self.assertGreater(len(integrated_report['recommended_actions']), 0)
    
    def test_security_audit_with_license_compliance(self):
        """Test comprehensive security audit including license compliance."""
        # Process multiple test models
        test_models = [
            {
                'id': 1,
                'name': 'Safe Commercial Model',
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True,
                'tags': [{'name': 'art'}]
            },
            {
                'id': 2,
                'name': 'Celebrity Non-Commercial',
                'allowCommercialUse': False,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': False,
                'tags': [{'name': 'celebrity'}]
            }
        ]
        
        # Process all models
        for model in test_models:
            self.license_manager.extract_license_info(model)
            self.security_scanner.assess_privacy_risks(model)
        
        # Generate comprehensive audit
        license_report = self.license_manager.export_compliance_report()
        security_audit = self.security_scanner.export_security_audit()
        
        # Create integrated audit report
        integrated_audit = {
            'audit_metadata': {
                'generated_at': time.time(),
                'models_processed': len(test_models)
            },
            'license_compliance': license_report,
            'security_assessment': security_audit,
            'recommendations': []
        }
        
        # Verify comprehensive audit structure
        self.assertIn('license_compliance', integrated_audit)
        self.assertIn('security_assessment', integrated_audit)
        self.assertEqual(integrated_audit['audit_metadata']['models_processed'], 2)
        
        # Verify license compliance data
        self.assertGreater(
            len(integrated_audit['license_compliance']['license_cache']), 0
        )
        
        # Verify security assessment data
        self.assertGreater(
            len(integrated_audit['security_assessment']['privacy_assessments']), 0
        )
    
    def test_file_security_with_license_validation(self):
        """Test file security scanning with license validation."""
        # Test file information
        test_file = {
            'id': 1,
            'name': 'model.safetensors',
            'sizeKB': 5000,
            'metadata': {
                'licenseUrl': 'https://example.com/license',
                'allowCommercialUse': True
            }
        }
        
        # Perform security scan
        scan_result = self.security_scanner.perform_security_scan(test_file)
        
        # Extract license from metadata if available
        if 'metadata' in test_file:
            license_info = self.license_manager.extract_license_info(test_file['metadata'])
            
            # Verify license extraction
            self.assertEqual(license_info.allow_commercial_use, LicenseStatus.ALLOWED)
        
        # Verify security scan
        self.assertIsInstance(scan_result, SecurityScanResult)
        self.assertEqual(scan_result.pickle_scan_status, ScanStatus.CLEAN)  # SafeTensors
        
        # Create integrated file report
        file_report = {
            'file_id': test_file['id'],
            'security_scan': scan_result.to_dict(),
            'license_info': license_info.to_dict() if 'metadata' in test_file else None,
            'safe_to_download': scan_result.is_safe() and not scan_result.has_risks()
        }
        
        # Verify integrated file report
        self.assertIn('security_scan', file_report)
        self.assertIn('license_info', file_report)
        self.assertTrue(file_report['safe_to_download'])


if __name__ == '__main__':
    unittest.main(verbosity=2)