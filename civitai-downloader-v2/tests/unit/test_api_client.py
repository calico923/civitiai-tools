#!/usr/bin/env python3
"""
API Client tests.
Tests for CivitaiAPIClient, rate limiting, error handling, and authentication.
"""

import pytest
import asyncio
import httpx
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import importlib.util
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestAPIClient:
    """Test CivitAI API client functionality."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_civitai_api_client_initialization(self):
        """Test CivitAI API client proper initialization."""
        # Import API client
        client_path = self.api_dir / "client.py"
        assert client_path.exists(), "client.py must exist"
        
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        # Test CivitaiAPIClient class exists
        assert hasattr(client_module, 'CivitaiAPIClient'), "CivitaiAPIClient class must exist"
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        # Test initialization
        api_key = "test_api_key"
        client = CivitaiAPIClient(api_key=api_key)
        
        # Validate client properties
        assert hasattr(client, 'api_key'), "Client must have api_key property"
        assert hasattr(client, 'base_url'), "Client must have base_url property"
        assert hasattr(client, 'timeout'), "Client must have timeout property"
        assert hasattr(client, 'rate_limiter'), "Client must have rate_limiter"
        
        # Test default configuration
        assert client.base_url == "https://civitai.com/api/v1", "Default base URL should be correct"
        assert client.timeout > 0, "Timeout should be positive"
    
    def test_basic_http_client_functionality(self):
        """Test basic HTTP client functionality with proper headers."""
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        # Test with API key
        api_key = "test_api_key_123"
        client = CivitaiAPIClient(api_key=api_key)
        
        # Test headers configuration
        headers = client.get_headers()
        assert isinstance(headers, dict), "Headers must be a dictionary"
        assert 'Authorization' in headers, "Authorization header must be present"
        assert f'Bearer {api_key}' in headers['Authorization'], "Authorization header must contain Bearer token"
        assert 'User-Agent' in headers, "User-Agent header must be present"
        assert 'Accept' in headers, "Accept header must be present"
        assert headers['Accept'] == 'application/json', "Accept header should be application/json"
    
    @pytest.mark.asyncio
    async def test_api_request_with_rate_limiting(self):
        """Test API request with rate limiting enforcement."""
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        client = CivitaiAPIClient(api_key="test_key")
        
        # Mock HTTP client
        with patch.object(client, '_http_client') as mock_http:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": [], "metadata": {}}
            mock_response.headers = {}
            mock_http.get = AsyncMock(return_value=mock_response)
            
            # Test rate limiting is called
            with patch.object(client.rate_limiter, 'wait') as mock_wait:
                mock_wait.return_value = None
                
                result = await client.get_models({"limit": 10})
                
                # Verify rate limiter was called
                mock_wait.assert_called_once()
                
                # Verify HTTP request was made
                mock_http.get.assert_called_once()
                
                # Verify response structure
                assert isinstance(result, dict), "Response must be a dictionary"
                assert 'items' in result, "Response must contain items"
                assert 'metadata' in result, "Response must contain metadata"
    
    @pytest.mark.asyncio
    async def test_error_handling_for_api_failures(self):
        """Test comprehensive error handling for various API failure scenarios."""
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        client = CivitaiAPIClient(api_key="test_key")
        
        # Test 404 Not Found error
        with patch.object(client, '_http_client') as mock_http:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_http.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception) as exc_info:
                await client.get_models({"limit": 10})
            
            # Verify error contains useful information
            error = exc_info.value
            assert "404" in str(error) or "Not Found" in str(error), "Error should contain status information"
        
        # Test 429 Rate Limited error
        with patch.object(client, '_http_client') as mock_http:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate Limited"
            mock_response.headers = {'Retry-After': '60'}
            mock_http.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception) as exc_info:
                await client.get_models({"limit": 10})
            
            error = exc_info.value
            assert "429" in str(error) or "Rate" in str(error), "Error should contain rate limit information"
        
        # Test network timeout error
        with patch.object(client, '_http_client') as mock_http:
            mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            
            with pytest.raises(Exception) as exc_info:
                await client.get_models({"limit": 10})
            
            error = exc_info.value
            assert "timeout" in str(error).lower(), "Error should contain timeout information"
        
        # Test connection error
        with patch.object(client, '_http_client') as mock_http:
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            with pytest.raises(Exception) as exc_info:
                await client.get_models({"limit": 10})
            
            error = exc_info.value
            assert "connect" in str(error).lower(), "Error should contain connection information"
    
    def test_rate_limiter_configuration(self):
        """Test rate limiter proper configuration and behavior."""
        # Import rate limiter
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        assert rate_limiter_path.exists(), "rate_limiter.py must exist"
        
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        # Test RateLimiter class exists
        assert hasattr(rate_limiter_module, 'RateLimiter'), "RateLimiter class must exist"
        RateLimiter = rate_limiter_module.RateLimiter
        
        # Test initialization
        rate_limiter = RateLimiter(requests_per_second=0.5)
        
        # Validate rate limiter properties
        assert hasattr(rate_limiter, 'requests_per_second'), "Rate limiter must have requests_per_second"
        assert hasattr(rate_limiter, 'last_request_time'), "Rate limiter must track last request time"
        assert rate_limiter.requests_per_second == 0.5, "Rate should be set correctly"
        
        # Test minimum interval calculation
        expected_interval = 1.0 / 0.5  # 2 seconds
        assert rate_limiter.min_interval == expected_interval, "Minimum interval should be calculated correctly"
    
    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delays(self):
        """Test that rate limiter enforces proper delays between requests."""
        rate_limiter_path = self.api_dir / "rate_limiter.py"
        spec = importlib.util.spec_from_file_location("rate_limiter", rate_limiter_path)
        rate_limiter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rate_limiter_module)
        
        RateLimiter = rate_limiter_module.RateLimiter
        
        # Create rate limiter with 1 request per second
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        # Test first request (should not wait)
        start_time = datetime.now()
        await rate_limiter.wait()
        first_wait_time = (datetime.now() - start_time).total_seconds()
        
        # First request should have minimal wait time
        assert first_wait_time < 0.1, "First request should not wait significantly"
        
        # Test second request (should wait)
        start_time = datetime.now()
        await rate_limiter.wait()
        second_wait_time = (datetime.now() - start_time).total_seconds()
        
        # Second request should wait approximately 1 second
        assert 0.5 <= second_wait_time <= 1.5, f"Second request should wait ~1 second, got {second_wait_time}"
    
    @pytest.mark.asyncio
    async def test_api_client_handles_pagination(self):
        """Test API client handles pagination correctly."""
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        client = CivitaiAPIClient(api_key="test_key")
        
        # Mock paginated responses
        with patch.object(client, '_http_client') as mock_http:
            # First page response
            first_response = Mock()
            first_response.status_code = 200
            first_response.json.return_value = {
                "items": [{"id": 1, "name": "Model 1"}],
                "metadata": {
                    "currentPage": 1,
                    "totalPages": 2,
                    "pageSize": 1,
                    "totalItems": 2,
                    "nextCursor": "cursor_123"
                }
            }
            first_response.headers = {}
            
            # Second page response
            second_response = Mock()
            second_response.status_code = 200
            second_response.json.return_value = {
                "items": [{"id": 2, "name": "Model 2"}],
                "metadata": {
                    "currentPage": 2,
                    "totalPages": 2,
                    "pageSize": 1,
                    "totalItems": 2,
                    "nextCursor": None
                }
            }
            second_response.headers = {}
            
            # Configure mock to return different responses for different calls
            mock_http.get = AsyncMock(side_effect=[first_response, second_response])
            
            # Test pagination handling
            all_models = []
            async for page in client.get_models_paginated({"limit": 1}):
                all_models.extend(page.get('items', []))
            
            # Verify all models were retrieved
            assert len(all_models) == 2, "Should retrieve all models across pages"
            assert all_models[0]['id'] == 1, "First model should be correct"
            assert all_models[1]['id'] == 2, "Second model should be correct"
            
            # Verify multiple requests were made
            assert mock_http.get.call_count == 2, "Should make request for each page"
    
    def test_response_cache_functionality(self):
        """Test response cache functionality and TTL handling."""
        # Import cache module
        cache_path = self.api_dir / "cache.py"
        assert cache_path.exists(), "cache.py must exist"
        
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        # Test ResponseCache class exists
        assert hasattr(cache_module, 'ResponseCache'), "ResponseCache class must exist"
        ResponseCache = cache_module.ResponseCache
        
        # Test cache initialization
        cache = ResponseCache(ttl_seconds=300)  # 5 minutes
        
        # Test cache properties
        assert hasattr(cache, 'ttl_seconds'), "Cache must have TTL configuration"
        assert hasattr(cache, 'cache'), "Cache must have storage mechanism"
        assert cache.ttl_seconds == 300, "TTL should be set correctly"
        
        # Test cache key generation
        params = {"query": "anime", "types": ["Checkpoint"], "limit": 20}
        cache_key = cache.generate_cache_key("models", params)
        
        assert isinstance(cache_key, str), "Cache key must be string"
        assert len(cache_key) > 0, "Cache key must not be empty"
        
        # Same parameters should generate same key
        same_key = cache.generate_cache_key("models", params)
        assert cache_key == same_key, "Same parameters should generate same cache key"
        
        # Different parameters should generate different key
        different_params = {"query": "anime", "types": ["LORA"], "limit": 20}
        different_key = cache.generate_cache_key("models", different_params)
        assert cache_key != different_key, "Different parameters should generate different cache key"
    
    def test_cache_storage_and_retrieval(self):
        """Test cache storage and retrieval with TTL expiration."""
        cache_path = self.api_dir / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        ResponseCache = cache_module.ResponseCache
        
        # Test with short TTL for testing
        cache = ResponseCache(ttl_seconds=1)
        
        # Test cache storage
        test_data = {"items": [{"id": 1, "name": "Test Model"}], "metadata": {}}
        cache_key = "test_key"
        
        cache.store(cache_key, test_data)
        
        # Test immediate retrieval
        retrieved_data = cache.get(cache_key)
        assert retrieved_data is not None, "Data should be retrievable immediately after storage"
        assert retrieved_data == test_data, "Retrieved data should match stored data"
        
        # Test cache hit
        assert cache.is_cache_hit(cache_key), "Should be cache hit for valid data"
        
        # Test cache miss for non-existent key
        assert not cache.is_cache_hit("non_existent_key"), "Should be cache miss for non-existent key"
        
        # Test TTL expiration (need to wait for expiration)
        import time
        time.sleep(1.1)  # Wait for TTL to expire
        
        expired_data = cache.get(cache_key)
        assert expired_data is None, "Data should be None after TTL expiration"
        assert not cache.is_cache_hit(cache_key), "Should be cache miss after TTL expiration"
    
    @pytest.mark.asyncio
    async def test_api_client_integrates_with_cache(self):
        """Test API client properly integrates with response cache."""
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        
        client = CivitaiAPIClient(api_key="test_key")
        
        # Test cache integration
        assert hasattr(client, 'cache'), "Client must have cache"
        
        test_response = {"items": [{"id": 1, "name": "Cached Model"}], "metadata": {}}
        
        # Mock HTTP client to return test response
        with patch.object(client, '_http_client') as mock_http:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = test_response
            mock_response.headers = {}
            mock_http.get = AsyncMock(return_value=mock_response)
            
            # First request should hit API and cache the result
            params = {"limit": 10}
            result1 = await client.get_models(params)
            
            # Verify API was called
            assert mock_http.get.call_count == 1, "API should be called for first request"
            assert result1 == test_response, "First result should match API response"
            
            # Second request with same parameters should use cache
            result2 = await client.get_models(params)
            
            # Verify API was not called again (cache hit)
            assert mock_http.get.call_count == 1, "API should not be called again for cached request"
            assert result2 == test_response, "Second result should match cached response"
    
    def test_search_params_data_class(self):
        """Test SearchParams data class for parameter management."""
        # Import params module
        params_path = self.api_dir / "params.py"
        assert params_path.exists(), "params.py must exist"
        
        spec = importlib.util.spec_from_file_location("params", params_path)
        params_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(params_module)
        
        # Test SearchParams class exists
        assert hasattr(params_module, 'SearchParams'), "SearchParams class must exist"
        SearchParams = params_module.SearchParams
        
        # Test basic parameters
        basic_params = SearchParams(
            query="anime style",
            types=["Checkpoint", "LORA"],
            limit=50
        )
        
        # Validate basic properties
        assert basic_params.query == "anime style", "Query should be set correctly"
        assert basic_params.types == ["Checkpoint", "LORA"], "Types should be set correctly"
        assert basic_params.limit == 50, "Limit should be set correctly"
        
        # Test parameter serialization
        param_dict = basic_params.to_dict()
        assert isinstance(param_dict, dict), "Serialization should return dictionary"
        assert 'query' in param_dict, "Serialized params should contain query"
        assert 'types' in param_dict, "Serialized params should contain types"
        assert 'limit' in param_dict, "Serialized params should contain limit"
        
        # Test that None values are excluded from serialization
        params_with_none = SearchParams(query="test", tags=None)
        serialized = params_with_none.to_dict()
        assert 'tags' not in serialized, "None values should be excluded from serialization"
    
    def test_advanced_filters_data_class(self):
        """Test AdvancedFilters data class for complex filtering."""
        params_path = self.api_dir / "params.py"
        spec = importlib.util.spec_from_file_location("params", params_path)
        params_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(params_module)
        
        # Test AdvancedFilters class exists
        assert hasattr(params_module, 'AdvancedFilters'), "AdvancedFilters class must exist"
        AdvancedFilters = params_module.AdvancedFilters
        
        # Test advanced filters creation
        from datetime import datetime
        
        filters = AdvancedFilters(
            min_downloads=1000,
            max_downloads=50000,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            nsfw=False,
            featured=True,
            verified=True,
            commercial=True
        )
        
        # Validate filter properties
        assert filters.min_downloads == 1000, "Min downloads should be set correctly"
        assert filters.max_downloads == 50000, "Max downloads should be set correctly"
        assert filters.nsfw is False, "NSFW filter should be set correctly"
        assert filters.featured is True, "Featured filter should be set correctly"
        assert filters.verified is True, "Verified filter should be set correctly"
        assert filters.commercial is True, "Commercial filter should be set correctly"
        
        # Test date handling
        assert isinstance(filters.start_date, datetime), "Start date should be datetime object"
        assert isinstance(filters.end_date, datetime), "End date should be datetime object"
        
        # Test filter serialization
        filter_dict = filters.to_dict()
        assert isinstance(filter_dict, dict), "Filter serialization should return dictionary"
        assert 'min_downloads' in filter_dict, "Should include min_downloads"
        assert 'max_downloads' in filter_dict, "Should include max_downloads"
        assert 'nsfw' in filter_dict, "Should include nsfw"