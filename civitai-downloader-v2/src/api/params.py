#!/usr/bin/env python3
"""
Search Parameters for CivitAI API requests.
Provides data classes for managing search parameters and advanced filters.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ModelType(Enum):
    """Model types supported by CivitAI per requirements.md requirement 1.2."""
    CHECKPOINT = "Checkpoint"
    LORA = "LORA"
    LOCON = "LoCon"
    DORA = "DoRA"
    TEXTUALINVERSION = "TextualInversion"
    HYPERNETWORK = "Hypernetwork"
    AESTHETICGRADIENT = "AestheticGradient"
    CONTROLNET = "Controlnet"
    POSES = "Poses"
    WILDCARDS = "Wildcards"
    WORKFLOWS = "Workflows"
    OTHER = "Other"
    VAE = "VAE"


@dataclass
class SearchParams:
    """Basic search parameters for CivitAI API."""
    
    query: Optional[str] = None
    types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    sort: Optional[str] = None
    period: Optional[str] = None
    nsfw: Optional[bool] = None
    base_models: Optional[List[str]] = None  # Support 50+ base models per requirement 1.3
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, excluding None values.
        
        Returns:
            Dictionary representation of parameters
        """
        params = {}
        for key, value in asdict(self).items():
            if value is not None:
                params[key] = value
        return params
    
    def to_api_params(self) -> Dict[str, Any]:
        """
        Convert to CivitAI API parameters with correct parameter names.
        
        Returns:
            Dictionary with API-compatible parameter names
        """
        params = {}
        
        # Basic parameters
        if self.query is not None:
            params['query'] = self.query
        
        if self.tags is not None:
            params['tags'] = self.tags
        
        if self.limit is not None:
            params['limit'] = self.limit
            
        if self.page is not None:
            params['page'] = self.page
            
        if self.sort is not None:
            params['sort'] = self.sort
            
        if self.period is not None:
            params['period'] = self.period
            
        if self.nsfw is not None:
            params['nsfw'] = self.nsfw
            
        if self.base_models is not None:
            params['baseModels'] = self.base_models
        
        # Use types parameter for CivitAI API compatibility
        if self.types is not None:
            params['types'] = self.types
        
        return params


@dataclass
class AdvancedFilters:
    """Advanced filtering parameters for CivitAI API."""
    
    min_downloads: Optional[int] = None
    max_downloads: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    nsfw: Optional[bool] = None
    featured: Optional[bool] = None
    verified: Optional[bool] = None
    commercial: Optional[bool] = None
    base_models: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, excluding None values and formatting dates.
        
        Returns:
            Dictionary representation of filters
        """
        filters = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, datetime):
                    # Format datetime for API
                    filters[key] = value.isoformat()
                else:
                    filters[key] = value
        return filters
    
    def merge_with_params(self, params: SearchParams) -> Dict[str, Any]:
        """
        Merge advanced filters with basic search parameters.
        
        Args:
            params: Basic search parameters
            
        Returns:
            Combined parameters dictionary
        """
        combined = params.to_dict()
        filters = self.to_dict()
        
        # Merge filters, with filters taking precedence
        combined.update(filters)
        
        return combined