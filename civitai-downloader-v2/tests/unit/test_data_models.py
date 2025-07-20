#!/usr/bin/env python3
"""
Data model validation tests.
Tests for Pydantic data models with comprehensive validation, serialization, and type checking.
"""

import pytest
from datetime import datetime
from typing import List, Optional
import json
import importlib.util
from pathlib import Path
from unittest.mock import patch


class TestDataModels:
    """Test data model validation and serialization functionality."""
    
    @property
    def models_dir(self) -> Path:
        """Get the data models directory."""
        return Path(__file__).parent.parent.parent / "src" / "data" / "models"
    
    def test_civitai_model_validation(self):
        """Test CivitAI model data validation and structure."""
        # Import CivitAIModel
        model_path = self.models_dir / "civitai_models.py"
        assert model_path.exists(), "civitai_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("civitai_models", model_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test CivitAIModel class exists
        assert hasattr(models_module, 'CivitAIModel'), "CivitAIModel class must exist"
        CivitAIModel = models_module.CivitAIModel
        
        # Test valid model creation
        valid_model_data = {
            'id': 12345,
            'name': 'Anime Checkpoint Model',
            'description': 'High quality anime style checkpoint model',
            'type': 'Checkpoint',
            'nsfw': False,
            'allowNoCredit': True,
            'allowCommercialUse': 'Image',
            'allowDerivatives': True,
            'allowDifferentLicense': False,
            'stats': {
                'downloadCount': 1000,
                'favoriteCount': 150,
                'commentCount': 25,
                'ratingCount': 80,
                'rating': 4.5
            },
            'creator': {
                'username': 'test_creator',
                'image': 'https://civitai.com/user/avatar.jpg'
            },
            'tags': ['anime', 'checkpoint', 'character'],
            'modelVersions': [
                {
                    'id': 54321,
                    'name': 'v1.0',
                    'description': 'Initial release',
                    'baseModel': 'SD 1.5',
                    'downloadUrl': 'https://civitai.com/api/download/models/54321',
                    'files': [
                        {
                            'id': 98765,
                            'url': 'https://civitai.com/api/download/models/54321',
                            'sizeKB': 2048000,
                            'name': 'model.safetensors',
                            'type': 'Model',
                            'format': 'SafeTensor',
                            'pickleScanResult': 'Success',
                            'pickleScanMessage': 'No Pickle imports',
                            'virusScanResult': 'Success',
                            'virusScanMessage': 'No malware detected',
                            'scannedAt': '2024-01-15T10:30:00Z',
                            'hashes': {
                                'AutoV1': 'abc123def456',
                                'AutoV2': 'def456ghi789',
                                'SHA256': '789ghi012jkl',
                                'CRC32': 'jkl012mn',
                                'BLAKE3': 'mno345pqr678'
                            }
                        }
                    ],
                    'images': [
                        {
                            'url': 'https://civitai.com/example1.jpg',
                            'nsfw': 'None',
                            'width': 512,
                            'height': 512,
                            'hash': 'sample_hash_1',
                            'meta': {'prompt': 'anime girl', 'steps': 20}
                        }
                    ],
                    'createdAt': '2024-01-15T10:00:00Z',
                    'updatedAt': '2024-01-15T10:30:00Z',
                    'trainedWords': ['anime', 'character']
                }
            ]
        }
        
        # Test model creation and validation
        model = CivitAIModel(**valid_model_data)
        assert model.id == 12345
        assert model.name == 'Anime Checkpoint Model'
        assert model.type == 'Checkpoint'
        assert model.nsfw == False
        assert len(model.modelVersions) == 1
        assert model.modelVersions[0].id == 54321
        assert len(model.modelVersions[0].files) == 1
        assert model.modelVersions[0].files[0].format == 'SafeTensor'
        
        # Test model serialization
        model_dict = model.model_dump()
        assert isinstance(model_dict, dict)
        assert 'id' in model_dict
        assert 'modelVersions' in model_dict
        
        # Test JSON serialization
        model_json = model.model_dump_json()
        assert isinstance(model_json, (str, bytes))
        parsed = json.loads(model_json)
        assert parsed['id'] == 12345
    
    def test_model_validation_errors(self):
        """Test that invalid model data raises proper validation errors."""
        model_path = self.models_dir / "civitai_models.py"
        spec = importlib.util.spec_from_file_location("civitai_models", model_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        CivitAIModel = models_module.CivitAIModel
        
        # Test missing required fields
        with pytest.raises(Exception, match="Field required"):
            CivitAIModel()  # No data provided
        
        # Test invalid ID type
        with pytest.raises(ValueError):
            CivitAIModel(id="not_an_integer", name="Test Model")
        
        # Test invalid type enum
        with pytest.raises(ValueError):
            CivitAIModel(
                id=123,
                name="Test Model",
                type="InvalidType"  # Should be one of the allowed types
            )
        
        # Test invalid URL format
        with pytest.raises(ValueError):
            CivitAIModel(
                id=123,
                name="Test Model",
                type="Checkpoint",
                modelVersions=[{
                    'id': 456,
                    'downloadUrl': 'not-a-valid-url'
                }]
            )
    
    def test_download_request_model(self):
        """Test download request data model validation."""
        request_path = self.models_dir / "download_models.py"
        assert request_path.exists(), "download_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("download_models", request_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test DownloadRequest class exists
        assert hasattr(models_module, 'DownloadRequest'), "DownloadRequest class must exist"
        DownloadRequest = models_module.DownloadRequest
        
        # Test valid download request
        valid_request = {
            'model_id': 12345,
            'version_id': 54321,
            'file_id': 98765,
            'destination_path': './downloads/models/anime_model.safetensors',
            'priority': 'normal',
            'retry_count': 0,
            'max_retries': 3,
            'chunk_size': 8192,
            'verify_hash': True,
            'expected_hash': 'abc123def456',
            'expected_size': 2048000,
            'download_url': 'https://civitai.com/api/download/models/54321',
            'headers': {'Authorization': 'Bearer token123'},
            'timeout': 300,
            'user_agent': 'CivitAI-Downloader/2.0'
        }
        
        request = DownloadRequest(**valid_request)
        assert request.model_id == 12345
        assert request.priority == 'normal'
        assert request.verify_hash == True
        assert request.chunk_size == 8192
        
        # Test serialization
        request_dict = request.model_dump()
        assert 'model_id' in request_dict
        assert 'download_url' in request_dict
    
    def test_search_parameters_model(self):
        """Test search parameters data model validation."""
        search_path = self.models_dir / "search_models.py"
        assert search_path.exists(), "search_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("search_models", search_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test SearchParameters class exists
        assert hasattr(models_module, 'SearchParameters'), "SearchParameters class must exist"
        SearchParameters = models_module.SearchParameters
        
        # Test valid search parameters
        valid_search = {
            'query': 'anime character',
            'limit': 50,
            'page': 1,
            'types': ['Checkpoint', 'LORA'],
            'sort': 'Most Downloaded',
            'period': 'Month',
            'rating': 4,
            'nsfw': False,
            'commercial_use': True,
            'base_models': ['SD 1.5', 'SDXL 1.0'],
            'tags': ['anime', 'character'],
            'username': 'favorite_creator',
            'favorites': False
        }
        
        search = SearchParameters(**valid_search)
        assert search.query == 'anime character'
        assert search.limit == 50
        assert len(search.types) == 2
        assert 'Checkpoint' in search.types
        assert search.nsfw == False
        
        # Test default values
        minimal_search = SearchParameters()
        assert minimal_search.limit == 20  # Should have sensible default
        assert minimal_search.page == 1
        assert minimal_search.nsfw == False
    
    def test_api_response_models(self):
        """Test API response data model validation."""
        response_path = self.models_dir / "api_models.py"
        assert response_path.exists(), "api_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("api_models", response_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test APIResponse class exists
        assert hasattr(models_module, 'APIResponse'), "APIResponse class must exist"
        APIResponse = models_module.APIResponse
        
        # Test successful API response
        success_response = {
            'status_code': 200,
            'success': True,
            'data': {'models': [{'id': 123, 'name': 'Test Model'}]},
            'message': 'Request successful',
            'request_id': 'req_123456789',
            'timestamp': '2024-01-15T10:30:00Z',
            'rate_limit': {
                'remaining': 95,
                'reset_at': '2024-01-15T11:00:00Z',
                'limit': 100
            }
        }
        
        response = APIResponse(**success_response)
        assert response.status_code == 200
        assert response.success == True
        assert 'models' in response.data
        assert response.rate_limit.remaining == 95
        
        # Test error API response
        error_response = {
            'status_code': 404,
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Model not found',
                'details': {'model_id': 99999}
            },
            'request_id': 'req_987654321',
            'timestamp': '2024-01-15T10:35:00Z'
        }
        
        error_resp = APIResponse(**error_response)
        assert error_resp.status_code == 404
        assert error_resp.success == False
        assert error_resp.error.code == 'NOT_FOUND'
    
    def test_model_file_validation(self):
        """Test model file data validation with security checks."""
        file_path = self.models_dir / "file_models.py"
        assert file_path.exists(), "file_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("file_models", file_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test ModelFile class exists
        assert hasattr(models_module, 'ModelFile'), "ModelFile class must exist"
        ModelFile = models_module.ModelFile
        
        # Test valid model file
        valid_file = {
            'id': 98765,
            'url': 'https://civitai.com/api/download/models/54321',
            'sizeKB': 2048000,
            'name': 'anime_model_v1.safetensors',
            'type': 'Model',
            'format': 'SafeTensor',
            'pickleScanResult': 'Success',
            'pickleScanMessage': 'No Pickle imports',
            'virusScanResult': 'Success',
            'virusScanMessage': 'No malware detected',
            'scannedAt': '2024-01-15T10:30:00Z',
            'hashes': {
                'AutoV1': 'abc123def456ghi789',
                'AutoV2': 'def456ghi789jkl012',
                'SHA256': '789abc012def345678901234567890abcdef1234567890123456789012345678',
                'CRC32': 'AB123456',
                'BLAKE3': 'mno345pqr678stu901vwx234yzab567'
            },
            'downloadUrl': 'https://civitai.com/api/download/models/54321?type=Model&format=SafeTensor',
            'primary': True
        }
        
        file_model = ModelFile(**valid_file)
        assert file_model.id == 98765
        assert file_model.format == 'SafeTensor'
        assert file_model.pickleScanResult == 'Success'
        assert file_model.primary == True
        assert file_model.hashes.SHA256 is not None
        
        # Test security validation
        assert file_model.is_safe_format()  # SafeTensor should be considered safe
        assert file_model.passed_security_scans()  # Both scans passed
        
        # Test unsafe file (Pickle format with scan issues)
        unsafe_file = {
            'id': 98766,
            'url': 'https://civitai.com/api/download/models/54322',
            'sizeKB': 2048000,
            'name': 'unsafe_model.ckpt',
            'type': 'Model',
            'format': 'PickleTensor',
            'pickleScanResult': 'Danger',
            'pickleScanMessage': 'Unsafe pickle imports detected',
            'virusScanResult': 'Success',
            'virusScanMessage': 'No malware detected',
            'scannedAt': '2024-01-15T10:30:00Z',
            'hashes': {'SHA256': '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'},
            'downloadUrl': 'https://civitai.com/api/download/models/54322',
            'primary': True
        }
        
        unsafe_model = ModelFile(**unsafe_file)
        assert not unsafe_model.is_safe_format()  # Pickle format should be flagged
        assert not unsafe_model.passed_security_scans()  # Pickle scan failed
    
    def test_configuration_models(self):
        """Test configuration data models for type safety."""
        config_path = self.models_dir / "config_models.py"
        assert config_path.exists(), "config_models.py must exist"
        
        spec = importlib.util.spec_from_file_location("config_models", config_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        # Test AppConfig class exists
        assert hasattr(models_module, 'AppConfig'), "AppConfig class must exist"
        AppConfig = models_module.AppConfig
        
        # Test valid configuration
        valid_config = {
            'api': {
                'api_key': 'test_key_123',
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30,
                'verify_ssl': True,
                'rate_limit_requests_per_minute': 60
            }
        }
        
        config = AppConfig(**valid_config)
        assert config.api.api_key.get_secret_value() == 'test_key_123'
        assert config.api.timeout == 30
        assert config.api.verify_ssl == True
        
        # Test validation constraints  
        with pytest.raises(Exception):
            AppConfig(
                api={'api_key': 'short', 'timeout': -5}  # Invalid short key and negative timeout
            )
    
    def test_model_serialization_performance(self):
        """Test that model serialization is efficient for large datasets."""
        model_path = self.models_dir / "civitai_models.py"
        spec = importlib.util.spec_from_file_location("civitai_models", model_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)
        
        CivitAIModel = models_module.CivitAIModel
        
        # Create a model with multiple versions and files
        large_model_data = {
            'id': 12345,
            'name': 'Large Model',
            'type': 'Checkpoint',
            'modelVersions': [
                {
                    'id': 54321 + i,
                    'name': f'v1.{i}',
                    'baseModel': 'SD 1.5',
                    'downloadUrl': f'https://civitai.com/api/download/models/{54321 + i}',
                    'files': [
                        {
                            'id': 98765 + j,
                            'url': f'https://civitai.com/api/download/models/{54321 + i}/file/{j}',
                            'sizeKB': 2048000,
                            'name': f'model_v{i}_f{j}.safetensors',
                            'type': 'Model',
                            'format': 'SafeTensor',
                            'pickleScanResult': 'Success',
                            'virusScanResult': 'Success',
                            'hashes': {'SHA256': f'hash_{i}_{j}'}
                        }
                        for j in range(3)  # 3 files per version
                    ],
                    'createdAt': '2024-01-15T10:00:00Z'
                }
                for i in range(5)  # 5 versions
            ]
        }
        
        # Test creation and serialization performance
        import time
        start_time = time.time()
        
        model = CivitAIModel(**large_model_data)
        creation_time = time.time() - start_time
        
        start_time = time.time()
        model_json = model.model_dump_json()
        serialization_time = time.time() - start_time
        
        start_time = time.time()
        model_dict = model.model_dump()
        dict_time = time.time() - start_time
        
        # Performance assertions (should complete quickly)
        assert creation_time < 1.0, "Model creation should be fast"
        assert serialization_time < 1.0, "JSON serialization should be fast"
        assert dict_time < 1.0, "Dict conversion should be fast"
        
        # Verify data integrity
        assert len(model.modelVersions) == 5
        assert len(model.modelVersions[0].files) == 3
        assert isinstance(model_json, str)
        assert len(model_json) > 1000  # Should be substantial JSON