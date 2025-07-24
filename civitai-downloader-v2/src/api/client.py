#!/usr/bin/env python3
"""
CivitAI API Client.
Unified API client for CivitAI service integration with rate limiting, caching, and error handling.
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncIterator, List
import sys
import math
import random
from pathlib import Path

# Add parent directory to path for imports
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from rate_limiter import RateLimiter
from cache import ResponseCache
from params import SearchParams


class CivitaiAPIClient:
    """Unified API client for CivitAI services."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://civitai.com/api/v1",
        timeout: int = 30,
        requests_per_second: float = 0.5,
        cache_ttl: int = 300,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        max_concurrent_requests: int = 3
    ):
        """
        Initialize CivitAI API client.
        
        Args:
            api_key: CivitAI API key
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds
            requests_per_second: Rate limit for requests
            cache_ttl: Cache TTL in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Exponential backoff factor for retries
            max_concurrent_requests: Maximum concurrent requests
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.max_concurrent_requests = max_concurrent_requests
        self.rate_limiter = RateLimiter(requests_per_second)
        self.cache = ResponseCache(cache_ttl)
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Fallback manager for unofficial API features per design.md
        self.fallback_manager = self._init_fallback_manager()
        
        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            headers=self.get_headers()
        )
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            'User-Agent': 'CivitAI-Downloader-v2/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    async def _make_request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make HTTP request with retry logic and enhanced error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response
            
        Raises:
            Exception: After all retry attempts failed
        """
        async with self._semaphore:  # Control concurrency
            last_exception = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    # Apply rate limiting
                    await self.rate_limiter.wait()
                    
                    # Make request
                    response = await self._http_client.request(method, url, **kwargs)
                    
                    # Handle specific HTTP status codes
                    if response.status_code == 429:
                        # Rate limited - record error and calculate backoff
                        self.rate_limiter.record_rate_limit_error()
                        
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            # Use server-provided retry-after value
                            backoff_time = float(retry_after)
                        else:
                            # Exponential backoff with jitter
                            backoff_time = (self.retry_backoff_factor ** attempt) + random.uniform(0, 1)
                        
                        if attempt < self.max_retries:
                            print(f"Rate limited (429). Retrying in {backoff_time:.1f}s... (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(backoff_time)
                            continue
                        else:
                            raise Exception(f"Rate limited (429) after {self.max_retries} retries")
                    
                    elif response.status_code >= 500:
                        # Server error - retry with exponential backoff
                        self.rate_limiter.record_error()
                        
                        if attempt < self.max_retries:
                            backoff_time = (self.retry_backoff_factor ** attempt) + random.uniform(0, 1)
                            print(f"Server error ({response.status_code}). Retrying in {backoff_time:.1f}s... (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(backoff_time)
                            continue
                        else:
                            raise Exception(f"Server error ({response.status_code}) after {self.max_retries} retries: {response.text}")
                    
                    elif response.status_code == 404:
                        # Not found - don't retry
                        raise Exception(f"API endpoint not found: {response.status_code}")
                    
                    elif response.status_code >= 400:
                        # Client error - don't retry
                        raise Exception(f"API error {response.status_code}: {response.text}")
                    
                    # Success - record it
                    self.rate_limiter.record_success()
                    return response
                    
                except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                    last_exception = e
                    self.rate_limiter.record_error()
                    
                    if attempt < self.max_retries:
                        backoff_time = (self.retry_backoff_factor ** attempt) + random.uniform(0, 1)
                        error_type = type(e).__name__
                        print(f"Network error ({error_type}). Retrying in {backoff_time:.1f}s... (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        raise Exception(f"Network error after {self.max_retries} retries: {str(e)}")
                
                except Exception as e:
                    # Other errors - don't retry
                    raise Exception(f"Request failed: {str(e)}")
            
            # Should not reach here, but handle it
            if last_exception:
                raise Exception(f"Request failed after all retries: {str(last_exception)}")
            else:
                raise Exception("Request failed for unknown reason")
    
    async def get_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get models from CivitAI API with enhanced retry logic.
        
        Args:
            params: Search parameters
            
        Returns:
            API response with models data
        """
        # Check cache first
        cache_key = self.cache.generate_cache_key("models", params)
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        # Build URL with proper array parameter handling
        url = self._build_url_with_array_params(f"{self.base_url}/models", params)
        
        # Make request with retry logic
        response = await self._make_request_with_retry("GET", url)
        
        # Parse response
        result = response.json()
        
        # Cache successful response
        self.cache.store(cache_key, result)
        
        return result
    
    async def get_models_paginated(self, params: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Get models with pagination support.
        
        Args:
            params: Search parameters
            
        Yields:
            Pages of model data
        """
        current_params = params.copy()
        
        while True:
            try:
                response = await self.get_models(current_params)
                yield response
                
                metadata = response.get('metadata', {})
                
                # Handle cursor-based pagination
                if 'nextCursor' in metadata and metadata['nextCursor']:
                    current_params['cursor'] = metadata['nextCursor']
                    if 'page' in current_params:
                        del current_params['page'] # Remove page if cursor is used
                # Handle page-based pagination
                elif 'currentPage' in metadata and 'totalPages' in metadata:
                    current_page = metadata.get('currentPage', 1)
                    total_pages = metadata.get('totalPages', 1)
                    
                    if current_page >= total_pages:
                        break
                    
                    current_params['page'] = current_page + 1
                else:
                    break # No more pages
                
            except Exception:
                # Stop pagination on error
                break
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _process_array_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process array parameters for API compatibility.
        
        CivitAI API expects certain parameters in specific formats:
        - allowCommercialUse: Uses array bracket notation: allowCommercialUse[]=Image
        - others: Uses comma-separated strings
        
        Args:
            params: Original parameters
            
        Returns:
            Processed parameters compatible with CivitAI API
        """
        processed = {}
        
        for key, value in params.items():
            if key == 'allowCommercialUse' and isinstance(value, list):
                # CRITICAL FIX: allowCommercialUse uses array bracket notation
                # httpx handles this automatically when we pass the list directly
                processed[key] = value
            elif key in ['types', 'tags', 'baseModels'] and isinstance(value, list):
                # Other array parameters use comma-separated strings
                processed[key] = ','.join(str(item) for item in value)
            else:
                # Non-array parameters pass through unchanged
                processed[key] = value
        
        return processed
    
    def _build_url_with_array_params(self, base_url: str, params: Dict[str, Any]) -> str:
        """
        Build URL with proper array parameter handling for CivitAI API.
        
        CivitAI API expects allowCommercialUse as array bracket notation:
        allowCommercialUse[]=Image&allowCommercialUse[]=Rent
        
        Args:
            base_url: Base URL
            params: Parameters to encode
            
        Returns:
            Complete URL with properly encoded parameters
        """
        import urllib.parse
        
        query_parts = []
        
        for key, value in params.items():
            if isinstance(value, list):
                # All array parameters use array bracket notation
                for item in value:
                    query_parts.append(f'{key}[]={urllib.parse.quote(str(item))}')
            elif value is not None:
                # Regular parameters
                query_parts.append(f'{key}={urllib.parse.quote(str(value))}')
        
        if query_parts:
            return f'{base_url}?{"&".join(query_parts)}'
        else:
            return base_url
    
    def _init_fallback_manager(self) -> Dict[str, Any]:
        """Initialize fallback manager for unofficial API features per design.md."""
        return {
            'unofficial_endpoints': [],
            'retry_count': 3,
            'fallback_enabled': True,
            'detected_features': {}
        }
    
    async def search_models(self, search_params: SearchParams) -> List[Dict[str, Any]]:
        """
        Unified search interface for models per design.md requirements.
        
        Args:
            search_params: Search parameters object
            
        Returns:
            List of model objects from API response
        """
        # Convert SearchParams to dict for API call
        params_dict = search_params.to_api_params()
        
        # Get full API response
        api_response = await self.get_models(params_dict)
        
        # Extract items array from API response
        # CivitAI API returns: {"items": [...], "metadata": {...}}
        return api_response.get("items", [])
    
    async def get_model_by_id(self, model_id: int) -> Dict[str, Any]:
        """
        Get a specific model by ID with enhanced retry logic.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model data
        """
        # Check cache first
        cache_key = self.cache.generate_cache_key("model", {"id": model_id})
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        url = f"{self.base_url}/models/{model_id}"
        
        # Make request with retry logic
        response = await self._make_request_with_retry("GET", url)
        
        result = response.json()
        
        # Cache successful response
        self.cache.store(cache_key, result)
        
        return result
    
    async def get_model_version_by_id(self, version_id: int) -> Dict[str, Any]:
        """
        Get a specific model version by ID with enhanced retry logic.
        
        Args:
            version_id: Version ID
            
        Returns:
            Version data
        """
        # Check cache first
        cache_key = self.cache.generate_cache_key("version", {"id": version_id})
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        url = f"{self.base_url}/model-versions/{version_id}"
        
        # Make request with retry logic
        response = await self._make_request_with_retry("GET", url)
        
        result = response.json()
        
        # Cache successful response
        self.cache.store(cache_key, result)
        
        return result
    
    def detect_unofficial_features(self) -> Dict[str, bool]:
        """
        Detect unofficial API features per design.md.
        
        Returns:
            Dictionary of detected features and their availability
        """
        detected = {
            'bulk_download': False,
            'advanced_search': False,
            'model_analytics': False,
            'enhanced_metadata': False
        }
        
        # Update with any previously detected features
        detected.update(self.fallback_manager.get('detected_features', {}))
        
        return detected