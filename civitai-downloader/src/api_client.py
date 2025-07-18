"""CivitAI API client implementation."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from .interfaces import (
    IAPIClient, ModelInfo, ModelVersion, ModelFile, ModelImage,
    ModelType, SearchParams, SortOrder, PeriodFilter, ModelCategory
)
from .config import ConfigManager


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
    
    async def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_call
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_call = asyncio.get_event_loop().time()


class CivitAIAPIClient(IAPIClient):
    """CivitAI API client with rate limiting and error handling."""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.base_url = self.config.config.api_base_url.rstrip('/')
        self.api_key = self.config.config.api_key
        self.rate_limiter = RateLimiter(calls_per_minute=60)
        self.session: Optional[ClientSession] = None
        
        # Setup headers
        self.headers = {
            'User-Agent': self.config.config.user_agent,
            'Accept': 'application/json',
        }
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = ClientTimeout(total=self.config.config.api_timeout)
        self.session = ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(
                ssl=self.config.config.verify_ssl
            )
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _normalize_model_type(self, model_type: str) -> str:
        """Normalize model type for API compatibility."""
        # LyCORIS needs to be converted to LoCon for API calls
        if model_type.upper() == "LYCORIS":
            return "LoCon"
        return model_type
    
    def _parse_model_type(self, type_str: str) -> ModelType:
        """Parse model type from API response."""
        type_map = {
            'Checkpoint': ModelType.CHECKPOINT,
            'TextualInversion': ModelType.TEXTUAL_INVERSION,
            'Hypernetwork': ModelType.HYPERNETWORK,
            'AestheticGradient': ModelType.AESTHETIC_GRADIENT,
            'LORA': ModelType.LORA,
            'LoCon': ModelType.LOCON,
            'LyCORIS': ModelType.LYCORIS,
            'Controlnet': ModelType.CONTROLNET,
            'Poses': ModelType.POSES,
            'Wildcards': ModelType.WILDCARDS,
        }
        return type_map.get(type_str, ModelType.OTHER)
    
    def _parse_model_info(self, data: Dict[str, Any]) -> ModelInfo:
        """Parse model info from API response."""
        return ModelInfo(
            id=data['id'],
            name=data['name'],
            type=self._parse_model_type(data.get('type', 'Other')),
            description=data.get('description'),
            tags=data.get('tags', []),
            creator=data.get('creator', {}).get('username', 'Unknown'),
            stats={
                'downloadCount': data.get('stats', {}).get('downloadCount', 0),
                'favoriteCount': data.get('stats', {}).get('favoriteCount', 0),
                'commentCount': data.get('stats', {}).get('commentCount', 0),
                'ratingCount': data.get('stats', {}).get('ratingCount', 0),
                'rating': data.get('stats', {}).get('rating', 0),
            },
            nsfw=data.get('nsfw', False),
            created_at=datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
        )
    
    def _parse_model_version(self, data: Dict[str, Any], model_id: int) -> ModelVersion:
        """Parse model version from API response."""
        files = []
        for file_data in data.get('files', []):
            files.append(ModelFile(
                id=file_data['id'],
                name=file_data['name'],
                size_bytes=file_data['sizeKB'] * 1024,
                format=file_data.get('type', 'Model'),
                fp=file_data.get('metadata', {}).get('fp'),
                hash=file_data.get('hashes', {}).get('SHA256'),
                download_url=file_data['downloadUrl'],
                metadata=file_data.get('metadata', {})
            ))
        
        images = []
        for img_data in data.get('images', []):
            images.append(ModelImage(
                id=img_data['id'],
                url=img_data['url'],
                width=img_data.get('width', 0),
                height=img_data.get('height', 0),
                hash=img_data.get('hash'),
                nsfw=img_data.get('nsfw', False),
                meta=img_data.get('meta')
            ))
        
        return ModelVersion(
            id=data['id'],
            model_id=model_id,
            name=data['name'],
            description=data.get('description'),
            base_model=data.get('baseModel'),
            trained_words=data.get('trainedWords', []),
            files=files,
            images=images,
            download_url=data.get('downloadUrl', ''),
            created_at=datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        )
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and retries."""
        if not self.session:
            raise RuntimeError("API client not initialized. Use 'async with' context manager.")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.config.api_max_retries):
            try:
                await self.rate_limiter.wait()
                
                # Add proxy if configured
                kwargs = {}
                if self.config.config.proxy:
                    kwargs['proxy'] = self.config.config.proxy
                
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            
            except aiohttp.ClientResponseError as e:
                if e.status == 429:  # Rate limited
                    wait_time = min(60, 2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                elif e.status >= 500:  # Server error, retry
                    if attempt < self.config.config.api_max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.config.config.api_max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed after {self.config.config.api_max_retries} attempts")
    
    async def search_models(self, params: SearchParams) -> Tuple[List[ModelInfo], Optional[str]]:
        """Search for models."""
        # Build query parameters
        query_params = {}
        
        if params.query:
            query_params['query'] = params.query
        
        if params.types:
            # Normalize model types for API
            types = [self._normalize_model_type(t.value) for t in params.types]
            query_params['types'] = types
        
        if params.tags:
            query_params['tag'] = params.tags
        
        if params.categories:
            # Categories are used as additional tags
            categories = [cat.value for cat in params.categories]
            existing_tags = query_params.get('tag', [])
            query_params['tag'] = existing_tags + categories
        
        if params.sort:
            query_params['sort'] = params.sort.value
        
        if params.sort_by:
            query_params['sortBy'] = params.sort_by
        
        if params.period != PeriodFilter.ALL_TIME:
            query_params['period'] = params.period.value
        
        if params.nsfw is not None:
            query_params['nsfw'] = params.nsfw
        
        if params.featured is not None:
            query_params['featured'] = params.featured
        
        if params.verified is not None:
            query_params['verified'] = params.verified
        
        if params.commercial is not None:
            query_params['commercial'] = params.commercial
        
        query_params['limit'] = params.limit
        
        # Use cursor for pagination if page > 1
        if params.page > 1:
            # This would need to be handled by storing cursors from previous requests
            # For now, we'll use the simple approach
            pass
        
        # Make request
        response = await self._make_request('GET', '/models', params=query_params)
        
        # Parse models
        models = []
        for item in response.get('items', []):
            try:
                models.append(self._parse_model_info(item))
            except Exception as e:
                # Skip malformed items
                continue
        
        # Extract next cursor from metadata
        next_cursor = response.get('metadata', {}).get('nextCursor')
        
        return models, next_cursor
    
    async def get_model_details(self, model_id: int) -> ModelInfo:
        """Get detailed model information."""
        response = await self._make_request('GET', f'/models/{model_id}')
        return self._parse_model_info(response)
    
    async def get_model_versions(self, model_id: int) -> List[ModelVersion]:
        """Get all versions of a model."""
        # First get the model details which includes versions
        response = await self._make_request('GET', f'/models/{model_id}')
        
        versions = []
        for version_data in response.get('modelVersions', []):
            try:
                versions.append(self._parse_model_version(version_data, model_id))
            except Exception as e:
                # Skip malformed versions
                continue
        
        return versions
    
    async def get_model_version(self, version_id: int) -> ModelVersion:
        """Get specific model version."""
        response = await self._make_request('GET', f'/model-versions/{version_id}')
        # The version endpoint doesn't include model_id, so we'll use 0 as placeholder
        # In practice, you'd get this from the model details
        return self._parse_model_version(response, 0)