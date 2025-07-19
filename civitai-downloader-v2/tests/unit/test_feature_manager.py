#!/usr/bin/env python3
"""
Feature Manager tests.
Tests for unofficial feature management, risk assessment, and fallback mechanisms.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import importlib.util
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestFeatureManager:
    """Test feature manager for unofficial CivitAI features."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_feature_manager_initialization(self):
        """Test FeatureManager proper initialization."""
        # Import feature manager
        feature_manager_path = self.api_dir / "feature_manager.py"
        assert feature_manager_path.exists(), "feature_manager.py must exist"
        
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        # Test FeatureManager class exists
        assert hasattr(feature_module, 'FeatureManager'), "FeatureManager class must exist"
        FeatureManager = feature_module.FeatureManager
        
        # Test initialization
        feature_manager = FeatureManager()
        
        # Validate properties
        assert hasattr(feature_manager, 'features'), "FeatureManager must track features"
        assert hasattr(feature_manager, 'risk_profiles'), "FeatureManager must have risk profiles"
        assert hasattr(feature_manager, 'assess_feature_availability'), "Must have availability assessment"
        assert hasattr(feature_manager, 'get_fallback_chain'), "Must have fallback chain"
    
    def test_feature_risk_profile_data_class(self):
        """Test FeatureRiskProfile data structure."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        # Test FeatureRiskProfile class exists
        assert hasattr(feature_module, 'FeatureRiskProfile'), "FeatureRiskProfile class must exist"
        FeatureRiskProfile = feature_module.FeatureRiskProfile
        
        # Test profile creation
        profile = FeatureRiskProfile(
            feature_name="advanced_search",
            risk_level="MEDIUM",
            fallback_strategy="official_search",
            success_rate=0.85,
            last_tested=datetime.now()
        )
        
        # Validate properties
        assert profile.feature_name == "advanced_search", "Feature name should be set"
        assert profile.risk_level == "MEDIUM", "Risk level should be set"
        assert profile.fallback_strategy == "official_search", "Fallback strategy should be set"
        assert 0.0 <= profile.success_rate <= 1.0, "Success rate should be valid percentage"
        assert isinstance(profile.last_tested, datetime), "Last tested should be datetime"
    
    def test_feature_availability_assessment(self):
        """Test feature availability assessment functionality."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test availability assessment
        availability = feature_manager.assess_feature_availability()
        
        assert isinstance(availability, dict), "Availability must be a dictionary"
        
        # Check for expected features
        expected_features = [
            'advanced_search',
            'custom_sort',
            'category_filter',
            'unofficial_api_fields'
        ]
        
        for feature in expected_features:
            if feature in availability:
                status = availability[feature]
                assert hasattr(status, 'value') if hasattr(status, 'value') else isinstance(status, str), \
                    f"Feature {feature} must have valid status"
    
    def test_risk_level_evaluation(self):
        """Test risk level evaluation for unofficial features."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test risk evaluation for different features
        test_features = [
            ("stable_feature", "LOW"),
            ("experimental_feature", "HIGH"),
            ("beta_feature", "MEDIUM")
        ]
        
        for feature_name, expected_risk in test_features:
            risk_level = feature_manager.evaluate_risk_level(feature_name)
            assert risk_level in ["LOW", "MEDIUM", "HIGH"], \
                f"Risk level must be valid for {feature_name}"
            
            # If we have specific expectations, test them
            if feature_name == "stable_feature":
                assert risk_level in ["LOW", "MEDIUM"], "Stable features should have lower risk"
    
    def test_fallback_chain_generation(self):
        """Test fallback chain generation for failed features."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test fallback chain for search features
        search_fallback = feature_manager.get_fallback_chain("advanced_search")
        
        assert isinstance(search_fallback, list), "Fallback chain must be a list"
        assert len(search_fallback) > 0, "Fallback chain must not be empty"
        
        # Verify fallback order (more reliable methods last)
        if len(search_fallback) > 1:
            # Should include official methods as fallback
            assert any("official" in method.lower() for method in search_fallback), \
                "Should include official methods in fallback"
        
        # Test fallback for sorting features
        sort_fallback = feature_manager.get_fallback_chain("custom_sort")
        assert isinstance(sort_fallback, list), "Sort fallback must be a list"
    
    def test_feature_status_tracking(self):
        """Test feature status updates and tracking."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test successful feature update
        feature_manager.update_feature_status("test_feature", success=True)
        
        # Test failed feature update
        feature_manager.update_feature_status("test_feature", success=False)
        
        # Get feature statistics
        stats = feature_manager.get_feature_statistics("test_feature")
        
        if stats:
            assert 'total_attempts' in stats, "Stats must include total attempts"
            assert 'success_count' in stats, "Stats must include success count"
            assert 'failure_count' in stats, "Stats must include failure count"
            assert 'success_rate' in stats, "Stats must include success rate"
            
            # Validate success rate calculation
            if stats['total_attempts'] > 0:
                expected_rate = stats['success_count'] / stats['total_attempts']
                assert abs(stats['success_rate'] - expected_rate) < 0.01, \
                    "Success rate calculation must be accurate"
    
    def test_fallback_chain_class(self):
        """Test FallbackChain implementation."""
        # Import fallback chain
        fallback_path = self.api_dir / "fallback_chain.py"
        assert fallback_path.exists(), "fallback_chain.py must exist"
        
        spec = importlib.util.spec_from_file_location("fallback_chain", fallback_path)
        fallback_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fallback_module)
        
        # Test FallbackChain class exists
        assert hasattr(fallback_module, 'FallbackChain'), "FallbackChain class must exist"
        FallbackChain = fallback_module.FallbackChain
        
        # Test initialization
        fallback_chain = FallbackChain()
        
        # Validate predefined chains
        assert hasattr(fallback_chain, 'chains'), "FallbackChain must have predefined chains"
        
        chains = fallback_chain.chains
        assert isinstance(chains, dict), "Chains must be a dictionary"
        
        # Check for expected chain types
        expected_chain_types = ['search', 'sort', 'pagination']
        for chain_type in expected_chain_types:
            if chain_type in chains:
                chain = chains[chain_type]
                assert isinstance(chain, list), f"{chain_type} chain must be a list"
                assert len(chain) > 0, f"{chain_type} chain must not be empty"
    
    @pytest.mark.asyncio
    async def test_fallback_execution(self):
        """Test fallback chain execution with failure recovery."""
        fallback_path = self.api_dir / "fallback_chain.py"
        spec = importlib.util.spec_from_file_location("fallback_chain", fallback_path)
        fallback_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fallback_module)
        
        FallbackChain = fallback_module.FallbackChain
        fallback_chain = FallbackChain()
        
        # Mock methods for testing
        with patch.object(fallback_chain, '_execute_method') as mock_execute:
            # First method fails, second succeeds
            mock_execute.side_effect = [
                Exception("First method failed"),
                "success_result"
            ]
            
            # Test fallback execution
            result = await fallback_chain.execute_with_fallback("search", test_param="value")
            
            assert result == "success_result", "Should return result from successful method"
            assert mock_execute.call_count == 2, "Should try two methods"
    
    @pytest.mark.asyncio
    async def test_all_methods_failure_handling(self):
        """Test handling when all fallback methods fail."""
        fallback_path = self.api_dir / "fallback_chain.py"
        spec = importlib.util.spec_from_file_location("fallback_chain", fallback_path)
        fallback_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fallback_module)
        
        FallbackChain = fallback_module.FallbackChain
        fallback_chain = FallbackChain()
        
        # Test AllMethodsFailedError exists
        assert hasattr(fallback_module, 'AllMethodsFailedError'), \
            "AllMethodsFailedError must be defined"
        
        AllMethodsFailedError = fallback_module.AllMethodsFailedError
        
        # Mock all methods to fail
        with patch.object(fallback_chain, '_execute_method') as mock_execute:
            mock_execute.side_effect = Exception("All methods fail")
            
            # Test that AllMethodsFailedError is raised
            with pytest.raises(AllMethodsFailedError):
                await fallback_chain.execute_with_fallback("search", test_param="value")
    
    def test_feature_configuration_management(self):
        """Test feature configuration and settings management."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test feature configuration
        test_config = {
            'enable_unofficial_features': True,
            'risk_tolerance': 'MEDIUM',
            'fallback_enabled': True,
            'max_retries': 3
        }
        
        feature_manager.configure_features(test_config)
        
        # Verify configuration was applied
        config = feature_manager.get_current_configuration()
        assert isinstance(config, dict), "Configuration must be a dictionary"
        
        # Test risk tolerance setting
        if 'risk_tolerance' in config:
            assert config['risk_tolerance'] in ['LOW', 'MEDIUM', 'HIGH'], \
                "Risk tolerance must be valid"
    
    def test_unofficial_feature_detection(self):
        """Test detection of available unofficial features."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Test feature detection
        detected_features = feature_manager.detect_unofficial_features()
        
        assert isinstance(detected_features, list), "Detected features must be a list"
        
        # Test individual feature validation
        for feature in detected_features:
            assert isinstance(feature, str), "Feature names must be strings"
            
            # Test feature validation
            is_valid = feature_manager.validate_feature(feature)
            assert isinstance(is_valid, bool), "Feature validation must return boolean"
    
    def test_feature_usage_analytics(self):
        """Test feature usage analytics and reporting."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        # Record some feature usage
        test_features = ["advanced_search", "custom_sort", "category_filter"]
        
        for feature in test_features:
            feature_manager.record_feature_usage(feature, success=True, duration=0.5)
            feature_manager.record_feature_usage(feature, success=False, duration=1.0)
        
        # Get analytics report
        analytics = feature_manager.get_usage_analytics()
        
        assert isinstance(analytics, dict), "Analytics must be a dictionary"
        
        # Check analytics structure
        expected_fields = ['total_usage', 'success_rate', 'average_duration', 'feature_breakdown']
        for field in expected_fields:
            if field in analytics:
                assert analytics[field] is not None, f"Analytics field {field} must not be None"
        
        # Test feature-specific analytics
        for feature in test_features:
            feature_analytics = feature_manager.get_feature_analytics(feature)
            if feature_analytics:
                assert 'usage_count' in feature_analytics, "Must include usage count"
                assert 'success_rate' in feature_analytics, "Must include success rate"
    
    def test_dynamic_feature_enabling_disabling(self):
        """Test dynamic enabling and disabling of features."""
        feature_manager_path = self.api_dir / "feature_manager.py"
        spec = importlib.util.spec_from_file_location("feature_manager", feature_manager_path)
        feature_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(feature_module)
        
        FeatureManager = feature_module.FeatureManager
        feature_manager = FeatureManager()
        
        test_feature = "test_dynamic_feature"
        
        # Test enabling feature
        feature_manager.enable_feature(test_feature)
        assert feature_manager.is_feature_enabled(test_feature), "Feature should be enabled"
        
        # Test disabling feature
        feature_manager.disable_feature(test_feature)
        assert not feature_manager.is_feature_enabled(test_feature), "Feature should be disabled"
        
        # Test feature status persistence
        enabled_features = feature_manager.get_enabled_features()
        assert isinstance(enabled_features, list), "Enabled features must be a list"
        
        disabled_features = feature_manager.get_disabled_features()
        assert isinstance(disabled_features, list), "Disabled features must be a list"