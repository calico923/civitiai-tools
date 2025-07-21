#!/usr/bin/env python3
"""
Tests for License Manager (Requirement 9).
Comprehensive testing for license information and compliance management.
"""

import unittest
import time
from unittest.mock import Mock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.security.license_manager import (
    LicenseManager, LicenseInfo, LicenseFilterConfig,
    LicenseType, LicenseStatus
)


class TestLicenseManager(unittest.TestCase):
    """Test license manager implementation per requirement 9."""
    
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
    
    def test_license_status_parsing(self):
        """Test license status value parsing."""
        test_cases = [
            (True, LicenseStatus.ALLOWED),
            (False, LicenseStatus.DISALLOWED),
            ('allowed', LicenseStatus.ALLOWED),
            ('disallowed', LicenseStatus.DISALLOWED),
            ('required', LicenseStatus.REQUIRED),
            (None, LicenseStatus.UNKNOWN),
            ('unknown', LicenseStatus.UNKNOWN)
        ]
        
        for input_value, expected_status in test_cases:
            model_data = {
                'id': 1,
                'allowCommercialUse': input_value,
                'allowDerivatives': input_value,
                'allowDifferentLicense': input_value,
                'allowNoCredit': input_value
            }
            
            license_info = self.manager.extract_license_info(model_data)
            
            self.assertEqual(license_info.allow_commercial_use, expected_status)
            self.assertEqual(license_info.allow_derivatives, expected_status)
            self.assertEqual(license_info.allow_different_license, expected_status)
            self.assertEqual(license_info.allow_no_credit, expected_status)
    
    def test_requirement_9_5_compliance_warnings(self):
        """Test license compliance warnings per requirement 9.5."""
        # Test commercial use warning
        commercial_restricted = LicenseInfo(
            allow_commercial_use=LicenseStatus.DISALLOWED,
            allow_derivatives=LicenseStatus.ALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.ALLOWED
        )
        
        warnings = self.manager.check_compliance_warnings(
            commercial_restricted, intended_use="commercial"
        )
        
        self.assertTrue(any("Commercial use is explicitly disallowed" in w for w in warnings))
        
        # Test derivative work warning
        derivative_restricted = LicenseInfo(
            allow_commercial_use=LicenseStatus.ALLOWED,
            allow_derivatives=LicenseStatus.DISALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.ALLOWED
        )
        
        warnings = self.manager.check_compliance_warnings(
            derivative_restricted, intended_use="derivative"
        )
        
        self.assertTrue(any("Derivative works are not allowed" in w for w in warnings))
        
        # Test attribution warning
        attribution_required = LicenseInfo(
            allow_commercial_use=LicenseStatus.ALLOWED,
            allow_derivatives=LicenseStatus.ALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.DISALLOWED
        )
        
        warnings = self.manager.check_compliance_warnings(attribution_required)
        
        self.assertTrue(any("Attribution required" in w for w in warnings))
        
        # Test unknown license warnings
        unknown_license = LicenseInfo(
            allow_commercial_use=LicenseStatus.UNKNOWN,
            allow_derivatives=LicenseStatus.UNKNOWN,
            allow_different_license=LicenseStatus.UNKNOWN,
            allow_no_credit=LicenseStatus.UNKNOWN
        )
        
        warnings = self.manager.check_compliance_warnings(unknown_license)
        
        self.assertTrue(any("License terms unclear" in w for w in warnings))
        
        # Verify warnings are logged
        self.assertGreater(len(self.manager.compliance_warnings), 0)
    
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
    
    def test_license_filter_config(self):
        """Test comprehensive license filtering configuration."""
        # Create test models with different license configurations
        models = [
            {
                'id': 1,
                'name': 'Fully Open Model',
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True
            },
            {
                'id': 2,
                'name': 'Commercial + Attribution Model',
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': False
            },
            {
                'id': 3,
                'name': 'Non-Commercial Model',
                'allowCommercialUse': False,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True
            },
            {
                'id': 4,
                'name': 'No Derivatives Model',
                'allowCommercialUse': True,
                'allowDerivatives': False,
                'allowDifferentLicense': False,
                'allowNoCredit': True
            }
        ]
        
        # Test commercial use only filter
        commercial_filter = LicenseFilterConfig(commercial_use_only=True)
        filtered = self.manager.apply_license_filter(models, commercial_filter)
        
        # Should include models 1, 2, 4 (commercial allowed)
        filtered_ids = [m['id'] for m in filtered]
        self.assertIn(1, filtered_ids)
        self.assertIn(2, filtered_ids)
        self.assertIn(4, filtered_ids)
        self.assertNotIn(3, filtered_ids)
        
        # Test derivatives required filter
        derivatives_filter = LicenseFilterConfig(require_derivatives=True)
        filtered = self.manager.apply_license_filter(models, derivatives_filter)
        
        # Should include models 1, 2, 3 (derivatives allowed)
        filtered_ids = [m['id'] for m in filtered]
        self.assertIn(1, filtered_ids)
        self.assertIn(2, filtered_ids)
        self.assertIn(3, filtered_ids)
        self.assertNotIn(4, filtered_ids)
        
        # Test attribution optional filter
        no_attribution_filter = LicenseFilterConfig(attribution_optional=True)
        filtered = self.manager.apply_license_filter(models, no_attribution_filter)
        
        # Should include models 1, 3, 4 (no credit required)
        filtered_ids = [m['id'] for m in filtered]
        self.assertIn(1, filtered_ids)
        self.assertIn(3, filtered_ids)
        self.assertIn(4, filtered_ids)
        self.assertNotIn(2, filtered_ids)
        
        # Test combined filters
        strict_filter = LicenseFilterConfig(
            commercial_use_only=True,
            require_derivatives=True
        )
        filtered = self.manager.apply_license_filter(models, strict_filter)
        
        # Should include models 1, 2 (commercial + derivatives)
        filtered_ids = [m['id'] for m in filtered]
        self.assertIn(1, filtered_ids)
        self.assertIn(2, filtered_ids)
        self.assertNotIn(3, filtered_ids)  # not commercial
        self.assertNotIn(4, filtered_ids)  # no derivatives
    
    def test_license_summary_generation(self):
        """Test license summary generation per requirement 9.5."""
        models = [
            {
                'id': 1,
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True,
                'license': 'MIT'
            },
            {
                'id': 2,
                'allowCommercialUse': False,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': False,
                'license': 'CC BY-NC'
            },
            {
                'id': 3,
                'allowCommercialUse': True,
                'allowDerivatives': False,
                'allowDifferentLicense': False,
                'allowNoCredit': False,
                'license': 'Custom'
            }
        ]
        
        summary = self.manager.get_license_summary(models)
        
        # Verify basic counts
        self.assertEqual(summary['total_models'], 3)
        self.assertEqual(summary['commercial_safe'], 2)  # models 1, 3
        self.assertEqual(summary['requires_attribution'], 2)  # models 2, 3
        self.assertEqual(summary['allows_derivatives'], 2)  # models 1, 2
        
        # Verify percentages
        self.assertAlmostEqual(summary['commercial_safe_percent'], 66.7, places=1)
        self.assertAlmostEqual(summary['attribution_required_percent'], 66.7, places=1)
        self.assertAlmostEqual(summary['derivatives_allowed_percent'], 66.7, places=1)
        
        # Verify license types
        self.assertIn('MIT', summary['license_types'])
        self.assertIn('CC BY-NC', summary['license_types'])
        self.assertIn('Custom', summary['license_types'])
    
    def test_license_display_formatting(self):
        """Test license information display formatting."""
        license_info = LicenseInfo(
            allow_commercial_use=LicenseStatus.ALLOWED,
            allow_derivatives=LicenseStatus.DISALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.DISALLOWED,
            license_name="Test License",
            license_description="A test license",
            license_url="https://example.com/license"
        )
        
        # Test compact format
        compact = self.manager.format_license_display(license_info, "compact")
        self.assertIn("✅ Commercial", compact)
        self.assertIn("❌ Derivatives", compact)
        self.assertIn("⚠️  Attribution Required", compact)
        
        # Test table format
        table = self.manager.format_license_display(license_info, "table")
        self.assertIn("License Information:", table)
        self.assertIn("Commercial Use:     allowed", table)
        self.assertIn("Derivatives:        disallowed", table)
        self.assertIn("Test License", table)
        
        # Test detailed format
        detailed = self.manager.format_license_display(license_info, "detailed")
        self.assertIn("License: Test License", detailed)
        self.assertIn("Description: A test license", detailed)
        self.assertIn("License URL: https://example.com/license", detailed)
        self.assertIn("Permissions:", detailed)
    
    def test_license_info_methods(self):
        """Test LicenseInfo convenience methods."""
        # Test commercial safe license
        commercial_license = LicenseInfo(
            allow_commercial_use=LicenseStatus.ALLOWED,
            allow_derivatives=LicenseStatus.ALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.ALLOWED
        )
        
        self.assertTrue(commercial_license.is_commercial_safe())
        self.assertTrue(commercial_license.allows_derivatives())
        self.assertFalse(commercial_license.requires_attribution())
        
        # Test restrictive license
        restrictive_license = LicenseInfo(
            allow_commercial_use=LicenseStatus.DISALLOWED,
            allow_derivatives=LicenseStatus.DISALLOWED,
            allow_different_license=LicenseStatus.DISALLOWED,
            allow_no_credit=LicenseStatus.DISALLOWED
        )
        
        self.assertFalse(restrictive_license.is_commercial_safe())
        self.assertFalse(restrictive_license.allows_derivatives())
        self.assertTrue(restrictive_license.requires_attribution())
    
    def test_compliance_report_export(self):
        """Test comprehensive compliance report export."""
        # Create some test data
        models = [
            {
                'id': 1,
                'allowCommercialUse': True,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': True
            },
            {
                'id': 2,
                'allowCommercialUse': False,
                'allowDerivatives': True,
                'allowDifferentLicense': True,
                'allowNoCredit': False
            }
        ]
        
        # Process models
        for model in models:
            self.manager.extract_license_info(model)
        
        # Generate some warnings
        license_info = self.manager.license_cache[2]
        self.manager.check_compliance_warnings(license_info, "commercial")
        
        # Export report
        report = self.manager.export_compliance_report()
        
        # Verify report structure
        self.assertIn('report_metadata', report)
        self.assertIn('license_cache', report)
        self.assertIn('compliance_warnings', report)
        self.assertIn('summary', report)
        
        # Verify metadata
        self.assertEqual(report['report_metadata']['total_models_processed'], 2)
        self.assertGreater(report['report_metadata']['compliance_warnings_count'], 0)
        
        # Verify cache data
        self.assertEqual(len(report['license_cache']), 2)
        self.assertIn('1', report['license_cache'])
        self.assertIn('2', report['license_cache'])
        
        # Verify warnings
        self.assertGreater(len(report['compliance_warnings']), 0)
    
    def test_license_info_to_dict(self):
        """Test LicenseInfo dictionary conversion."""
        license_info = LicenseInfo(
            allow_commercial_use=LicenseStatus.ALLOWED,
            allow_derivatives=LicenseStatus.DISALLOWED,
            allow_different_license=LicenseStatus.ALLOWED,
            allow_no_credit=LicenseStatus.DISALLOWED,
            license_name="Test License",
            source_model_id=123
        )
        
        data = license_info.to_dict()
        
        # Verify structure
        self.assertIn('license_fields', data)
        self.assertIn('metadata', data)
        self.assertIn('compliance_flags', data)
        
        # Verify license fields
        self.assertEqual(data['license_fields']['allowCommercialUse'], 'allowed')
        self.assertEqual(data['license_fields']['allowDerivatives'], 'disallowed')
        
        # Verify metadata
        self.assertEqual(data['metadata']['license_name'], 'Test License')
        self.assertEqual(data['metadata']['source_model_id'], 123)
        
        # Verify compliance flags
        self.assertTrue(data['compliance_flags']['commercial_safe'])
        self.assertFalse(data['compliance_flags']['allows_derivatives'])
        self.assertTrue(data['compliance_flags']['requires_attribution'])


if __name__ == '__main__':
    unittest.main(verbosity=2)