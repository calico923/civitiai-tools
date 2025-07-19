#!/usr/bin/env python3
"""
Configuration management system tests.
Tests for environment variable loading, YAML config parsing, and validation.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open
import importlib.util


class TestConfigManagement:
    """Test configuration management system functionality."""
    
    @property
    def config_dir(self) -> Path:
        """Get the configuration management directory."""
        return Path(__file__).parent.parent.parent / "src" / "core" / "config"
    
    def test_env_vars_override_yaml_config(self):
        """Test that environment variables override YAML configuration values."""
        # Import SystemConfig
        config_path = self.config_dir / "system_config.py"
        assert config_path.exists(), "system_config.py must exist"
        
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        # Test SystemConfig class exists
        assert hasattr(config_module, 'SystemConfig'), "SystemConfig class must exist"
        SystemConfig = config_module.SystemConfig
        
        # Create temporary YAML config
        yaml_content = {
            'api': {
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30,
                'api_key': 'yaml_key'
            },
            'download': {
                'concurrent_downloads': 3,
                'chunk_size': 8192
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file_path = f.name
        
        try:
            # Test without environment variable override
            with patch.dict(os.environ, {}, clear=True):
                config = SystemConfig(config_file=yaml_file_path)
                assert config.get('api.api_key') == 'yaml_key'
                assert config.get('api.timeout') == 30
                assert config.get('download.concurrent_downloads') == 3
            
            # Test with environment variable override
            with patch.dict(os.environ, {
                'CIVITAI_API_KEY': 'env_override_key',
                'CIVITAI_TIMEOUT': '60',
                'CIVITAI_CONCURRENT_DOWNLOADS': '5'
            }):
                config = SystemConfig(config_file=yaml_file_path)
                assert config.get('api.api_key') == 'env_override_key'
                assert config.get('api.timeout') == 60
                assert config.get('download.concurrent_downloads') == 5
        finally:
            os.unlink(yaml_file_path)
    
    def test_config_validation_raises_error_on_missing_required_field(self):
        """Test that config validation raises error when required fields are missing."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test with missing required API key
        incomplete_config = {
            'api': {
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30
                # Missing 'api_key'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_config, f)
            yaml_file_path = f.name
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match="API key is required"):
                    config = SystemConfig(config_file=yaml_file_path)
                    config.validate()
        finally:
            os.unlink(yaml_file_path)
    
    def test_config_default_values_fallback(self):
        """Test that configuration provides sensible default values."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test with minimal config (only required fields)
        minimal_config = {
            'api': {
                'api_key': 'test_key'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(minimal_config, f)
            yaml_file_path = f.name
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                config = SystemConfig(config_file=yaml_file_path)
                
                # Test default values are provided
                assert config.get('api.base_url') == 'https://civitai.com/api/v1'
                assert config.get('api.timeout') == 30
                assert config.get('download.concurrent_downloads') == 3
                assert config.get('download.chunk_size') == 8192
                assert config.get('logging.level') == 'INFO'
                assert config.get('security.verify_ssl') == True
        finally:
            os.unlink(yaml_file_path)
    
    def test_config_nested_key_access(self):
        """Test that nested configuration keys can be accessed using dot notation."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        nested_config = {
            'api': {
                'civitai': {
                    'base_url': 'https://civitai.com/api/v1',
                    'rate_limit': {
                        'requests_per_minute': 60,
                        'burst_size': 10
                    }
                }
            },
            'download': {
                'paths': {
                    'models': './downloads/models',
                    'temp': './downloads/temp'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(nested_config, f)
            yaml_file_path = f.name
        
        try:
            config = SystemConfig(config_file=yaml_file_path)
            
            # Test nested key access
            assert config.get('api.civitai.base_url') == 'https://civitai.com/api/v1'
            assert config.get('api.civitai.rate_limit.requests_per_minute') == 60
            assert config.get('api.civitai.rate_limit.burst_size') == 10
            assert config.get('download.paths.models') == './downloads/models'
            assert config.get('download.paths.temp') == './downloads/temp'
            
            # Test non-existent key returns None or default
            assert config.get('non.existent.key') is None
            assert config.get('non.existent.key', 'default') == 'default'
        finally:
            os.unlink(yaml_file_path)
    
    def test_config_type_conversion(self):
        """Test that configuration values are properly type-converted."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test environment variables with different types
        with patch.dict(os.environ, {
            'CIVITAI_API_KEY': 'test_key',
            'CIVITAI_TIMEOUT': '45',  # String that should be converted to int
            'CIVITAI_VERIFY_SSL': 'false',  # String that should be converted to bool
            'CIVITAI_CHUNK_SIZE': '16384',  # String that should be converted to int
            'CIVITAI_MAX_RETRIES': '3.5'  # String that should be converted to float
        }):
            config = SystemConfig()
            
            # Test type conversions
            assert isinstance(config.get('api.timeout'), int)
            assert config.get('api.timeout') == 45
            
            assert isinstance(config.get('security.verify_ssl'), bool)
            assert config.get('security.verify_ssl') == False
            
            assert isinstance(config.get('download.chunk_size'), int)
            assert config.get('download.chunk_size') == 16384
            
            # Test float conversion if supported
            if config.get('api.max_retries') is not None:
                assert isinstance(config.get('api.max_retries'), float)
                assert config.get('api.max_retries') == 3.5
    
    def test_config_validation_schema(self):
        """Test that configuration validation uses a proper schema."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test invalid configuration values
        invalid_configs = [
            # Negative timeout
            {
                'api': {
                    'api_key': 'test_key',
                    'timeout': -10
                }
            },
            # Invalid URL format
            {
                'api': {
                    'api_key': 'test_key',
                    'base_url': 'not-a-valid-url'
                }
            },
            # Invalid concurrent downloads (too high)
            {
                'api': {
                    'api_key': 'test_key'
                },
                'download': {
                    'concurrent_downloads': 100
                }
            }
        ]
        
        for invalid_config in invalid_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(invalid_config, f)
                yaml_file_path = f.name
            
            try:
                with pytest.raises((ValueError, TypeError)):
                    config = SystemConfig(config_file=yaml_file_path)
                    config.validate()
            finally:
                os.unlink(yaml_file_path)
    
    def test_config_environment_variable_mapping(self):
        """Test that environment variables are properly mapped to config keys."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test standard environment variable mappings
        env_vars = {
            'CIVITAI_API_KEY': 'test_key_123',
            'CIVITAI_BASE_URL': 'https://custom.civitai.com/api/v1',
            'CIVITAI_TIMEOUT': '120',
            'CIVITAI_CONCURRENT_DOWNLOADS': '7',
            'CIVITAI_CHUNK_SIZE': '32768',
            'CIVITAI_VERIFY_SSL': 'true',
            'CIVITAI_LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SystemConfig()
            
            # Verify environment variables are mapped correctly
            assert config.get('api.api_key') == 'test_key_123'
            assert config.get('api.base_url') == 'https://custom.civitai.com/api/v1'
            assert config.get('api.timeout') == 120
            assert config.get('download.concurrent_downloads') == 7
            assert config.get('download.chunk_size') == 32768
            assert config.get('security.verify_ssl') == True
            assert config.get('logging.level') == 'DEBUG'
    
    def test_config_file_not_found_handling(self):
        """Test that missing config files are handled gracefully."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        # Test with non-existent config file
        non_existent_file = '/path/that/does/not/exist/config.yaml'
        
        with patch.dict(os.environ, {'CIVITAI_API_KEY': 'test_key'}):
            # Should not raise an exception, should use defaults + env vars
            config = SystemConfig(config_file=non_existent_file)
            assert config.get('api.api_key') == 'test_key'
            assert config.get('api.base_url') == 'https://civitai.com/api/v1'  # Default value
    
    def test_config_serialization(self):
        """Test that configuration can be serialized for debugging/logging."""
        config_path = self.config_dir / "system_config.py"
        spec = importlib.util.spec_from_file_location("system_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        SystemConfig = config_module.SystemConfig
        
        test_config = {
            'api': {
                'api_key': 'secret_key_123',
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30
            },
            'download': {
                'concurrent_downloads': 3
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            yaml_file_path = f.name
        
        try:
            config = SystemConfig(config_file=yaml_file_path)
            
            # Test serialization (should mask sensitive data)
            serialized = config.to_dict()
            assert isinstance(serialized, dict)
            assert 'api' in serialized
            
            # Test that sensitive data is masked
            serialized_safe = config.to_dict(mask_sensitive=True)
            assert 'secret_key_123' not in str(serialized_safe)
            assert '***' in serialized_safe['api']['api_key'] or 'REDACTED' in serialized_safe['api']['api_key']
            
            # Test that non-sensitive data is preserved
            assert serialized_safe['api']['base_url'] == 'https://civitai.com/api/v1'
            assert serialized_safe['api']['timeout'] == 30
        finally:
            os.unlink(yaml_file_path)