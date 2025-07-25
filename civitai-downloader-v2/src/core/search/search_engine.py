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

logger = logging.getLogger(__name__)


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


class TripleFilterEngine:
    """
    Triple filtering system per requirement 11.2.
    Implements Category × Tag × Model Type filtering.
    """
    
    def __init__(self, security_scanner: Optional[SecurityScanner] = None):
        """Initialize triple filter engine."""
        self.security_scanner = security_scanner or SecurityScanner()
        self.filter_stats = {
            'category_filtered': 0,
            'tag_filtered': 0,
            'type_filtered': 0,
            'security_filtered': 0,
            'total_processed': 0
        }
    
    def apply_triple_filter(self, models: List[Dict[str, Any]], 
                          search_params: AdvancedSearchParams) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Apply category × tag × model type filtering per requirement 11.2.
        
        Args:
            models: List of models to filter
            search_params: Search parameters with filter criteria
            
        Returns:
            Tuple of (filtered_models, filter_statistics)
        """
        self.filter_stats['total_processed'] = len(models)
        filtered_models = models.copy()
        
        # Step 1: Category filtering
        if search_params.categories:
            before_count = len(filtered_models)
            filtered_models = self._filter_by_categories(filtered_models, search_params.categories)
            self.filter_stats['category_filtered'] = before_count - len(filtered_models)
        
        # Step 2: Tag filtering
        if search_params.tags:
            before_count = len(filtered_models)
            filtered_models = self._filter_by_tags(filtered_models, search_params.tags)
            self.filter_stats['tag_filtered'] = before_count - len(filtered_models)
        
        # Step 3: Model type filtering
        if search_params.model_types:
            before_count = len(filtered_models)
            filtered_models = self._filter_by_types(filtered_models, search_params.model_types)
            self.filter_stats['type_filtered'] = before_count - len(filtered_models)
        
        # Step 4: Security filtering (if file format specified)
        if search_params.file_format != FileFormat.ALL_FORMATS:
            before_count = len(filtered_models)
            filtered_models = self._filter_by_security(filtered_models, search_params.file_format)
            self.filter_stats['security_filtered'] = before_count - len(filtered_models)
        
        return filtered_models, dict(self.filter_stats)
    
    def _filter_by_categories(self, models: List[Dict[str, Any]], 
                            categories: List[ModelCategory]) -> List[Dict[str, Any]]:
        """Filter models by categories (integrated into tag system per requirement 11.5)."""
        category_names = {cat.value.lower() for cat in categories}
        filtered = []
        
        for model in models:
            model_tags = self._extract_model_tags(model)
            model_categories = {tag.lower() for tag in model_tags if tag.lower() in category_names}
            
            # Model passes if it has any of the specified categories
            if model_categories:
                filtered.append(model)
        
        return filtered
    
    def _filter_by_tags(self, models: List[Dict[str, Any]], 
                       tags: List[str]) -> List[Dict[str, Any]]:
        """Filter models by tags."""
        target_tags = {tag.lower() for tag in tags}
        filtered = []
        
        for model in models:
            model_tags = {tag.lower() for tag in self._extract_model_tags(model)}
            
            # Model passes if it has any of the specified tags
            if target_tags.intersection(model_tags):
                filtered.append(model)
        
        return filtered
    
    def _filter_by_types(self, models: List[Dict[str, Any]], 
                        model_types: List[str]) -> List[Dict[str, Any]]:
        """Filter models by type."""
        target_types = {t.lower() for t in model_types}
        filtered = []
        
        for model in models:
            model_type = model.get('type', '').lower()
            if model_type in target_types:
                filtered.append(model)
        
        return filtered
    
    def _filter_by_security(self, models: List[Dict[str, Any]], 
                          file_format: FileFormat) -> List[Dict[str, Any]]:
        """Filter models by security requirements per requirement 10.6."""
        filtered = []
        
        for model in models:
            # Get model files
            files = []
            for version in model.get('modelVersions', []):
                files.extend(version.get('files', []))
            
            if not files:
                continue
            
            # Apply file format filtering
            safe_files = []
            for file_info in files:
                file_name = file_info.get('name', '').lower()
                
                if file_format == FileFormat.SAFETENSORS_ONLY:
                    if file_name.endswith('.safetensors'):
                        safe_files.append(file_info)
                elif file_format == FileFormat.PICKLE_ALLOWED:
                    # Allow both safetensors and pickle, but prefer safetensors
                    if file_name.endswith(('.safetensors', '.ckpt', '.pt', '.pth')):
                        safe_files.append(file_info)
                else:  # ALL_FORMATS
                    safe_files.append(file_info)
            
            # Only include models with acceptable files
            if safe_files:
                # Perform security scan on primary file
                primary_file = safe_files[0]
                scan_result = self.security_scanner.perform_security_scan(primary_file)
                
                # Include if file is safe or format allows risky files
                if scan_result.is_safe() or file_format == FileFormat.ALL_FORMATS:
                    # Add security metadata to model
                    model['security_scan'] = scan_result.to_dict()
                    model['safe_files'] = safe_files
                    filtered.append(model)
        
        return filtered
    
    def _extract_model_tags(self, model: Dict[str, Any]) -> List[str]:
        """Extract all tags from model data."""
        tags = []
        
        # Direct tags
        for tag in model.get('tags', []):
            if isinstance(tag, dict):
                tags.append(tag.get('name', ''))
            else:
                tags.append(str(tag))
        
        # Category as tag (per requirement 11.5)
        if 'category' in model:
            tags.append(model['category'])
        
        # Version tags
        for version in model.get('modelVersions', []):
            for tag in version.get('tags', []):
                if isinstance(tag, dict):
                    tags.append(tag.get('name', ''))
                else:
                    tags.append(str(tag))
        
        return [tag for tag in tags if tag]


class AdvancedSearchEngine:
    """
    Advanced search engine implementing requirements 10-12.
    Provides comprehensive search with filtering, sorting, and fallback mechanisms.
    """
    
    def __init__(self, api_client=None, client=None, db_manager=None):
        """
        Initialize advanced search engine.
        
        Args:
            api_client: API client (legacy parameter)
            client: API client (preferred parameter for integration tests)
            db_manager: Database manager for storing search results
        """
        # Support both api_client and client parameters for backward compatibility
        self.api_client = client or api_client
        self.client = self.api_client  # Alias for integration test compatibility
        self.db_manager = db_manager
        
        self.base_model_detector = BaseModelDetector()
        self.unofficial_api_manager = UnofficialAPIManager()
        self.triple_filter = TripleFilterEngine()
        self.license_manager = LicenseManager()
        
        # Search performance tracking
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'fallback_used': 0,
            'avg_response_time': 0.0,
            'last_search_time': None
        }
    
    async def search(self, search_params: AdvancedSearchParams = None, query: str = None, filters: Dict[str, Any] = None) -> Union[SearchResult, List[Dict[str, Any]]]:
        """
        Perform advanced search with comprehensive filtering.
        
        Args:
            search_params: Advanced search parameters (preferred)
            query: Search query string (integration test compatibility)
            filters: Search filters dict (integration test compatibility)
            
        Returns:
            SearchResult when using search_params, List[Dict] when using query/filters for integration test compatibility
        """
        # Support both parameter formats for integration test compatibility
        if search_params is None:
            # Create AdvancedSearchParams from query and filters
            search_params = AdvancedSearchParams(
                query=query or "",
                model_types=filters.get('types', []) if filters else [],
                # Map nsfw filter
                nsfw_filter=NSFWFilter.SFW_ONLY if (filters and not filters.get('nsfw', True)) else NSFWFilter.INCLUDE_ALL,
                # Default values for other parameters
                page=1,
                limit=50
            )
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
        
        # For integration test compatibility, return just the models list
        # when called with query/filters parameters instead of search_params
        if query is not None or filters is not None:
            return result.models
        else:
            return result
    
    async def search_models_list(self, query: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Integration test compatible method that always returns models list.
        
        Args:
            query: Search query string
            filters: Search filters dict
            
        Returns:
            List of model dictionaries
        """
        result = await self.search(query=query, filters=filters)
        return result  # This will be List[Dict] due to the query/filters path
    
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
        page = 1
        has_more = True
        
        while has_more:
            # Create paginated params
            batch_params = AdvancedSearchParams(
                **search_params.__dict__,
                page=page,
                limit=min(batch_size, search_params.limit)
            )
            
            # Get batch
            result = await self.search(batch_params)
            
            # Yield batch if has results
            if result.models:
                yield result
            
            # Check if more pages
            has_more = result.has_next and len(result.models) == batch_size
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
            logger.error(f"Official search failed: {e}")
            self.unofficial_api_manager.record_feature_usage('basic_search', False)
            raise
    
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
    
    async def _official_search(self, search_params: AdvancedSearchParams) -> SearchResult:
        """Perform official search using only documented API features."""
        # Convert to basic API parameters (official only)
        api_params = {
            'limit': min(search_params.limit, 200),
            'page': search_params.page
        }
        
        if search_params.query:
            api_params['query'] = search_params.query
        
        if search_params.model_types:
            api_params['types'] = search_params.model_types
        
        # Use official sort options only
        if search_params.sort_option:
            api_params['sort'] = search_params.sort_option.value
        
        # Execute API call
        response = await self._execute_api_call(api_params)
        
        # Process results
        models = response.get('items', [])
        
        # Apply client-side filtering (since we can't use advanced API params)
        filtered_models = self._apply_client_side_filters(models, search_params)
        
        return SearchResult(
            models=filtered_models,
            total_count=response.get('totalItems', len(models)),
            filtered_count=len(filtered_models),
            page=search_params.page,
            has_next=len(filtered_models) >= search_params.limit,
            search_metadata={
                'search_type': 'official',
                'api_params': api_params,
                'client_side_filtering': True
            },
            filter_applied={
                'categories': [cat.value for cat in search_params.categories] if search_params.categories else [],
                'tags': search_params.tags or [],
                'model_types': search_params.model_types or []
            }
        )
    
    def _apply_client_side_filters(self, models: List[Dict[str, Any]], 
                                 search_params: AdvancedSearchParams) -> List[Dict[str, Any]]:
        """Apply client-side filtering when API parameters aren't available."""
        filtered = models.copy()
        
        # Apply download range filter
        if search_params.download_range:
            filtered = search_params.download_range.to_filter(filtered)
        
        # Apply NSFW filter
        if search_params.nsfw_filter != NSFWFilter.INCLUDE_ALL:
            filtered = self._filter_nsfw_content(filtered, search_params.nsfw_filter)
        
        # Apply quality filters
        if search_params.quality_filter.value != 'all':
            filtered = self._filter_by_quality(filtered, search_params.quality_filter)
        
        # Apply commercial filter
        if search_params.commercial_filter.value != 'all':
            filtered = self._filter_by_commercial_use(filtered, search_params.commercial_filter)
        
        # Apply triple filtering
        filtered, _ = self.triple_filter.apply_triple_filter(filtered, search_params)
        
        return filtered
    
    def _apply_post_filters(self, models: List[Dict[str, Any]], 
                          search_params: AdvancedSearchParams) -> List[Dict[str, Any]]:
        """Apply post-processing filters."""
        filtered = models.copy()
        
        # Apply license filtering if commercial use is specified
        if search_params.commercial_filter.value == 'commercial':
            filtered = self.license_manager.filter_commercial_models(filtered)
        
        # Apply base model filtering
        if search_params.base_model:
            filtered = self._filter_by_base_model(filtered, search_params.base_model)
        
        return filtered
    
    def _filter_nsfw_content(self, models: List[Dict[str, Any]], 
                           nsfw_filter: NSFWFilter) -> List[Dict[str, Any]]:
        """Filter NSFW content per requirement 10.3."""
        if nsfw_filter == NSFWFilter.INCLUDE_ALL:
            return models
        
        filtered = []
        for model in models:
            is_nsfw = model.get('nsfw', False)
            
            if nsfw_filter == NSFWFilter.SFW_ONLY and not is_nsfw:
                filtered.append(model)
            elif nsfw_filter == NSFWFilter.NSFW_ONLY and is_nsfw:
                filtered.append(model)
            elif nsfw_filter == NSFWFilter.MATURE:
                # Include mature content but not explicit NSFW
                nsfw_level = model.get('nsfwLevel', 0)
                if nsfw_level <= 2:  # Assuming 0=SFW, 1=Suggestive, 2=Mature, 3+=Explicit
                    filtered.append(model)
        
        return filtered
    
    def _filter_by_quality(self, models: List[Dict[str, Any]], 
                         quality_filter) -> List[Dict[str, Any]]:
        """Filter by model quality per requirement 10.4."""
        filtered = []
        
        for model in models:
            is_verified = model.get('verified', False)
            is_featured = model.get('featured', False)
            
            if quality_filter.value == 'verified' and is_verified:
                filtered.append(model)
            elif quality_filter.value == 'featured' and is_featured:
                filtered.append(model)
            elif quality_filter.value == 'verified_featured' and is_verified and is_featured:
                filtered.append(model)
            elif quality_filter.value == 'all':
                filtered.append(model)
        
        return filtered
    
    def _filter_by_commercial_use(self, models: List[Dict[str, Any]], 
                                commercial_filter) -> List[Dict[str, Any]]:
        """Filter by commercial use per requirement 10.5."""
        if commercial_filter.value == 'all':
            return models
        
        filtered = []
        for model in models:
            commercial_allowed = model.get('allowCommercialUse', None)
            
            if commercial_filter.value == 'commercial' and commercial_allowed is True:
                filtered.append(model)
            elif commercial_filter.value == 'non_commercial' and commercial_allowed is False:
                filtered.append(model)
        
        return filtered
    
    def _filter_by_base_model(self, models: List[Dict[str, Any]], 
                            base_model: str) -> List[Dict[str, Any]]:
        """Filter by base model per requirement 11.6."""
        filtered = []
        base_model_lower = base_model.lower()
        
        for model in models:
            # Check explicit base model
            model_base = model.get('baseModel', '').lower()
            detected_base = model.get('detected_base_model', '').lower()
            
            if base_model_lower in model_base or base_model_lower in detected_base:
                filtered.append(model)
        
        return filtered
    
    async def _execute_api_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call with error handling."""
        if not self.api_client:
            raise ValueError("API client not configured")
        
        # Add rate limiting and retry logic here
        # Integration test compatibility: try sync call first, then async
        try:
            response = self.api_client.search_models(params)
            # If response is a coroutine, await it
            if hasattr(response, '__await__'):
                response = await response
        except Exception:
            # Fallback to pure async call
            response = await self.api_client.search_models(params)
        
        # Detect API capabilities if enabled
        if self.unofficial_api_manager.feature_detection_enabled:
            self.unofficial_api_manager.detect_api_capabilities(response)
        
        return response
    
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
            'filter_statistics': dict(self.triple_filter.filter_stats)
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
                                 model_types: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        バージョンレベルでの厳密フィルタリング
        
        Args:
            models: CivitAI APIから取得したモデルリスト
            base_model: 必要なベースモデル (例: "Illustrious")
            model_types: 必要なモデルタイプリスト (例: ["LORA"])
            
        Returns:
            フィルタリング済みモデルリストと統計情報のタプル
        """
        self.filter_stats = {
            'models_processed': 0,
            'models_removed': 0,
            'versions_processed': 0,
            'versions_removed': 0,
            'base_model_filtered': 0,
            'type_filtered': 0
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
        print(f"    └─ タイプ不適合: {stats['type_filtered']}")
        print(f"  残存バージョン: {stats['versions_processed'] - stats['versions_removed']}")