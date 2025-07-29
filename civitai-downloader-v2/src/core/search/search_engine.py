#!/usr/bin/env python3
"""
Advanced Search Engine Implementation.
Integrates advanced search parameters with triple filtering and fallback mechanisms.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass

from .advanced_search import (
    AdvancedSearchParams, BaseModelDetector, UnofficialAPIManager,
    ModelCategory, CustomSortMetric, SortOption, FileFormat, NSFWFilter
)
from ..security.security_scanner import SecurityScanner
from ..security.license_manager import LicenseManager
from ..exceptions import SearchError, NetworkError
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Search result with metadata and filtering information."""
    models: List[Dict[str, Any]]
    total_count: int
    filtered_count: int
    page: int
    has_next: bool
    search_metadata: Dict[str, Any]
    filter_applied: Dict[str, Any]
    fallback_used: Optional[str] = None




class AdvancedSearchEngine:
    """
    Advanced search engine implementing requirements 10-12.
    Provides comprehensive search with filtering, sorting, and fallback mechanisms.
    """
    
    def __init__(self, api_client=None):
        """Initialize advanced search engine."""
        self.api_client = api_client
        self.base_model_detector = BaseModelDetector()
        self.unofficial_api_manager = UnofficialAPIManager()
        self.license_manager = LicenseManager()
        self.logger = logging.getLogger(__name__)
        
        # Search performance tracking
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'fallback_used': 0,
            'avg_response_time': 0.0,
            'last_search_time': None
        }
    
    async def search(self, query_or_params, filters=None):
        """
        Search with backward compatibility.
        Support both old (query, filters) and new (AdvancedSearchParams) formats.
        """
        # Handle backward compatibility
        if isinstance(query_or_params, str) and filters is not None:
            # Old format: search(query, filters)
            from .advanced_search import AdvancedSearchParams, NSFWFilter
            search_params = AdvancedSearchParams(
                query=query_or_params,
                model_types=filters.get('types', []),
                nsfw_filter=NSFWFilter.INCLUDE_ALL if filters.get('nsfw', False) else NSFWFilter.SFW_ONLY,
                limit=filters.get('limit', 100)
            )
        else:
            # New format: search(AdvancedSearchParams)
            search_params = query_or_params
        
        return await self._search_internal(search_params)
    
    async def _search_internal(self, search_params: AdvancedSearchParams) -> SearchResult:
        """
        Perform advanced search with comprehensive filtering.
        
        Args:
            search_params: Advanced search parameters
            
        Returns:
            SearchResult with filtered models and metadata
        """
        logger.debug(f"search_engine: search_params type: {type(search_params)}")
        logger.debug(f"search_engine: search_params: {search_params}")
        
        start_time = time.time()
        self.search_stats['total_searches'] += 1
        
        # Validate parameters
        validation_errors = search_params.validate()
        if validation_errors:
            raise ValueError(f"Invalid search parameters: {validation_errors}")
        
        # Attempt search with fallback mechanism
        try:
            result = await self._execute_search_with_fallback(search_params)
            self.search_stats['successful_searches'] += 1
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
        
        # Update performance statistics
        response_time = time.time() - start_time
        self._update_performance_stats(response_time)
        
        return result
    
    async def _search_with_target(self, search_params: AdvancedSearchParams, 
                                original_target: int) -> SearchResult:
        """Internal search method that passes original target to filtering."""
        # Handle backward compatibility
        if isinstance(search_params, str):
            raise ValueError("_search_with_target requires AdvancedSearchParams")
        
        return await self._search_internal_with_target(search_params, original_target)
    
    async def _search_internal_with_target(self, search_params: AdvancedSearchParams, 
                                         original_target: int) -> SearchResult:
        """Internal search with original target for proper filtering."""
        start_time = time.time()
        self.search_stats['total_searches'] += 1
        
        # Validate parameters
        validation_errors = search_params.validate()
        if validation_errors:
            raise ValueError(f"Invalid search parameters: {validation_errors}")
        
        # Attempt search with fallback mechanism
        try:
            result = await self._execute_search_with_fallback_target(search_params, original_target)
            self.search_stats['successful_searches'] += 1
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
        
        # Update performance statistics
        response_time = time.time() - start_time
        self._update_performance_stats(response_time)
        
        return result
    
    async def _execute_search_with_fallback_target(self, search_params: AdvancedSearchParams, 
                                                 original_target: int) -> SearchResult:
        """Execute search with fallback and original target."""
        fallback_used = None
        
        # Try advanced search first
        try:
            if self.unofficial_api_manager.features['advanced_sorting'].enabled:
                result = await self._advanced_search(search_params)
                self.unofficial_api_manager.record_feature_usage('advanced_sorting', True)
                return result
        except Exception as e:
            logger.warning(f"Advanced search failed: {e}")
            self.unofficial_api_manager.record_feature_usage('advanced_sorting', False)
            fallback_used = 'official_search'
        
        # Fallback to official search with original target
        try:
            result = await self._official_search(search_params, original_target)
            self.unofficial_api_manager.record_feature_usage('basic_search', True)
            if fallback_used:
                result.fallback_used = fallback_used
                self.search_stats['fallback_used'] += 1
            return result
        except Exception as e:
            if "connection" in str(e).lower() or "network" in str(e).lower():
                logger.error(f"Network error in official search: {e}")
                self.unofficial_api_manager.record_feature_usage('basic_search', False)
                raise NetworkError(f"Network error during search: {e}") from e
            else:
                logger.error(f"Official search failed: {e}")
                self.unofficial_api_manager.record_feature_usage('basic_search', False)
                raise SearchError(f"Search operation failed: {e}") from e
    
    async def search_streaming(self, search_params: AdvancedSearchParams, 
                             batch_size: int = 50):
        """
        Stream search results in batches for memory optimization.
        
        Args:
            search_params: Advanced search parameters
            batch_size: Number of models per batch
            
        Yields:
            SearchResult batches
        """
        logger.debug(f"search_streaming called with limit={search_params.limit}, batch_size={batch_size}")
        page = 1
        has_more = True
        total_yielded = 0
        original_limit = search_params.limit  # 元の目標数を保持
        logger.debug(f"search_streaming: original_limit={original_limit}")
        
        while has_more and total_yielded < original_limit:
            logger.debug(f"search_streaming loop: page={page}, has_more={has_more}, total_yielded={total_yielded}, original_limit={original_limit}")
            # Create paginated params (exclude page and limit to avoid conflicts)
            params_dict = search_params.__dict__.copy()
            params_dict.pop('page', None)
            params_dict.pop('limit', None)
            
            # 残り必要数を計算
            remaining_needed = original_limit - total_yielded
            current_batch_size = min(batch_size, remaining_needed)
            logger.debug(f"search_streaming: remaining_needed={remaining_needed}, current_batch_size={current_batch_size}")
            
            batch_params = AdvancedSearchParams(
                **params_dict,
                page=page,
                limit=current_batch_size
            )
            
            # Get batch (pass original target for proper filtering)
            logger.debug(f"search_streaming: calling _search_with_target with batch limit={current_batch_size}, target={original_limit}")
            result = await self._search_with_target(batch_params, original_limit)
            
            logger.debug(f"search_streaming: got result with {len(result.models)} models, has_next={result.has_next}")
            
            # Yield batch if has results
            if result.models:
                total_yielded += len(result.models)
                logger.debug(f"search_streaming: yielding {len(result.models)} models, total_yielded now {total_yielded}")
                yield result
            else:
                logger.debug("search_streaming: no models in result, not yielding")
            
            # Check if more pages and not reached limit
            # Fixed: Don't require exact batch size match - allow for last page with fewer results
            has_more = result.has_next and len(result.models) > 0 and total_yielded < original_limit
            logger.debug(f"search_streaming: has_more calculation: has_next={result.has_next}, models_count={len(result.models)}, total_yielded={total_yielded} < original_limit={original_limit} = {has_more}")
            page += 1
    
    async def _execute_search_with_fallback(self, search_params: AdvancedSearchParams) -> SearchResult:
        """Execute search with fallback per requirement 12.4."""
        fallback_used = None
        
        # Try advanced search first
        try:
            if self.unofficial_api_manager.features['advanced_sorting'].enabled:
                result = await self._advanced_search(search_params)
                self.unofficial_api_manager.record_feature_usage('advanced_sorting', True)
                return result
        except Exception as e:
            logger.warning(f"Advanced search failed: {e}")
            self.unofficial_api_manager.record_feature_usage('advanced_sorting', False)
            fallback_used = 'official_search'
        
        # Fallback to official search
        try:
            result = await self._official_search(search_params)
            self.unofficial_api_manager.record_feature_usage('basic_search', True)
            if fallback_used:
                result.fallback_used = fallback_used
                self.search_stats['fallback_used'] += 1
            return result
        except Exception as e:
            if "connection" in str(e).lower() or "network" in str(e).lower():
                logger.error(f"Network error in official search: {e}")
                self.unofficial_api_manager.record_feature_usage('basic_search', False)
                raise NetworkError(f"Network error during search: {e}") from e
            else:
                logger.error(f"Official search failed: {e}")
                self.unofficial_api_manager.record_feature_usage('basic_search', False)
                raise SearchError(f"Search operation failed: {e}") from e
    
    async def _advanced_search(self, search_params: AdvancedSearchParams) -> SearchResult:
        """Perform advanced search using unofficial API features."""
        # Convert to API parameters
        api_params = search_params.to_api_params()
        
        # Add custom sorting if enabled
        if search_params.custom_sort and self.unofficial_api_manager.features['advanced_sorting'].enabled:
            api_params['sort'] = search_params.custom_sort.value
        
        # Execute API call
        response = await self._execute_api_call(api_params)
        
        # Process results
        models = response.get('items', [])
        
        # Apply base model detection
        for model in models:
            detected_model = self.base_model_detector.detect_base_model(model)
            if detected_model:
                model['detected_base_model'] = detected_model
        
        # Apply triple filtering
        filtered_models, filter_stats = self.triple_filter.apply_triple_filter(models, search_params)
        
        # Apply post-processing filters
        filtered_models = self._apply_post_filters(filtered_models, search_params)
        
        return SearchResult(
            models=filtered_models,
            total_count=response.get('totalItems', len(models)),
            filtered_count=len(filtered_models),
            page=search_params.page,
            has_next=len(filtered_models) >= search_params.limit,
            search_metadata={
                'search_type': 'advanced',
                'api_params': api_params,
                'base_models_detected': len(self.base_model_detector.detected_models),
                'filter_stats': filter_stats
            },
            filter_applied={
                'categories': [cat.value for cat in search_params.categories] if search_params.categories else [],
                'tags': search_params.tags or [],
                'model_types': search_params.model_types or [],
                'file_format': search_params.file_format.value,
                'nsfw_filter': search_params.nsfw_filter.value
            }
        )
    
    async def _official_search(self, search_params: AdvancedSearchParams, 
                             original_target: Optional[int] = None) -> SearchResult:
        """Perform official search using only documented API features."""
        logger.debug(f"_official_search: search_params type: {type(search_params)}")
        logger.debug(f"_official_search: search_params: {search_params}")
        
        # Check database cache first
        cached_models = await self._check_db_cache(search_params)
        if cached_models:
            logger.debug(f"Using {len(cached_models)} cached models from database")
            return SearchResult(
                models=cached_models,
                total_count=len(cached_models),
                filtered_count=len(cached_models),
                page=search_params.page,
                has_next=False,
                search_metadata={
                    'search_type': 'cached',
                    'source': 'database',
                    'cache_hit': True
                },
                filter_applied={
                    'categories': [cat.value for cat in search_params.categories] if search_params.categories else [],
                    'tags': search_params.tags or [],
                    'model_types': search_params.model_types or [],
                    'base_model': search_params.base_model
                }
            )
        
        logger.debug("No suitable cache found, fetching from API")
        
        # Convert to basic API parameters (official only)
        api_params = {
            'limit': min(search_params.limit, 100)  # API max limit is 100
        }
        
        # Handle query and pagination (CivitAI API constraint)
        has_query = False
        if search_params.query:
            api_params['query'] = search_params.query
            has_query = True
        elif search_params.categories and not search_params.query:
            # Use "/" query like WebUI for category searches
            api_params['query'] = '/'
            has_query = True
        
        # Add page parameter only if no query (API constraint)
        if not has_query:
            api_params['page'] = search_params.page
        
        # Add model types (maps to 'types' parameter)
        if search_params.model_types:
            api_params['types'] = search_params.model_types
        
        # Handle categories: Always use local filtering for accuracy
        use_local_category_filter = False
        if search_params.categories:
            category_names = [cat.value for cat in search_params.categories]
            if len(category_names) == 1:
                # Single category: use API filter + local filter (double validation)
                api_params['category'] = category_names[0]
                use_local_category_filter = True  # Force local filtering for accuracy
                logger.debug(f"Using API category filter + local validation: {category_names[0]}")
            else:
                # Multiple categories: skip API filter, use local OR filter
                use_local_category_filter = True
                logger.debug(f"Multiple categories detected, using local OR filter: {category_names}")
        
        # Add base model parameter (critical for filtering)
        if search_params.base_model:
            api_params['baseModel'] = search_params.base_model
        
        # Add tags parameter
        if search_params.tags:
            # API supports multiple tags as comma-separated
            api_params['tag'] = ','.join(search_params.tags)
        
        # Use official sort options only
        if search_params.sort_option:
            api_params['sort'] = search_params.sort_option.value
        else:
            # Default to models_v9 like WebUI
            api_params['sort'] = 'Newest'
        
        logger.debug(f"Final API params: {api_params}")
        
        # Execute API call with appropriate pagination
        all_models = []
        # Use original_target if provided (for streaming), otherwise use search_params.limit
        target_limit = original_target if original_target else search_params.limit
        per_page_limit = min(100, max(search_params.limit, 50))  # API max is 100 per page, fetch at least 50 for filtering
        
        logger.debug(f"target_limit = {target_limit}, original_target = {original_target}, search_params.limit = {search_params.limit}")
        
        # Use cursor-based pagination for queries, page-based for non-queries
        if has_query:
            # Cursor-based pagination for queries
            cursor = None
            page_count = 0
            
            # Dynamic limit based on target - allow much more fetching when limit is specified
            max_pages = 99999 if target_limit > 100 else 10
            while len(all_models) < target_limit and page_count < max_pages:  # Dynamic safety limit
                current_api_params = api_params.copy()
                current_api_params['limit'] = min(per_page_limit, target_limit - len(all_models))
                
                if cursor:
                    current_api_params['cursor'] = cursor
                
                logger.debug(f"Fetching with cursor={cursor}, limit={current_api_params['limit']}")
                
                response = await self._execute_api_call(current_api_params)
                page_models = response.get('items', [])
                
                if not page_models:
                    logger.debug(f"No more models found with cursor {cursor}")
                    break
                
                all_models.extend(page_models)
                logger.debug(f"Got {len(page_models)} models, total: {len(all_models)}")
                
                # Get next cursor
                metadata = response.get('metadata', {})
                cursor = metadata.get('nextCursor')
                
                if not cursor:
                    logger.debug("No more cursors available")
                    break
                
                page_count += 1
        else:
            # Use cursor-based pagination for non-query searches when nextCursor is available
            cursor = None
            page_count = 0
            
            # Dynamic limit based on target - allow much more fetching when limit is specified
            max_pages = 99999 if target_limit > 1000 else 100
            while len(all_models) < target_limit and page_count < max_pages:  # Dynamic safety limit
                current_api_params = api_params.copy()
                current_api_params['limit'] = min(per_page_limit, target_limit - len(all_models))
                
                if cursor:
                    current_api_params['cursor'] = cursor
                    logger.debug(f"Fetching with cursor={cursor}, limit={current_api_params['limit']}")
                else:
                    current_api_params['page'] = search_params.page  # Only for first request
                    logger.debug(f"Fetching page {search_params.page} with limit {current_api_params['limit']}")
                
                response = await self._execute_api_call(current_api_params)
                page_models = response.get('items', [])
                
                if not page_models:
                    logger.debug(f"No more models found with cursor {cursor}")
                    break
                
                all_models.extend(page_models)
                logger.debug(f"Got {len(page_models)} models, total: {len(all_models)}")
                
                # Get next cursor
                metadata = response.get('metadata', {})
                next_cursor = metadata.get('nextCursor')
                
                logger.debug(f"Metadata: {metadata}")
                logger.debug(f"nextCursor: {next_cursor}")
                
                if not next_cursor:
                    logger.debug("No more cursors available")
                    break
                
                cursor = next_cursor
                page_count += 1
        
        logger.debug(f"Total models retrieved: {len(all_models)}")
        
        logger.debug(f"Initial API fetch completed: {len(all_models)} models")
        
        # Apply version-level filtering and continue fetching until target is reached
        if search_params.base_model or use_local_category_filter:
            filtered_models = []
            # Use the last cursor from pagination (both query and non-query)
            current_cursor = cursor
            
            # Process initial batch
            version_filter = LocalVersionFilter()
            batch_filtered, filter_stats = version_filter.filter_by_version_criteria(
                all_models, 
                base_model=search_params.base_model,
                model_types=search_params.model_types,
                categories=[cat.value for cat in search_params.categories] if use_local_category_filter else None
            )
            filtered_models.extend(batch_filtered)
            logger.debug(f"Initial batch filtered: {len(batch_filtered)} from {len(all_models)} models")
            
            # Continue fetching until we have enough filtered results or no more data
            additional_fetches = 0
            # Dynamic limit based on target - allow much more additional fetching when limit is specified
            max_additional_fetches = 999 if target_limit > 100 else 50
            while current_cursor and len(filtered_models) < target_limit and additional_fetches < max_additional_fetches:  # Continue until target is reached
                additional_fetches += 1
                needed = target_limit - len(filtered_models)
                fetch_size = min(100, max(50, needed * 2))  # Fetch extra to account for filtering
                
                logger.debug(f"Need {needed} more, fetching batch #{additional_fetches} (size: {fetch_size})")
                
                additional_params = api_params.copy()
                additional_params['cursor'] = current_cursor
                additional_params['limit'] = fetch_size
                
                try:
                    additional_response = await self._execute_api_call(additional_params)
                    additional_models = additional_response.get('items', [])
                    
                    if not additional_models:
                        break
                    
                    # Filter additional batch
                    additional_filtered, _ = version_filter.filter_by_version_criteria(
                        additional_models,
                        base_model=search_params.base_model,
                        model_types=search_params.model_types,
                        categories=[cat.value for cat in search_params.categories] if use_local_category_filter else None
                    )
                    
                    filtered_models.extend(additional_filtered)
                    logger.debug(f"Batch #{additional_fetches}: +{len(additional_filtered)} filtered (total: {len(filtered_models)})")
                    
                    # Update cursor
                    additional_metadata = additional_response.get('metadata', {})
                    current_cursor = additional_metadata.get('nextCursor')
                    
                    if not current_cursor:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error in additional fetch: {e}")
                    break
            
            logger.debug(f"Final result: {len(filtered_models)} models after filtering (requested: {target_limit})")
        else:
            filtered_models = all_models
            logger.debug(f"No base model filtering, using all {len(filtered_models)} models")
        
        # Cache results to database for future use
        self._cache_models_to_db(filtered_models, search_params)
        
        # Update cache metadata
        try:
            from ...data.optimized_schema import OptimizedDatabase
            db = OptimizedDatabase('data/civitai.db')
            cache_key = self._generate_cache_key(search_params)
            self._update_cache_info(db, cache_key, filtered_models)
        except Exception as e:
            self.logger.warning(f"Cache metadata update failed: {e}")
        
        logger.debug(f"Returning all filtered models: {len(filtered_models)}")
        
        # Determine if more data is available
        # For streaming: if we got a full batch and there's an overall target, continue
        overall_target = original_target if original_target else search_params.limit
        batch_is_full = len(filtered_models) >= search_params.limit
        within_overall_limit = overall_target > search_params.limit
        
        logger.debug(f"has_next calculation: overall_target={overall_target}, batch_is_full={batch_is_full}, within_overall_limit={within_overall_limit}, final_has_next={batch_is_full and within_overall_limit}")
        
        return SearchResult(
            models=filtered_models,
            total_count=len(all_models),
            filtered_count=len(filtered_models),
            page=search_params.page,
            has_next=batch_is_full and within_overall_limit,  # Continue if batch is full and overall target is larger
            search_metadata={
                'search_type': 'official',
                'api_params': api_params,
                'client_side_filtering': True,
                'pagination_type': 'cursor' if has_query else 'page',
                'raw_models_count': len(all_models)
            },
            filter_applied={
                'categories': [cat.value for cat in search_params.categories] if search_params.categories else [],
                'tags': search_params.tags or [],
                'model_types': search_params.model_types or [],
                'base_model': search_params.base_model
            }
        )
    
    def _cache_models_to_db(self, models: List[Dict[str, Any]], search_params: AdvancedSearchParams) -> None:
        """Cache retrieved models to database for future use."""
        try:
            # Import database here to avoid circular imports
            from ...data.optimized_schema import OptimizedDatabase
            
            db = OptimizedDatabase('data/civitai.db')
            cached_count = 0
            
            for model in models:
                try:
                    # Store model data in database
                    db.store_model(model)
                    cached_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to cache model {model.get('id', 'unknown')}: {e}")
            
            logger.debug(f"Cached {cached_count}/{len(models)} models to database")
            
        except Exception as e:
            self.logger.warning(f"Database caching failed: {e}")
    
    async def _check_db_cache(self, search_params: AdvancedSearchParams) -> Optional[List[Dict[str, Any]]]:
        """Check if results are available in database cache with freshness validation."""
        try:
            from ...data.optimized_schema import OptimizedDatabase
            import time
            
            db = OptimizedDatabase('data/civitai.db')
            
            # Check cache freshness (24 hours)
            cache_key = self._generate_cache_key(search_params)
            cache_info = self._get_cache_info(db, cache_key)
            
            if cache_info:
                cache_age_hours = (time.time() - cache_info['timestamp']) / 3600
                logger.debug(f"Cache found, age: {cache_age_hours:.1f} hours")
                
                if cache_age_hours > 24:
                    logger.debug("Cache expired (>24h), will refresh from API")
                    return None
                elif cache_age_hours > 6 and await self._has_new_models_since(search_params, cache_info['latest_model_id']):
                    logger.debug("New models detected, refreshing cache")
                    return None
            
            # Query database for matching models
            cached_models = db.search_models(
                base_model=search_params.base_model,
                model_types=search_params.model_types,
                categories=[cat.value for cat in search_params.categories] if search_params.categories else None,
                limit=search_params.limit
            )
            
            if cached_models and len(cached_models) >= search_params.limit:
                logger.debug(f"Using {len(cached_models)} fresh cached models")
                return cached_models
                
        except Exception as e:
            self.logger.warning(f"Database cache check failed: {e}")
        
        return None
    
    def _generate_cache_key(self, search_params: AdvancedSearchParams) -> str:
        """Generate unique cache key for search parameters."""
        key_parts = [
            search_params.base_model or '',
            ','.join(search_params.model_types or []),
            ','.join([cat.value for cat in search_params.categories] if search_params.categories else []),
            ','.join(search_params.tags or [])
        ]
        return '|'.join(key_parts)
    
    def _get_cache_info(self, db, cache_key: str) -> Optional[Dict]:
        """Get cache metadata from database."""
        try:
            cursor = db.connection.cursor()
            cursor.execute("""
                SELECT timestamp, latest_model_id, model_count 
                FROM search_cache 
                WHERE cache_key = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (cache_key,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'timestamp': row[0],
                    'latest_model_id': row[1],
                    'model_count': row[2]
                }
        except Exception as e:
            self.logger.debug(f"Cache info retrieval failed: {e}")
        
        return None
    
    async def _has_new_models_since(self, search_params: AdvancedSearchParams, latest_cached_id: str) -> bool:
        """Check if new models exist since last cache update."""
        try:
            # Fetch only the latest model to check for updates
            api_params = {
                'limit': 1,
                'query': search_params.query or '/',
                'types': search_params.model_types,
                'category': search_params.categories[0].value if search_params.categories else None,
                'baseModel': search_params.base_model,
                'sort': 'Newest'  # Get the most recent
            }
            
            logger.debug("Checking for new models (1 API request)")
            response = await self._execute_api_call(api_params)
            latest_models = response.get('items', [])
            
            if latest_models:
                latest_api_id = str(latest_models[0].get('id', ''))
                is_newer = latest_api_id != latest_cached_id
                logger.debug(f"Latest API ID: {latest_api_id}, Cached ID: {latest_cached_id}, New: {is_newer}")
                return is_newer
                
        except Exception as e:
            self.logger.warning(f"New model check failed: {e}")
            # If check fails, assume there might be new models (safe side)
            return True
        
        return False
    
    def _update_cache_info(self, db, cache_key: str, models: List[Dict[str, Any]]) -> None:
        """Update cache metadata in database."""
        try:
            import time
            
            latest_model_id = str(models[0].get('id', '')) if models else ''
            timestamp = time.time()
            
            # Create table if not exists
            cursor = db.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT,
                    timestamp REAL,
                    latest_model_id TEXT,
                    model_count INTEGER,
                    PRIMARY KEY (cache_key)
                )
            """)
            
            # Insert or update cache info
            cursor.execute("""
                INSERT OR REPLACE INTO search_cache 
                (cache_key, timestamp, latest_model_id, model_count)
                VALUES (?, ?, ?, ?)
            """, (cache_key, timestamp, latest_model_id, len(models)))
            
            db.connection.commit()
            logger.debug(f"Updated cache info for key: {cache_key}")
            
        except Exception as e:
            self.logger.warning(f"Cache info update failed: {e}")
    
    
    
    
    async def _execute_api_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call with error handling and rate limiting."""
        logger.debug(f"_execute_api_call: params type: {type(params)}")
        logger.debug(f"_execute_api_call: params: {params}")
        
        if not self.api_client:
            raise ValueError("API client not configured")
        
        # Rate limiting: wait between requests to avoid being banned
        import time
        
        # Check if we need to wait (minimum 1 second between requests)
        current_time = time.time()
        if hasattr(self, '_last_api_call_time'):
            time_since_last = current_time - self._last_api_call_time
            if time_since_last < 1.0:
                wait_time = 1.0 - time_since_last
                logger.debug(f"Rate limiting - waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self._last_api_call_time = time.time()
        
        # Retry logic for network errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.api_client.get_models(params)
                
                # Detect API capabilities if enabled
                if self.unofficial_api_manager.feature_detection_enabled:
                    self.unofficial_api_manager.detect_api_capabilities(response)
                
                return response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                    logger.debug(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    
    def _update_performance_stats(self, response_time: float) -> None:
        """Update search performance statistics."""
        total = self.search_stats['total_searches']
        current_avg = self.search_stats['avg_response_time']
        
        # Calculate new average
        new_avg = ((current_avg * (total - 1)) + response_time) / total
        self.search_stats['avg_response_time'] = new_avg
        self.search_stats['last_search_time'] = time.time()
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search statistics."""
        return {
            'search_performance': dict(self.search_stats),
            'unofficial_api_stats': self.unofficial_api_manager.get_usage_statistics(),
            'base_model_detection': {
                'known_models': len(self.base_model_detector.known_models),
                'detected_models': len(self.base_model_detector.detected_models),
                'all_models': self.base_model_detector.get_all_detected_models()
            },
            'filter_statistics': {}
        }
    
    def configure_unofficial_features(self, enable_advanced: bool = False, 
                                    risk_tolerance: str = 'low') -> None:
        """Configure unofficial API features per requirement 12.1."""
        risk_levels = {
            'low': ['LOW'],
            'medium': ['LOW', 'MEDIUM'],
            'high': ['LOW', 'MEDIUM', 'HIGH'],
            'critical': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        }
        
        allowed_risks = risk_levels.get(risk_tolerance, ['LOW'])
        
        for feature_name, feature in self.unofficial_api_manager.features.items():
            if feature.risk_level.value.upper() in allowed_risks:
                if enable_advanced or feature.official:
                    self.unofficial_api_manager.enable_feature(feature_name)
    
    async def search_with_category_tags_types(self, categories: List[str], 
                                            tags: List[str], 
                                            model_types: List[str],
                                            **kwargs) -> SearchResult:
        """
        Convenience method for triple filtering per requirement 11.2.
        
        Args:
            categories: List of category names
            tags: List of tag names
            model_types: List of model types
            **kwargs: Additional search parameters
            
        Returns:
            SearchResult with triple filtering applied
        """
        # Convert category names to enums
        category_enums = []
        for cat_name in categories:
            try:
                category_enums.append(ModelCategory(cat_name.lower()))
            except ValueError:
                logger.warning(f"Unknown category: {cat_name}")
        
        # Create search parameters
        search_params = AdvancedSearchParams(
            categories=category_enums,
            tags=tags,
            model_types=model_types,
            **kwargs
        )
        
        return await self.search(search_params)


class LocalVersionFilter:
    """
    ローカルフィルタリングシステム - APIレスポンス後のバージョンレベルフィルタリング
    CivitAI APIはモデル単位でフィルタリングするため、バージョンレベルでの厳密なフィルタリングはローカルで実行
    """
    
    def __init__(self):
        """Initialize version filter."""
        self.filter_stats = {
            'models_processed': 0,
            'models_removed': 0,
            'versions_processed': 0,
            'versions_removed': 0,
            'base_model_filtered': 0,
            'type_filtered': 0
        }
    
    def filter_by_version_criteria(self, models: List[Dict[str, Any]], 
                                 base_model: Optional[str] = None,
                                 model_types: Optional[List[str]] = None,
                                 categories: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        バージョンレベルでの厳密フィルタリング
        
        Args:
            models: CivitAI APIから取得したモデルリスト
            base_model: 必要なベースモデル (例: "Illustrious")
            model_types: 必要なモデルタイプリスト (例: ["LORA"])
            categories: 必要なカテゴリリスト (例: ["style"])
            
        Returns:
            フィルタリング済みモデルリストと統計情報のタプル
        """
        self.filter_stats = {
            'models_processed': 0,
            'models_removed': 0,
            'versions_processed': 0,
            'versions_removed': 0,
            'base_model_filtered': 0,
            'type_filtered': 0,
            'category_filtered': 0
        }
        
        filtered_models = []
        
        for model in models:
            self.filter_stats['models_processed'] += 1
            original_versions = model.get('modelVersions', [])
            filtered_versions = []
            for version in original_versions:
                self.filter_stats['versions_processed'] += 1
                should_include = True
                
                # ベースモデルフィルタリング
                if base_model:
                    version_base_model = version.get('baseModel', '')
                    if version_base_model != base_model:
                        should_include = False
                        self.filter_stats['base_model_filtered'] += 1
                
                # モデルタイプフィルタリング（モデル単位でチェック）
                if model_types and should_include:
                    model_type = model.get('type', '')
                    if model_type not in model_types:
                        should_include = False
                        self.filter_stats['type_filtered'] += 1
                
                # カテゴリフィルタリング（モデル単位でチェック - OR ロジック）
                if categories and should_include:
                    model_tags = model.get('tags', [])
                    # タグの中にカテゴリが含まれているかチェック
                    model_categories = []
                    for tag in model_tags:
                        if isinstance(tag, dict):
                            tag_name = tag.get('name', '').lower()
                        else:
                            tag_name = str(tag).lower()
                        model_categories.append(tag_name)
                    
                    # OR検索: 指定されたカテゴリのいずれかがモデルのタグに含まれているかチェック
                    category_found = any(cat.lower() in model_categories for cat in categories)
                    if not category_found:
                        should_include = False
                        self.filter_stats['category_filtered'] += 1
                
                if should_include:
                    filtered_versions.append(version)
                else:
                    self.filter_stats['versions_removed'] += 1
            
            # フィルタリング後にバージョンが残っている場合のみモデルを含める
            if filtered_versions:
                filtered_model = model.copy()
                filtered_model['modelVersions'] = filtered_versions
                filtered_models.append(filtered_model)
            else:
                self.filter_stats['models_removed'] += 1
        
        return filtered_models, dict(self.filter_stats)
    
    def print_filter_statistics(self, stats: Dict[str, int]) -> None:
        """フィルタリング統計情報を表示"""
        print("\n📊 ローカルフィルタリング統計:")
        print(f"  処理されたモデル: {stats['models_processed']}")
        print(f"  除外されたモデル: {stats['models_removed']}")
        print(f"  残存モデル: {stats['models_processed'] - stats['models_removed']}")
        print(f"  処理されたバージョン: {stats['versions_processed']}")
        print(f"  除外されたバージョン: {stats['versions_removed']}")
        print(f"    ├─ ベースモデル不適合: {stats['base_model_filtered']}")
        print(f"    ├─ タイプ不適合: {stats['type_filtered']}")
        print(f"    └─ カテゴリ不適合: {stats.get('category_filtered', 0)}")
        print(f"  残存バージョン: {stats['versions_processed'] - stats['versions_removed']}")