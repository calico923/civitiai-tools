#!/usr/bin/env python3
"""
Advanced Search module for CivitAI Downloader.
Implements requirements 10-12: Advanced search parameters, categories, and unofficial API management.
"""

# Legacy search components
from .strategy import (
    SearchStrategy,
    SearchFilters,
    SearchMetadata,
    ModelType,
    SortOrder,
    Period,
    search_checkpoints,
    search_loras,
    search_by_creator
)

# Phase 5 advanced search components
from .advanced_search import (
    AdvancedSearchParams,
    BaseModelDetector,
    UnofficialAPIManager,
    DateRange,
    DownloadRange,
    NSFWFilter,
    ModelQuality,
    CommercialUse,
    FileFormat,
    ModelCategory,
    SortOption,
    CustomSortMetric,
    RiskLevel,
    APIFeature
)

from .search_engine import (
    AdvancedSearchEngine,
    SearchResult
)

__all__ = [
    # Legacy components
    'SearchStrategy',
    'SearchFilters', 
    'SearchMetadata',
    'ModelType',
    'SortOrder',
    'Period',
    'search_checkpoints',
    'search_loras',
    'search_by_creator',
    
    # Phase 5 advanced search parameters
    'AdvancedSearchParams',
    'DateRange',
    'DownloadRange',
    
    # Filtering enums
    'NSFWFilter',
    'ModelQuality',
    'CommercialUse',
    'FileFormat',
    'ModelCategory',
    
    # Sorting options
    'SortOption',
    'CustomSortMetric',
    
    # API management
    'UnofficialAPIManager',
    'APIFeature',
    'RiskLevel',
    
    # Base model detection
    'BaseModelDetector',
    
    # Search engine
    'AdvancedSearchEngine',
    'SearchResult'
]