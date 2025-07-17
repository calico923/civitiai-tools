"""Search engine implementation with advanced filtering."""

import asyncio
from typing import List, Optional, Set

from .interfaces import (
    ISearchEngine, IAPIClient, ModelInfo, ModelVersion,
    SearchParams, ModelType
)
from .api_client import CivitAIAPIClient
from .config import ConfigManager


class ModelSearchEngine(ISearchEngine):
    """Advanced search engine for CivitAI models."""
    
    def __init__(self, api_client: Optional[IAPIClient] = None, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.api_client = api_client
        self._owned_client = False
        
        # If no client provided, we'll create our own
        if not self.api_client:
            self.api_client = CivitAIAPIClient(self.config)
            self._owned_client = True
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self._owned_client:
            await self.api_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owned_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def search(self, params: SearchParams) -> List[ModelInfo]:
        """Search for models with advanced filtering."""
        all_models = []
        seen_ids = set()
        
        # If searching for multiple base models, we need to do multiple searches
        # since the API doesn't support OR operations for base models
        if params.base_models and len(params.base_models) > 1:
            # Create separate search for each base model
            for base_model in params.base_models:
                sub_params = SearchParams(
                    query=params.query,
                    types=params.types,
                    tags=params.tags,
                    base_models=[base_model],
                    sort=params.sort,
                    nsfw=params.nsfw,
                    limit=params.limit,
                    page=params.page
                )
                
                models, _ = await self.api_client.search_models(sub_params)
                
                # Add unique models
                for model in models:
                    if model.id not in seen_ids:
                        seen_ids.add(model.id)
                        all_models.append(model)
        else:
            # Single search
            models, next_cursor = await self.api_client.search_models(params)
            all_models.extend(models)
            
            # Handle pagination if we need more results
            current_page = 1
            while next_cursor and len(all_models) < params.limit * params.page:
                # Note: This is simplified - in production you'd handle cursor properly
                current_page += 1
                sub_params = SearchParams(
                    query=params.query,
                    types=params.types,
                    tags=params.tags,
                    base_models=params.base_models,
                    sort=params.sort,
                    nsfw=params.nsfw,
                    limit=params.limit,
                    page=current_page
                )
                
                models, next_cursor = await self.api_client.search_models(sub_params)
                all_models.extend(models)
        
        # Apply client-side filtering if needed
        if params.base_models:
            all_models = await self.filter_by_base_model(all_models, params.base_models)
        
        # Apply pagination to final results
        start_idx = (params.page - 1) * params.limit
        end_idx = start_idx + params.limit
        
        return all_models[start_idx:end_idx]
    
    async def filter_by_base_model(self, models: List[ModelInfo], base_models: List[str]) -> List[ModelInfo]:
        """Filter models by base model (client-side)."""
        if not base_models:
            return models
        
        # Normalize base model names for comparison
        normalized_base_models = {bm.lower().replace(' ', '') for bm in base_models}
        
        filtered_models = []
        
        # We need to fetch version details to check base models
        for model in models:
            try:
                versions = await self.api_client.get_model_versions(model.id)
                
                # Check if any version matches the base models
                for version in versions:
                    if version.base_model:
                        normalized_version_base = version.base_model.lower().replace(' ', '')
                        if any(base in normalized_version_base or normalized_version_base in base 
                              for base in normalized_base_models):
                            filtered_models.append(model)
                            break
            except Exception:
                # Skip models that fail to load versions
                continue
        
        return filtered_models
    
    async def search_by_tags(self, tags: List[str], params: Optional[SearchParams] = None) -> List[ModelInfo]:
        """Search models by tags with AND logic."""
        if not params:
            params = SearchParams()
        
        params.tags = tags
        return await self.search(params)
    
    async def search_similar(self, model: ModelInfo, limit: int = 10) -> List[ModelInfo]:
        """Find similar models based on tags and type."""
        # Search for models with similar tags
        if model.tags:
            params = SearchParams(
                types=[model.type],
                tags=model.tags[:5],  # Use top 5 tags
                limit=limit + 1,  # +1 to exclude self
                nsfw=None  # Don't filter by NSFW for similar search
            )
            
            results = await self.search(params)
            
            # Remove the original model from results
            return [m for m in results if m.id != model.id][:limit]
        else:
            # If no tags, search by type only
            params = SearchParams(
                types=[model.type],
                limit=limit + 1
            )
            
            results = await self.search(params)
            return [m for m in results if m.id != model.id][:limit]
    
    async def get_trending(self, time_period: str = "week", limit: int = 20) -> List[ModelInfo]:
        """Get trending models for a time period."""
        # The API doesn't directly support time-based trending,
        # so we'll use most downloaded as a proxy
        params = SearchParams(
            sort=SortOrder.MOST_DOWNLOADED,
            limit=limit
        )
        
        return await self.search(params)
    
    async def get_by_creator(self, username: str, limit: int = 20) -> List[ModelInfo]:
        """Get models by a specific creator."""
        # Search with creator's username in query
        params = SearchParams(
            query=f"creator:{username}",
            limit=limit
        )
        
        results = await self.search(params)
        
        # Filter to ensure exact creator match
        return [m for m in results if m.creator.lower() == username.lower()]


class SearchCache:
    """Simple in-memory cache for search results."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl_seconds
    
    def _make_key(self, params: SearchParams) -> str:
        """Create cache key from search parameters."""
        parts = [
            params.query or "",
            ",".join(t.value for t in (params.types or [])),
            ",".join(params.tags or []),
            ",".join(params.base_models or []),
            params.sort.value if params.sort else "",
            str(params.nsfw),
            str(params.limit),
            str(params.page)
        ]
        return "|".join(parts)
    
    def get(self, params: SearchParams) -> Optional[List[ModelInfo]]:
        """Get cached results if available and not expired."""
        import time
        
        key = self._make_key(params)
        if key in self.cache:
            timestamp = self.timestamps[key]
            if time.time() - timestamp < self.ttl:
                return self.cache[key]
            else:
                # Expired, remove from cache
                del self.cache[key]
                del self.timestamps[key]
        
        return None
    
    def set(self, params: SearchParams, results: List[ModelInfo]) -> None:
        """Cache search results."""
        import time
        
        key = self._make_key(params)
        self.cache[key] = results
        self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        self.timestamps.clear()


class CachedSearchEngine(ModelSearchEngine):
    """Search engine with caching support."""
    
    def __init__(self, api_client: Optional[IAPIClient] = None, config: Optional[ConfigManager] = None):
        super().__init__(api_client, config)
        self.cache = SearchCache()
    
    async def search(self, params: SearchParams) -> List[ModelInfo]:
        """Search with caching."""
        # Check cache first
        cached = self.cache.get(params)
        if cached is not None:
            return cached
        
        # Perform search
        results = await super().search(params)
        
        # Cache results
        self.cache.set(params, results)
        
        return results