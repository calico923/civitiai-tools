#!/usr/bin/env python3
"""
Search Strategy for CivitAI Downloader.
Provides advanced search capabilities with filtering, sorting, and pagination.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from enum import Enum
import requests
from concurrent.futures import ThreadPoolExecutor

# Optional import for concurrent processing
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from ...api.auth import AuthManager
    from ...core.config.system_config import SystemConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from api.auth import AuthManager
    from core.config.system_config import SystemConfig


class ModelType(Enum):
    """Model types supported by CivitAI."""
    CHECKPOINT = "Checkpoint"
    TEXTUAL_INVERSION = "TextualInversion"
    HYPERNETWORK = "Hypernetwork"
    AESTHETIC_GRADIENT = "AestheticGradient"
    LORA = "LORA"
    CONTROLNET = "Controlnet"
    POSES = "Poses"


class SortOrder(Enum):
    """Sort order options."""
    HIGHEST_RATED = "Highest Rated"
    MOST_DOWNLOADED = "Most Downloaded"
    NEWEST = "Newest"
    OLDEST = "Oldest"
    MOST_LIKED = "Most Liked"
    MOST_DISCUSSED = "Most Discussed"


class Period(Enum):
    """Time period for statistics."""
    ALL_TIME = "AllTime"
    YEAR = "Year"
    MONTH = "Month"
    WEEK = "Week"
    DAY = "Day"


@dataclass
class SearchFilters:
    """Search filter configuration."""
    query: Optional[str] = None
    username: Optional[str] = None
    tag: Optional[str] = None
    model_types: List[ModelType] = field(default_factory=list)
    sort: SortOrder = SortOrder.HIGHEST_RATED
    period: Period = Period.ALL_TIME
    rating: Optional[int] = None  # Minimum rating
    nsfw: Optional[bool] = None  # None = both, True = NSFW only, False = SFW only
    favorites: Optional[bool] = None
    hidden: Optional[bool] = None
    primary_file_only: bool = True
    allow_no_credit: Optional[bool] = None
    allow_derivatives: Optional[bool] = None
    allow_different_license: Optional[bool] = None
    allow_commercial_use: Optional[bool] = None


@dataclass
class SearchMetadata:
    """Search result metadata."""
    total_items: int
    current_page: int
    per_page: int
    total_pages: int
    next_page: Optional[str] = None
    prev_page: Optional[str] = None


@dataclass
class SearchResult:
    """Single search result."""
    id: int
    name: str
    description: Optional[str]
    type: str
    nsfw: bool
    tags: List[str]
    rating: float
    download_count: int
    favorite_count: int
    comment_count: int
    creator: Dict[str, Any]
    model_versions: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    stats: Dict[str, Any]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create SearchResult from API response data."""
        # Handle tags - they can be either strings or objects
        tags_raw = data.get('tags', [])
        if tags_raw and isinstance(tags_raw[0], str):
            # Tags are already strings
            tags = tags_raw
        else:
            # Tags are objects with 'name' field
            tags = [tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in tags_raw]
        
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description'),
            type=data.get('type', ''),
            nsfw=data.get('nsfw', False),
            tags=tags,
            rating=data.get('stats', {}).get('rating', 0.0),
            download_count=data.get('stats', {}).get('downloadCount', 0),
            favorite_count=data.get('stats', {}).get('favoriteCount', 0),
            comment_count=data.get('stats', {}).get('commentCount', 0),
            creator=data.get('creator', {}),
            model_versions=data.get('modelVersions', []),
            created_at=data.get('createdAt', ''),
            updated_at=data.get('updatedAt', ''),
            stats=data.get('stats', {})
        )


class SearchStrategy:
    """Advanced search strategy with filtering and pagination."""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None, config: Optional[SystemConfig] = None):
        """
        Initialize search strategy.
        
        Args:
            auth_manager: Authentication manager
            config: System configuration
        """
        self.auth_manager = auth_manager or AuthManager()
        self.config = config or SystemConfig()
        self.base_url = self.config.get('api.base_url', 'https://civitai.com/api/v1')
        self.timeout = self.config.get('api.timeout', 30)
        self.max_retries = int(self.config.get('api.max_retries', 3))
        
        # Search statistics
        self.stats = {
            'total_searches': 0,
            'total_results': 0,
            'avg_response_time': 0.0,
            'errors': 0
        }
    
    def build_search_params(self, filters: SearchFilters, page: int = 1, limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Build search parameters from filters.
        
        Args:
            filters: Search filters
            page: Page number (1-based) - ignored if query is present (uses cursor instead)
            limit: Results per page
            cursor: Cursor for pagination (used with query search)
            
        Returns:
            Dictionary of search parameters
        """
        params = {
            'limit': limit
        }
        
        if filters.query:
            params['query'] = filters.query
            # Use cursor-based pagination for query searches
            if cursor:
                params['cursor'] = cursor
        else:
            # Use page-based pagination for non-query searches
            params['page'] = page
        
        if filters.username:
            params['username'] = filters.username
        
        if filters.tag:
            params['tag'] = filters.tag
        
        if filters.model_types:
            params['types'] = [t.value for t in filters.model_types]
        
        if filters.sort:
            params['sort'] = filters.sort.value
        
        if filters.period and filters.period != Period.ALL_TIME:
            params['period'] = filters.period.value
        
        if filters.rating is not None:
            params['rating'] = filters.rating
        
        if filters.nsfw is not None:
            params['nsfw'] = filters.nsfw
        
        if filters.favorites is not None:
            params['favorites'] = filters.favorites
        
        if filters.hidden is not None:
            params['hidden'] = filters.hidden
        
        # Always include primaryFileOnly if specified (default is True)
        params['primaryFileOnly'] = filters.primary_file_only
        
        # License and usage filters
        if filters.allow_no_credit is not None:
            params['allowNoCredit'] = filters.allow_no_credit
        
        if filters.allow_derivatives is not None:
            params['allowDerivatives'] = filters.allow_derivatives
        
        if filters.allow_different_license is not None:
            params['allowDifferentLicense'] = filters.allow_different_license
        
        if filters.allow_commercial_use is not None:
            params['allowCommercialUse'] = filters.allow_commercial_use
        
        return params
    
    def search(self, filters: SearchFilters, page: int = 1, limit: int = 20, cursor: Optional[str] = None) -> tuple[List[SearchResult], SearchMetadata]:
        """
        Perform search with filters.
        
        Args:
            filters: Search filters
            page: Page number (1-based) - ignored if query is present
            limit: Results per page
            cursor: Cursor for pagination (used with query search)
            
        Returns:
            Tuple of (search results, metadata)
        """
        start_time = time.time()
        
        try:
            params = self.build_search_params(filters, page, limit, cursor)
            headers = self.auth_manager.get_auth_headers()
            
            response = self._make_request(
                'GET',
                f'{self.base_url}/models',
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get('items', []):
                try:
                    result = SearchResult.from_api_response(item)
                    results.append(result)
                except Exception as e:
                    # Log parsing errors but continue
                    print(f"Warning: Failed to parse result: {e}")
            
            # Parse metadata
            metadata_raw = data.get('metadata', {})
            metadata = SearchMetadata(
                total_items=metadata_raw.get('totalItems', 0),
                current_page=metadata_raw.get('currentPage', page),
                per_page=metadata_raw.get('pageSize', limit),
                total_pages=metadata_raw.get('totalPages', 1),
                next_page=metadata_raw.get('nextCursor'),  # For cursor-based pagination
                prev_page=metadata_raw.get('prevCursor')   # For cursor-based pagination
            )
            
            # Update statistics
            response_time = time.time() - start_time
            self._update_stats(len(results), response_time, success=True)
            
            return results, metadata
            
        except Exception as e:
            self._update_stats(0, time.time() - start_time, success=False)
            raise Exception(f"Search failed: {e}")
    
    async def search_async(self, filters: SearchFilters, page: int = 1, limit: int = 20) -> tuple[List[SearchResult], SearchMetadata]:
        """
        Async version of search.
        
        Args:
            filters: Search filters
            page: Page number (1-based)
            limit: Results per page
            
        Returns:
            Tuple of (search results, metadata)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, filters, page, limit)
    
    def search_all_pages(self, filters: SearchFilters, limit: int = 20, max_pages: Optional[int] = None) -> AsyncGenerator[SearchResult, None]:
        """
        Search all pages with a generator.
        
        Args:
            filters: Search filters
            limit: Results per page
            max_pages: Maximum pages to fetch (None for all)
            
        Yields:
            Individual search results
        """
        page = 1
        total_fetched = 0
        
        while True:
            try:
                results, metadata = self.search(filters, page, limit)
                
                if not results:
                    break
                
                for result in results:
                    yield result
                    total_fetched += 1
                
                # Check if we should continue
                if max_pages and page >= max_pages:
                    break
                
                if page >= metadata.total_pages:
                    break
                
                page += 1
                
                # Rate limiting - small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
    
    def search_by_ids(self, model_ids: List[int], max_concurrent: int = 5) -> List[SearchResult]:
        """
        Search for specific models by IDs with concurrent processing.
        
        OPTIMIZATION: Uses concurrent requests to minimize the N+1 query problem.
        While CivitAI API doesn't provide batch endpoints, concurrent requests
        significantly improve performance over sequential calls.
        
        Performance characteristics:
        - Sequential: ~0.1s * N requests  
        - Concurrent: ~(N / max_concurrent) * max_request_time
        
        Args:
            model_ids: List of model IDs
            max_concurrent: Maximum concurrent requests (default: 5)
            
        Returns:
            List of search results (preserves order of input IDs)
        """
        # Check if aiohttp is available for concurrent processing
        if not AIOHTTP_AVAILABLE:
            print("aiohttp not available, falling back to sequential processing")
            return self._search_by_ids_sequential(model_ids)
        
        results = []
        headers = self.auth_manager.get_auth_headers()
        
        async def fetch_model(session, model_id: int) -> Optional[SearchResult]:
            """Fetch a single model asynchronously."""
            try:
                async with session.get(
                    f'{self.base_url}/models/{model_id}',
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return SearchResult.from_api_response(data)
                    return None
            except Exception as e:
                print(f"Error fetching model {model_id}: {e}")
                return None
        
        async def fetch_all_models():
            """Fetch all models concurrently."""
            connector = aiohttp.TCPConnector(limit=max_concurrent)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                connector=connector, 
                timeout=timeout
            ) as session:
                # Create semaphore to limit concurrent requests
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def fetch_with_semaphore(model_id: int):
                    async with semaphore:
                        result = await fetch_model(session, model_id)
                        # Rate limiting - small delay between requests
                        await asyncio.sleep(0.02)  # 50 requests/second max
                        return (model_id, result)
                
                # Execute all requests concurrently
                tasks = [fetch_with_semaphore(model_id) for model_id in model_ids]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results, preserving order
                result_map = {}
                for response in responses:
                    if isinstance(response, tuple) and response[1] is not None:
                        model_id, result = response
                        result_map[model_id] = result
                
                # Return results in original order
                return [result_map.get(model_id) for model_id in model_ids if model_id in result_map]
        
        # Run async operation
        try:
            if hasattr(asyncio, 'get_running_loop'):
                # We're in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # Use thread pool to avoid blocking the current loop
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_all_models())
                        results = future.result()
                except RuntimeError:
                    results = asyncio.run(fetch_all_models())
            else:
                results = asyncio.run(fetch_all_models())
        except Exception as e:
            print(f"Concurrent fetch failed, falling back to sequential: {e}")
            # Fallback to sequential processing
            return self._search_by_ids_sequential(model_ids)
        
        return results
    
    def _search_by_ids_sequential(self, model_ids: List[int]) -> List[SearchResult]:
        """Sequential fallback for search_by_ids."""
        results = []
        headers = self.auth_manager.get_auth_headers()
        
        for model_id in model_ids:
            try:
                response = self._make_request(
                    'GET',
                    f'{self.base_url}/models/{model_id}',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = SearchResult.from_api_response(data)
                    results.append(result)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching model {model_id}: {e}")
        
        return results
    
    def get_popular_tags(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get popular tags for search suggestions.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of tag information
        """
        try:
            headers = self.auth_manager.get_auth_headers()
            params = {'limit': limit, 'sort': 'Most Used'}
            
            response = self._make_request(
                'GET',
                f'{self.base_url}/tags',
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            
        except Exception as e:
            print(f"Error fetching tags: {e}")
        
        return []
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            Response object
        """
        kwargs.setdefault('timeout', self.timeout)
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                return response
                
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise e
                
                # Exponential backoff
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)
    
    def _update_stats(self, result_count: int, response_time: float, success: bool) -> None:
        """Update search statistics."""
        self.stats['total_searches'] += 1
        
        if success:
            self.stats['total_results'] += result_count
            # Update average response time
            total_searches = self.stats['total_searches']
            current_avg = self.stats['avg_response_time']
            self.stats['avg_response_time'] = (
                (current_avg * (total_searches - 1) + response_time) / total_searches
            )
        else:
            self.stats['errors'] += 1
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset search statistics."""
        self.stats = {
            'total_searches': 0,
            'total_results': 0,
            'avg_response_time': 0.0,
            'errors': 0
        }


# Convenience functions for common search patterns

def search_checkpoints(query: str = None, nsfw: bool = False, limit: int = 20) -> List[SearchResult]:
    """Search for checkpoint models."""
    filters = SearchFilters(
        query=query,
        model_types=[ModelType.CHECKPOINT],
        nsfw=nsfw,
        sort=SortOrder.HIGHEST_RATED
    )
    
    strategy = SearchStrategy()
    results, _ = strategy.search(filters, limit=limit)
    return results


def search_loras(query: str = None, limit: int = 20) -> List[SearchResult]:
    """Search for LoRA models."""
    filters = SearchFilters(
        query=query,
        model_types=[ModelType.LORA],
        sort=SortOrder.MOST_DOWNLOADED
    )
    
    strategy = SearchStrategy()
    results, _ = strategy.search(filters, limit=limit)
    return results


def search_by_creator(username: str, limit: int = 20) -> List[SearchResult]:
    """Search models by creator."""
    filters = SearchFilters(
        username=username,
        sort=SortOrder.NEWEST
    )
    
    strategy = SearchStrategy()
    results, _ = strategy.search(filters, limit=limit)
    return results


if __name__ == "__main__":
    # Test the search functionality
    print("Testing CivitAI Search Strategy...")
    
    # Test basic search without query (uses page-based pagination)
    filters = SearchFilters(
        model_types=[ModelType.CHECKPOINT],
        sort=SortOrder.HIGHEST_RATED,
        nsfw=False
    )
    
    strategy = SearchStrategy()
    
    try:
        results, metadata = strategy.search(filters, limit=3)
        
        print(f"\nSearch Results: {len(results)} items")
        print(f"Total available: {metadata.total_items}")
        print(f"Page: {metadata.current_page}/{metadata.total_pages}")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.name}")
            print(f"   Type: {result.type}")
            print(f"   Rating: {result.rating:.1f}")
            print(f"   Downloads: {result.download_count:,}")
            print(f"   Creator: {result.creator.get('username', 'Unknown')}")
            print(f"   Tags: {', '.join(result.tags[:3])}...")
        
        print(f"\nSearch Statistics:")
        stats = strategy.get_search_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Search test failed: {e}")