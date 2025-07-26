#!/usr/bin/env python3
"""
Tests for Advanced Search System (Requirements 10-12).
Comprehensive testing for advanced search parameters, categories, and API management.
"""

import unittest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.search.advanced_search import (
    AdvancedSearchParams, BaseModelDetector, UnofficialAPIManager,
    DateRange, DownloadRange, NSFWFilter, ModelQuality, CommercialUse,
    FileFormat, ModelCategory, SortOption, CustomSortMetric, RiskLevel, APIFeature
)
from core.search.search_engine import (
    AdvancedSearchEngine, SearchResult
)


class TestAdvancedSearchParams(unittest.TestCase):
    """Test advanced search parameters per requirement 10."""
    
    def test_requirement_10_1_download_range_filtering(self):
        """Test download range filtering per requirement 10.1."""
        # Test valid download range
        download_range = DownloadRange(min_downloads=100, max_downloads=1000)
        
        # Test models data
        models = [
            {'id': 1, 'name': 'Low Download Model', 'stats': {'downloadCount': 50}},
            {'id': 2, 'name': 'Good Download Model', 'stats': {'downloadCount': 500}},
            {'id': 3, 'name': 'High Download Model', 'stats': {'downloadCount': 2000}}
        ]
        
        filtered = download_range.to_filter(models)
        
        # Should only include model with downloads between 100-1000
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 2)
        
        # Test validation
        errors = download_range.validate()
        self.assertEqual(len(errors), 0)
        
        # Test invalid range
        invalid_range = DownloadRange(min_downloads=1000, max_downloads=100)
        errors = invalid_range.validate()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('less than maximum' in error for error in errors))
    
    def test_requirement_10_2_date_range_filtering(self):
        """Test date range filtering per requirement 10.2."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now() - timedelta(days=1)
        
        date_range = DateRange(start_date=start_date, end_date=end_date)
        
        # Test API parameter conversion
        api_params = date_range.to_api_params()
        
        self.assertIn('periodStartDate', api_params)
        self.assertIn('periodEndDate', api_params)
        self.assertEqual(api_params['period'], 'AllTime')
        
        # Test validation
        errors = date_range.validate()
        self.assertEqual(len(errors), 0)
        
        # Test invalid date range (start > end)
        invalid_range = DateRange(
            start_date=datetime.now(),
            end_date=datetime.now() - timedelta(days=1)
        )
        errors = invalid_range.validate()
        self.assertGreater(len(errors), 0)
    
    def test_requirement_10_3_nsfw_filtering(self):
        """Test NSFW content filtering per requirement 10.3."""
        search_params = AdvancedSearchParams(
            query="test",
            nsfw_filter=NSFWFilter.SFW_ONLY
        )
        
        api_params = search_params.to_api_params()
        
        self.assertEqual(api_params['nsfw'], 'false')
        self.assertEqual(api_params['query'], 'test')
    
    def test_requirement_10_4_quality_filtering(self):
        """Test quality filtering per requirement 10.4."""
        # Test verified models only
        search_params = AdvancedSearchParams(
            quality_filter=ModelQuality.VERIFIED
        )
        
        api_params = search_params.to_api_params()
        self.assertTrue(api_params.get('verified'))
        
        # Test featured models only
        search_params = AdvancedSearchParams(
            quality_filter=ModelQuality.FEATURED
        )
        
        api_params = search_params.to_api_params()
        self.assertTrue(api_params.get('featured'))
        
        # Test both verified and featured
        search_params = AdvancedSearchParams(
            quality_filter=ModelQuality.VERIFIED_AND_FEATURED
        )
        
        api_params = search_params.to_api_params()
        self.assertTrue(api_params.get('verified'))
        self.assertTrue(api_params.get('featured'))
    
    def test_requirement_10_5_commercial_filtering(self):
        """Test commercial use filtering per requirement 10.5."""
        search_params = AdvancedSearchParams(
            commercial_filter=CommercialUse.COMMERCIAL_ALLOWED
        )
        
        api_params = search_params.to_api_params()
        self.assertTrue(api_params.get('allowCommercialUse'))
        
        # Test non-commercial only
        search_params = AdvancedSearchParams(
            commercial_filter=CommercialUse.NON_COMMERCIAL_ONLY
        )
        
        api_params = search_params.to_api_params()
        self.assertFalse(api_params.get('allowCommercialUse'))
    
    def test_requirement_10_6_file_format_preferences(self):
        """Test file format preferences per requirement 10.6."""
        # Test SafeTensors only (default)
        search_params = AdvancedSearchParams()
        self.assertEqual(search_params.file_format, FileFormat.SAFETENSORS_ONLY)
        
        # Test pickle allowed
        search_params = AdvancedSearchParams(
            file_format=FileFormat.PICKLE_ALLOWED
        )
        self.assertEqual(search_params.file_format, FileFormat.PICKLE_ALLOWED)
    
    def test_parameter_validation(self):
        """Test comprehensive parameter validation."""
        # Test valid parameters
        search_params = AdvancedSearchParams(
            query="test",
            limit=100,
            page=1
        )
        
        errors = search_params.validate()
        self.assertEqual(len(errors), 0)
        
        # Test invalid parameters
        invalid_params = AdvancedSearchParams(
            limit=0,  # Invalid
            page=0   # Invalid
        )
        
        errors = invalid_params.validate()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('positive' in error for error in errors))
        
        # Test API limit enforcement in to_api_params (limit is capped at 100)
        high_limit_params = AdvancedSearchParams(limit=300)
        api_params = high_limit_params.to_api_params()
        self.assertEqual(api_params['limit'], 100)  # Should be capped at 100


class TestModelCategories(unittest.TestCase):
    """Test model categories per requirement 11.1."""
    
    def test_requirement_11_1_category_support(self):
        """Test support for categories aligned with SQL migration."""
        expected_categories = [
            "character", "style", "concept", "clothing", "background", 
            "tool", "building", "vehicle", "object", "animal",
            "body", "outfit", "base", "action", "workflow", "wildcards"
        ]
        
        # Verify all categories are available
        available_categories = [cat.value for cat in ModelCategory]
        
        for expected in expected_categories:
            self.assertIn(expected, available_categories)
        
        self.assertEqual(len(ModelCategory), 16)
    
    def test_category_integration_with_tags(self):
        """Test category integration with tag system per requirement 11.5."""
        search_params = AdvancedSearchParams(
            categories=[ModelCategory.CHARACTER, ModelCategory.STYLE],
            tags=["anime", "portrait"]
        )
        
        api_params = search_params.to_api_params()
        
        # Categories and tags should be separate in API params
        expected_tags = ["anime", "portrait"]
        expected_categories = ["character", "style"]
        self.assertEqual(api_params['tag'], expected_tags)
        self.assertEqual(api_params['categories'], expected_categories)


class TestCustomSorting(unittest.TestCase):
    """Test custom sorting per requirement 11.3."""
    
    def test_requirement_11_3_custom_sort_metrics(self):
        """Test custom sort metrics per requirement 11.3."""
        # Test tipped amount sorting
        search_params = AdvancedSearchParams(
            custom_sort=CustomSortMetric.TIPPED_AMOUNT
        )
        
        api_params = search_params.to_api_params()
        self.assertEqual(api_params['sort'], 'metrics.tippedAmountCount:desc')
        
        # Test comment count sorting
        search_params = AdvancedSearchParams(
            custom_sort=CustomSortMetric.COMMENT_COUNT
        )
        
        api_params = search_params.to_api_params()
        self.assertEqual(api_params['sort'], 'metrics.commentCount:desc')
    
    def test_sort_fallback(self):
        """Test sort fallback per requirement 11.4."""
        # Test with fallback enabled
        search_params = AdvancedSearchParams(
            custom_sort=CustomSortMetric.TIPPED_AMOUNT,
            sort_fallback=True
        )
        
        self.assertTrue(search_params.sort_fallback)


class TestBaseModelDetector(unittest.TestCase):
    """Test base model detection per requirement 11.6."""
    
    def setUp(self):
        """Set up base model detector."""
        self.detector = BaseModelDetector()
    
    def test_requirement_11_6_base_model_support(self):
        """Test support for 50+ base models per requirement 11.6."""
        known_models = self.detector.known_models
        
        # Verify we have 50+ known models
        self.assertGreaterEqual(len(known_models), 50)
        
        # Verify specific models mentioned in requirements
        expected_models = ['Illustrious', 'NoobAI', 'Pony', 'SDXL 1.0']
        for model in expected_models:
            self.assertIn(model, known_models)
    
    def test_dynamic_model_detection(self):
        """Test dynamic model detection."""
        # Test model with explicit base model
        model_data = {
            'id': 1,
            'name': 'Test Model',
            'baseModel': 'SDXL 1.0'
        }
        
        detected = self.detector.detect_base_model(model_data)
        self.assertEqual(detected, 'SDXL 1.0')
        
        # Test model with base model in name
        model_data = {
            'id': 2,
            'name': 'Anime Style SDXL Model',
            'description': 'A model for SDXL'
        }
        
        detected = self.detector.detect_base_model(model_data)
        self.assertIsNotNone(detected)
        self.assertIn('SDXL', detected.upper())
        
        # Test model with base model in tags
        model_data = {
            'id': 3,
            'name': 'Character Model',
            'tags': [{'name': 'Pony Diffusion'}, {'name': 'character'}]
        }
        
        detected = self.detector.detect_base_model(model_data)
        self.assertIsNotNone(detected)
        
        # Test unknown model detection
        model_data = {
            'id': 4,
            'name': 'Unknown Base Model XYZ',
            'description': 'A model using XYZ architecture'
        }
        
        detected = self.detector.detect_base_model(model_data)
        # Should return None for truly unknown models
        # Or detect pattern if it matches our regex patterns


class TestUnofficialAPIManager(unittest.TestCase):
    """Test unofficial API management per requirement 12."""
    
    def setUp(self):
        """Set up API manager."""
        self.manager = UnofficialAPIManager()
    
    def test_requirement_12_1_official_priority_mode(self):
        """Test official priority mode per requirement 12.1."""
        # Test official priority mode
        self.assertTrue(self.manager.official_priority_mode)
        
        # Try to enable unofficial feature in official mode
        result = self.manager.enable_feature('advanced_sorting')
        self.assertFalse(result)  # Should fail in official priority mode
        
        # Disable official priority mode
        self.manager.official_priority_mode = False
        result = self.manager.enable_feature('advanced_sorting')
        self.assertTrue(result)  # Should succeed now
    
    def test_requirement_12_2_risk_level_management(self):
        """Test risk level management per requirement 12.2."""
        features = self.manager.features
        
        # Verify risk levels are assigned
        self.assertEqual(features['basic_search'].risk_level, RiskLevel.LOW)
        self.assertEqual(features['advanced_sorting'].risk_level, RiskLevel.MEDIUM)
        self.assertEqual(features['undocumented_endpoints'].risk_level, RiskLevel.HIGH)
        self.assertEqual(features['rate_limit_bypass'].risk_level, RiskLevel.CRITICAL)
        
        # Test critical feature requires force enable
        result = self.manager.enable_feature('rate_limit_bypass')
        self.assertFalse(result)  # Should fail without force
        
        # Disable official priority mode to test force enable
        self.manager.official_priority_mode = False
        result = self.manager.enable_feature('rate_limit_bypass', force=True)
        self.assertTrue(result)  # Should succeed with force when not in official mode
    
    def test_requirement_12_3_feature_detection(self):
        """Test API capability detection per requirement 12.3."""
        # Mock API response
        api_response = {
            'items': [
                {
                    'id': 1,
                    'name': 'Test Model',
                    'stats': {'downloadCount': 100},
                    'metrics': {'rating': 4.5},
                    'allowCommercialUse': True,
                    'nsfw': False,
                    'tags': [{'name': 'anime'}]
                }
            ],
            'metadata': {'totalPages': 10},
            'totalPages': 10,
            'nextCursor': 'abc123'
        }
        
        detected = self.manager.detect_api_capabilities(api_response)
        
        expected_capabilities = {
            'metadata_support', 'pagination_metadata', 'cursor_pagination',
            'detailed_statistics', 'license_filtering', 'nsfw_classification',
            'tag_system'
        }
        
        # Should detect most of these capabilities
        self.assertGreaterEqual(len(detected.intersection(expected_capabilities)), 5)
    
    def test_requirement_12_4_fallback_mechanisms(self):
        """Test fallback mechanisms per requirement 12.4."""
        # Test fallback strategy for advanced sorting
        fallbacks = self.manager.get_fallback_strategy('advanced_sorting')
        expected_fallbacks = ['basic_sorting', 'no_sorting']
        self.assertEqual(fallbacks, expected_fallbacks)
        
        # Test fallback for bulk operations
        fallbacks = self.manager.get_fallback_strategy('bulk_operations')
        self.assertIn('individual_requests', fallbacks)
        
        # Test no fallback for critical features
        fallbacks = self.manager.get_fallback_strategy('rate_limit_bypass')
        self.assertEqual(len(fallbacks), 0)
    
    def test_requirement_12_6_usage_statistics(self):
        """Test usage statistics tracking per requirement 12.6."""
        # Record some usage
        self.manager.record_feature_usage('basic_search', True, 1.5)
        self.manager.record_feature_usage('basic_search', True, 2.0)
        self.manager.record_feature_usage('advanced_sorting', False)
        
        stats = self.manager.get_usage_statistics()
        
        # Verify structure
        self.assertIn('official_features', stats)
        self.assertIn('unofficial_features', stats)
        self.assertIn('feature_details', stats)
        self.assertIn('configuration', stats)
        
        # Verify official feature stats
        official_stats = stats['official_features']
        self.assertEqual(official_stats['success_count'], 2)
        self.assertEqual(official_stats['failure_count'], 0)
        self.assertEqual(official_stats['success_rate'], 1.0)
        
        # Verify unofficial feature stats
        unofficial_stats = stats['unofficial_features']
        self.assertEqual(unofficial_stats['success_count'], 0)
        self.assertEqual(unofficial_stats['failure_count'], 1)
        self.assertEqual(unofficial_stats['success_rate'], 0.0)
        
        # Verify feature details
        basic_search_stats = stats['feature_details']['basic_search']
        self.assertEqual(basic_search_stats['usage_count'], 2)
        self.assertEqual(basic_search_stats['error_count'], 0)
        self.assertEqual(basic_search_stats['success_rate'], 1.0)


class TestLocalVersionFilter(unittest.TestCase):
    """Test local version filtering system per requirement 11.2."""
    
    def setUp(self):
        """Set up local version filter."""
        from core.search.search_engine import LocalVersionFilter
        self.filter_engine = LocalVersionFilter()
    
    def test_requirement_11_2_triple_filtering(self):
        """Test category × tag × type filtering per requirement 11.2."""
        # Test models
        models = [
            {
                'id': 1,
                'name': 'Anime Character Model',
                'type': 'LORA',
                'tags': [{'name': 'character'}, {'name': 'anime'}],
                'modelVersions': [{'files': [{'name': 'model.safetensors'}]}]
            },
            {
                'id': 2,
                'name': 'Style Transfer Model',
                'type': 'Checkpoint',
                'tags': [{'name': 'style'}, {'name': 'art'}],
                'modelVersions': [{'files': [{'name': 'model.ckpt'}]}]
            },
            {
                'id': 3,
                'name': 'Vehicle Concept',
                'type': 'LORA',
                'tags': [{'name': 'vehicle'}, {'name': 'concept'}],
                'modelVersions': [{'files': [{'name': 'model.safetensors'}]}]
            }
        ]
        
        # Test triple filtering
        search_params = AdvancedSearchParams(
            categories=[ModelCategory.CHARACTER],
            tags=['anime'],
            model_types=['LORA']
        )
        
        # Convert search params to filter arguments
        categories = [cat.value.lower() for cat in search_params.categories] if search_params.categories else None
        
        filtered, stats = self.filter_engine.filter_by_version_criteria(
            models, 
            base_model=search_params.base_model,
            model_types=search_params.model_types,
            categories=categories
        )
        
        # Should only return the anime character LORA
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 1)
        
        # Verify filter statistics
        self.assertEqual(stats['models_processed'], 3)
        self.assertGreater(stats['models_removed'], 0)


class TestSearchEngineIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integrated advanced search engine."""
    
    def setUp(self):
        """Set up search engine with mocked API client."""
        # Mock API client
        self.mock_api_client = AsyncMock()
        self.mock_api_client.search_models = AsyncMock()
        
        # Initialize search engine
        self.search_engine = AdvancedSearchEngine(api_client=self.mock_api_client)
    
    async def test_integrated_search_functionality(self):
        """Test integrated search with all components."""
        # Mock API response
        mock_response = {
            'items': [
                {
                    'id': 1,
                    'name': 'Test Character Model',
                    'type': 'LORA',
                    'tags': [{'name': 'character'}, {'name': 'anime'}],
                    'allowCommercialUse': True,
                    'nsfw': False,
                    'modelVersions': [{
                        'files': [{'name': 'model.safetensors', 'sizeKB': 1000}]
                    }]
                }
            ],
            'totalItems': 1
        }
        
        self.mock_api_client.search_models.return_value = mock_response
        
        # Create search parameters
        search_params = AdvancedSearchParams(
            query="character",
            categories=[ModelCategory.CHARACTER],
            tags=['anime'],
            model_types=['LORA'],
            commercial_filter=CommercialUse.COMMERCIAL_ALLOWED,
            file_format=FileFormat.SAFETENSORS_ONLY
        )
        
        # Execute search
        result = await self.search_engine.search(search_params)
        
        # Verify result
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(len(result.models), 1)
        self.assertEqual(result.models[0]['id'], 1)
        
        # Verify API was called
        self.mock_api_client.search_models.assert_called_once()
        
        # Verify filter metadata
        self.assertIn('categories', result.filter_applied)
        self.assertIn('character', result.filter_applied['categories'])
    
    def test_search_statistics_tracking(self):
        """Test search statistics tracking."""
        initial_stats = self.search_engine.get_search_statistics()
        
        self.assertIn('search_performance', initial_stats)
        self.assertIn('unofficial_api_stats', initial_stats)
        self.assertIn('base_model_detection', initial_stats)
        self.assertIn('filter_statistics', initial_stats)
        
        # Verify initial state
        perf_stats = initial_stats['search_performance']
        self.assertEqual(perf_stats['total_searches'], 0)
        self.assertEqual(perf_stats['successful_searches'], 0)
    
    def test_unofficial_feature_configuration(self):
        """Test unofficial feature configuration."""
        # Configure with low risk tolerance
        self.search_engine.configure_unofficial_features(
            enable_advanced=False,
            risk_tolerance='low'
        )
        
        # Only official and low-risk features should be enabled
        features = self.search_engine.unofficial_api_manager.features
        self.assertTrue(features['basic_search'].enabled)
        self.assertFalse(features['advanced_sorting'].enabled)
        
        # Disable official priority mode to allow unofficial features
        self.search_engine.unofficial_api_manager.official_priority_mode = False
        
        # Configure with high risk tolerance
        self.search_engine.configure_unofficial_features(
            enable_advanced=True,
            risk_tolerance='high'
        )
        
        # More features should be enabled now
        self.assertTrue(features['advanced_sorting'].enabled)


if __name__ == '__main__':
    unittest.main(verbosity=2)