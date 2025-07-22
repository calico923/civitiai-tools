#!/usr/bin/env python3
"""
CivitAI API Client.
Unified API client for CivitAI service integration with rate limiting, caching, and error handling.
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncIterator, List
import sys
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
        cache_ttl: int = 300
    ):
        """
        Initialize CivitAI API client.
        
        Args:
            api_key: CivitAI API key
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds
            requests_per_second: Rate limit for requests
            cache_ttl: Cache TTL in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.rate_limiter = RateLimiter(requests_per_second)
        self.cache = ResponseCache(cache_ttl)
        
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
    
    async def get_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get models from CivitAI API.
        
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
        
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        # Make API request
        url = f"{self.base_url}/models"
        
        try:
            response = await self._http_client.get(url, params=params)
            
            # Handle HTTP errors
            if response.status_code == 404:
                raise Exception(f"API endpoint not found: {response.status_code}")
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise Exception(f"Rate limited (429): Retry after {retry_after} seconds")
            elif response.status_code >= 400:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            # Parse response
            result = response.json()
            
            # Cache successful response
            self.cache.store(cache_key, result)
            
            return result
            
        except httpx.TimeoutException:
            raise Exception("Request timeout")
        except httpx.ConnectError:
            raise Exception("Connection failed")
        except Exception as e:
            # Re-raise known exceptions
            if "timeout" in str(e).lower() or "connect" in str(e).lower() or "404" in str(e) or "429" in str(e):
                raise
            # Wrap other exceptions
            raise Exception(f"API request failed: {str(e)}")
    
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