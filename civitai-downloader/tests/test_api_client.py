"""Tests for CivitAI API client."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from src.api_client import CivitAIAPIClient, RateLimiter
from src.interfaces import ModelType, SearchParams, SortOrder
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


@pytest.fixture
def mock_model_response():
    """Mock model API response."""
    return {
        "id": 123456,
        "name": "Test Model",
        "type": "LORA",
        "description": "A test model",
        "tags": ["anime", "style"],
        "creator": {"username": "testuser"},
        "stats": {
            "downloadCount": 1000,
            "favoriteCount": 100,
            "commentCount": 50,
            "ratingCount": 20,
            "rating": 4.5
        },
        "nsfw": False,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-02T00:00:00Z"
    }


@pytest.fixture
def mock_version_response():
    """Mock version API response."""
    return {
        "id": 789,
        "name": "v1.0",
        "description": "Initial version",
        "baseModel": "SD 1.5",
        "trainedWords": ["test", "style"],
        "files": [
            {
                "id": 111,
                "name": "model.safetensors",
                "sizeKB": 144320,
                "type": "Model",
                "metadata": {"fp": "fp16"},
                "hashes": {"SHA256": "abc123"},
                "downloadUrl": "https://civitai.com/api/download/models/789"
            }
        ],
        "images": [
            {
                "id": 222,
                "url": "https://example.com/preview.jpg",
                "width": 512,
                "height": 768,
                "hash": "def456",
                "nsfw": False,
                "meta": {"prompt": "test prompt"}
            }
        ],
        "downloadUrl": "https://civitai.com/api/download/models/789",
        "createdAt": "2024-01-01T00:00:00Z"
    }


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiter enforces delays."""
        limiter = RateLimiter(calls_per_minute=120)  # 2 calls per second
        
        start_time = asyncio.get_event_loop().time()
        await limiter.wait()
        await limiter.wait()
        await limiter.wait()
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 1 second for 3 calls at 2/sec
        assert end_time - start_time >= 1.0


class TestCivitAIAPIClient:
    """Test CivitAI API client."""
    
    
    @pytest.mark.asyncio
    async def test_normalize_model_type(self, mock_config):
        """Test model type normalization."""
        client = CivitAIAPIClient(mock_config)
        
        # LyCORIS should be converted to LoCon
        assert client._normalize_model_type("LyCORIS") == "LoCon"
        assert client._normalize_model_type("LYCORIS") == "LoCon"
        assert client._normalize_model_type("lycoris") == "LoCon"
        
        # Others should pass through
        assert client._normalize_model_type("LORA") == "LORA"
        assert client._normalize_model_type("Checkpoint") == "Checkpoint"
    
    
    
    
    @pytest.mark.asyncio
    async def test_retry_on_error(self, mock_config):
        """Test retry logic on errors."""
        client = CivitAIAPIClient(mock_config)
        
        # Mock the session to simulate HTTP errors
        call_count = 0
        
        async def mock_context_manager(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Simulate server error
                raise ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500
                )
            else:
                # Success on third try
                mock_response = AsyncMock()
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value={"items": [], "metadata": {}})
                return mock_response
        
        # Mock the session and context manager
        client.session = AsyncMock()
        context_manager = AsyncMock()
        context_manager.__aenter__ = mock_context_manager
        context_manager.__aexit__ = AsyncMock(return_value=None)
        client.session.request = MagicMock(return_value=context_manager)
        
        # Should succeed after retries
        result = await client._make_request('GET', '/models')
        assert call_count == 3
        assert result == {"items": [], "metadata": {}}
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, mock_config):
        """Test retry on rate limit."""
        client = CivitAIAPIClient(mock_config)
        
        # Mock rate limit response
        call_count = 0
        
        async def mock_context_manager(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Simulate rate limit
                raise ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429
                )
            else:
                # Success on second try
                mock_response = AsyncMock()
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value={"success": True})
                return mock_response
        
        # Mock the session and context manager
        client.session = AsyncMock()
        context_manager = AsyncMock()
        context_manager.__aenter__ = mock_context_manager
        context_manager.__aexit__ = AsyncMock(return_value=None)
        client.session.request = MagicMock(return_value=context_manager)
        
        # Should succeed after rate limit retry
        result = await client._make_request('GET', '/test')
        assert call_count == 2
        assert result == {"success": True}