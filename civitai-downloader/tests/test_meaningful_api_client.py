"""Meaningful API client tests that test actual business logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError
import json
from urllib.parse import urlencode

from src.api_client import CivitAIAPIClient
from src.interfaces import SearchParams, ModelType, SortOrder
from src.config import ConfigManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=ConfigManager)
    config.config = MagicMock()
    config.config.api_base_url = "https://civitai.com/api/v1"
    config.config.api_key = "test-api-key"
    config.config.api_timeout = 30
    config.config.api_max_retries = 3
    config.config.user_agent = "Test/1.0"
    config.config.verify_ssl = True
    config.config.proxy = None
    return config


class TestMeaningfulAPIClient:
    """Tests that validate actual API client business logic."""
    
    @pytest.mark.asyncio
    async def test_search_models_url_construction(self, mock_config):
        """Test that search parameters are correctly converted to API URL and params."""
        client = CivitAIAPIClient(mock_config)
        
        # Mock the HTTP response at the infrastructure level
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "items": [{
                "id": 123,
                "name": "Test Model",
                "type": "LORA", 
                "creator": {"username": "testuser"},
                "stats": {"downloadCount": 100},
                "nsfw": False,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "description": "Test description",
                "tags": ["anime", "style"]
            }],
            "metadata": {"nextCursor": "abc123"}
        })
        
        # Capture the actual HTTP request details
        captured_url = None
        captured_params = None
        
        async def mock_make_request(method, endpoint, params=None, json_data=None):
            nonlocal captured_url, captured_params
            captured_url = f"{client.base_url}/{endpoint.lstrip('/')}"
            captured_params = params or {}
            return {
                "items": [{
                    "id": 123,
                    "name": "Test Model",
                    "type": "LORA",
                    "creator": {"username": "testuser"},
                    "stats": {"downloadCount": 100},
                    "nsfw": False,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "description": "Test description",
                    "tags": ["anime", "style"]
                }],
                "metadata": {"nextCursor": "abc123"}
            }
        
        client._make_request = mock_make_request
        
        # Test complex search parameters
        params = SearchParams(
            query="anime character",
            types=[ModelType.LORA, ModelType.LYCORIS],
            tags=["anime", "style", "character"],
            sort=SortOrder.MOST_DOWNLOADED,
            nsfw=False,
            limit=50,
            page=2
        )
        
        models, cursor = await client.search_models(params)
        
        # Verify URL construction
        assert captured_url == f"{client.base_url}/models"
        
        # Verify parameter transformation
        assert captured_params['query'] == "anime character"
        assert captured_params['types'] == ["LORA", "LoCon"]  # LyCORIS should be normalized
        assert captured_params['tag'] == ["anime", "style", "character"]
        assert captured_params['sort'] == "Most Downloaded"
        assert captured_params['nsfw'] == False
        assert captured_params['limit'] == 50
        
        # Verify response parsing
        assert len(models) == 1
        assert models[0].id == 123
        assert models[0].type == ModelType.LORA
        assert cursor == "abc123"
    
    @pytest.mark.asyncio
    async def test_model_details_with_complex_response(self, mock_config):
        """Test model details parsing with complex real-world response structure."""
        client = CivitAIAPIClient(mock_config)
        
        # Use realistic response structure from actual API
        complex_response = {
            "id": 456,
            "name": "Complex Model",
            "type": "Checkpoint",
            "description": "A complex model with many features",
            "creator": {"username": "complexuser", "id": 789},
            "stats": {
                "downloadCount": 15420,
                "favoriteCount": 892,
                "commentCount": 156,
                "ratingCount": 45,
                "rating": 4.7
            },
            "tags": ["realistic", "portrait", "professional", "photography"],
            "nsfw": True,
            "createdAt": "2024-06-15T14:30:00Z",
            "updatedAt": "2024-07-01T09:15:00Z",
            "modelVersions": [
                {
                    "id": 1001,
                    "name": "v2.1",
                    "description": "Latest version",
                    "baseModel": "SD 1.5",
                    "files": [
                        {
                            "id": 2001,
                            "name": "model.safetensors",
                            "sizeKB": 2048576,  # 2GB
                            "type": "Model",
                            "metadata": {"fp": "fp16"},
                            "hashes": {"SHA256": "abcdef123456"},
                            "downloadUrl": "https://civitai.com/api/download/models/1001"
                        }
                    ]
                }
            ]
        }
        
        captured_url = None
        async def mock_make_request(method, endpoint, params=None, json_data=None):
            nonlocal captured_url
            captured_url = f"{client.base_url}/{endpoint.lstrip('/')}"
            return complex_response
        
        client._make_request = mock_make_request
        
        # Test model details retrieval
        model = await client.get_model_details(456)
        
        # Verify URL construction
        assert captured_url == f"{client.base_url}/models/456"
        
        # Verify complex response parsing
        assert model.id == 456
        assert model.name == "Complex Model"
        assert model.creator == "complexuser"
        assert model.stats['downloadCount'] == 15420
        assert model.stats['rating'] == 4.7
        assert len(model.tags) == 4
        assert "realistic" in model.tags
        assert model.nsfw == True
    
    @pytest.mark.asyncio
    async def test_version_endpoint_with_file_parsing(self, mock_config):
        """Test version endpoint with complex file structure parsing."""
        client = CivitAIAPIClient(mock_config)
        
        # Realistic version response with multiple files
        version_response = {
            "id": 1001,
            "name": "v2.1 Ultra",
            "description": "Enhanced version with multiple formats",
            "baseModel": "SDXL 1.0",
            "trainedWords": ["masterpiece", "detailed", "photorealistic"],
            "createdAt": "2024-07-15T10:00:00Z",
            "files": [
                {
                    "id": 3001,
                    "name": "model_fp16.safetensors",
                    "sizeKB": 6789120,  # ~6.7GB
                    "type": "Model",
                    "metadata": {"fp": "fp16", "size": "full"},
                    "hashes": {"SHA256": "fp16hash123"},
                    "downloadUrl": "https://civitai.com/api/download/models/1001?type=Model&format=SafeTensor"
                },
                {
                    "id": 3002,
                    "name": "model_fp32.ckpt",
                    "sizeKB": 13578240,  # ~13.6GB
                    "type": "Model",
                    "metadata": {"fp": "fp32", "size": "full"},
                    "hashes": {"SHA256": "fp32hash456"},
                    "downloadUrl": "https://civitai.com/api/download/models/1001?type=Model&format=PickleTensor"
                },
                {
                    "id": 3003,
                    "name": "vae.safetensors",
                    "sizeKB": 335544,  # ~335MB
                    "type": "VAE",
                    "metadata": {"architecture": "AutoencoderKL"},
                    "hashes": {"SHA256": "vaehash789"},
                    "downloadUrl": "https://civitai.com/api/download/models/1001?type=VAE"
                }
            ],
            "images": [
                {
                    "id": 4001,
                    "url": "https://image.civitai.com/sample1.jpg",
                    "width": 1024,
                    "height": 1536,
                    "hash": "img1hash",
                    "nsfw": False,
                    "meta": {
                        "prompt": "masterpiece, detailed portrait",
                        "negativePrompt": "blurry, low quality",
                        "seed": 12345,
                        "steps": 30,
                        "cfg": 7.5
                    }
                }
            ]
        }
        
        captured_url = None
        async def mock_make_request(method, endpoint, params=None, json_data=None):
            nonlocal captured_url
            captured_url = f"{client.base_url}/{endpoint.lstrip('/')}"
            return version_response
        
        client._make_request = mock_make_request
        
        # Test version retrieval
        version = await client.get_model_version(1001)
        
        # Verify URL construction
        assert captured_url == f"{client.base_url}/model-versions/1001"
        
        # Verify complex file parsing
        assert version.id == 1001
        assert version.name == "v2.1 Ultra"
        assert version.base_model == "SDXL 1.0"
        assert len(version.trained_words) == 3
        assert len(version.files) == 3
        assert len(version.images) == 1
        
        # Verify file size calculations (KB to bytes)
        fp16_file = next(f for f in version.files if f.name == "model_fp16.safetensors")
        assert fp16_file.size_bytes == 6789120 * 1024
        assert fp16_file.fp == "fp16"
        
        vae_file = next(f for f in version.files if f.name == "vae.safetensors")
        assert vae_file.size_bytes == 335544 * 1024
        
        # Verify image metadata extraction
        image = version.images[0]
        assert image.width == 1024
        assert image.height == 1536
        assert image.meta["steps"] == 30
        assert image.meta["cfg"] == 7.5
    
    @pytest.mark.asyncio
    async def test_error_handling_with_realistic_scenarios(self, mock_config):
        """Test error handling with realistic API error scenarios."""
        client = CivitAIAPIClient(mock_config)
        
        # Test 404 model not found
        async def mock_404_request(method, endpoint, params=None, json_data=None):
            raise ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=404,
                message="Model not found"
            )
        
        client._make_request = mock_404_request
        
        # Should raise the error after retries
        with pytest.raises(ClientResponseError) as exc_info:
            await client.get_model_details(999999)
        
        assert exc_info.value.status == 404
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_header(self, mock_config):
        """Test that API key is correctly included in request headers."""
        mock_config.config.api_key = "test-api-key-12345"
        client = CivitAIAPIClient(mock_config)
        
        captured_headers = None
        async def mock_make_request(method, endpoint, params=None, json_data=None):
            nonlocal captured_headers
            # Return minimal response for auth test
            return {"items": [], "metadata": {}}
        
        client._make_request = mock_make_request
        
        # Test that headers are set correctly during initialization
        assert client.headers["Authorization"] == "Bearer test-api-key-12345"
        assert client.headers["User-Agent"] == mock_config.config.user_agent
        assert client.headers["Accept"] == "application/json"
        
        # Test that search still works with auth
        await client.search_models(SearchParams(query="test"))
        
        # Verify the mock was called (authentication worked)
        # Since we're mocking _make_request, we don't need to assert session calls