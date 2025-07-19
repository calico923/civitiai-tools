"""
SearchStrategy - Abstract interface for search strategies.

This module defines the abstract base class for implementing different search strategies
for discovering models on Civitai. Supports both synchronous and asynchronous operations.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchParams:
    """Search parameters for model discovery."""
    query: Optional[str] = None
    types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    base_models: Optional[List[str]] = None
    sort: Optional[str] = None
    period: Optional[str] = None
    nsfw: Optional[bool] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    cursor: Optional[str] = None


@dataclass 
class SearchResult:
    """Result from a search operation."""
    models: List[Dict[str, Any]]
    total_count: int
    has_next: bool
    next_cursor: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchStrategy(ABC):
    """
    Abstract base class for search strategies.
    
    This interface defines the contract for implementing different search strategies
    to discover models on Civitai. Implementations should handle different search
    approaches like direct tag search, base model filtering, category-based search, etc.
    """
    
    @abstractmethod
    async def search(self, params: SearchParams) -> AsyncIterator[SearchResult]:
        """
        Execute search with given parameters.
        
        Args:
            params: Search parameters specifying the search criteria
            
        Returns:
            AsyncIterator yielding SearchResult objects with discovered models
            
        Raises:
            SearchError: If search execution fails
            ValidationError: If search parameters are invalid
        """
        pass
    
    @abstractmethod
    def validate_params(self, params: SearchParams) -> bool:
        """
        Validate search parameters for this strategy.
        
        Args:
            params: Search parameters to validate
            
        Returns:
            True if parameters are valid for this strategy
            
        Raises:
            ValidationError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of this search strategy.
        
        Returns:
            String identifier for this strategy
        """
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        Check if this strategy supports streaming results.
        
        Returns:
            True if strategy can stream results for memory efficiency
        """
        pass