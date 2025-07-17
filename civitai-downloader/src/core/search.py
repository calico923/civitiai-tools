"""Model search engine with filtering capabilities."""

from typing import List, Dict, Optional, Any, Iterator
from dataclasses import dataclass
import re

from ..api.client import CivitAIClient
from ..api.models import SearchQuery, ModelSummary, SearchResponse
from ..api.exceptions import APIError, ValidationError


@dataclass
class SearchFilter:
    """Search filter configuration."""
    model_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    base_models: Optional[List[str]] = None
    username: Optional[str] = None
    nsfw: Optional[bool] = None
    min_downloads: Optional[int] = None
    min_rating: Optional[float] = None
    checkpoint_type: Optional[str] = None  # "Merge" or "Trained"


class ModelTypeNormalizer:
    """Handles model type normalization between UI names and API names."""
    
    # Mapping from common UI names to API names
    TYPE_MAPPING = {
        "LoRA": "LORA",
        "LyCORIS": "LoCon", 
        "Embedding": "TextualInversion",
        "ControlNet": "Controlnet",
        "Motion": "Other",  # Motion is not a separate type in API
    }
    
    # Valid API model types based on investigation
    VALID_API_TYPES = {
        "Checkpoint", "LORA", "LoCon", "TextualInversion", 
        "Hypernetwork", "AestheticGradient", "VAE", "Poses",
        "DoRA", "Workflows", "Upscaler", "Controlnet", 
        "Detection", "Wildcards", "Other"
    }
    
    @classmethod
    def normalize_type(cls, model_type: str) -> str:
        """
        Normalize model type from UI name to API name.
        
        Args:
            model_type: Model type (UI or API name)
            
        Returns:
            API-compatible model type name
        """
        # Return the mapped type if it exists, otherwise return as-is
        return cls.TYPE_MAPPING.get(model_type, model_type)
    
    @classmethod
    def normalize_types(cls, model_types: List[str]) -> List[str]:
        """
        Normalize a list of model types.
        
        Args:
            model_types: List of model types
            
        Returns:
            List of API-compatible model type names
        """
        return [cls.normalize_type(t) for t in model_types]
    
    @classmethod
    def validate_type(cls, model_type: str) -> bool:
        """
        Check if a model type is valid for the API.
        
        Args:
            model_type: Model type to validate
            
        Returns:
            True if valid, False otherwise
        """
        normalized = cls.normalize_type(model_type)
        return normalized in cls.VALID_API_TYPES


class BaseModelFilter:
    """Client-side filtering for base models since API doesn't support it."""
    
    @staticmethod
    def extract_base_model(model_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract base model from model data.
        
        Args:
            model_data: Raw model data from API
            
        Returns:
            Base model name or None
        """
        # Try to get base model from first version
        versions = model_data.get("modelVersions", [])
        if versions and len(versions) > 0:
            return versions[0].get("baseModel")
        return None
    
    @staticmethod
    def matches_base_model(model_data: Dict[str, Any], target_base_model: str) -> bool:
        """
        Check if model matches the target base model.
        
        Args:
            model_data: Raw model data from API
            target_base_model: Target base model to match
            
        Returns:
            True if matches, False otherwise
        """
        base_model = BaseModelFilter.extract_base_model(model_data)
        if not base_model:
            return False
        
        # Case-insensitive partial matching
        return target_base_model.lower() in base_model.lower()
    
    @staticmethod
    def filter_by_base_models(
        models_data: List[Dict[str, Any]], 
        base_models: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter models by base model(s).
        
        Args:
            models_data: List of raw model data from API
            base_models: List of base models to filter by
            
        Returns:
            Filtered list of model data
        """
        if not base_models:
            return models_data
        
        filtered = []
        for model_data in models_data:
            for base_model in base_models:
                if BaseModelFilter.matches_base_model(model_data, base_model):
                    filtered.append(model_data)
                    break  # Don't add the same model multiple times
        
        return filtered


class CheckpointTypeFilter:
    """Client-side filtering for checkpoint types (Merge vs Trained)."""
    
    @staticmethod
    def detect_checkpoint_type(model_data: Dict[str, Any]) -> Optional[str]:
        """
        Detect if a checkpoint is Merge or Trained based on metadata.
        
        Args:
            model_data: Raw model data from API
            
        Returns:
            "Merge" or "Trained" or None if undetermined
        """
        # Check model name and description for merge indicators
        name = model_data.get("name", "").lower()
        description = model_data.get("description", "").lower()
        
        merge_keywords = ["merge", "mix", "mixed", "blend", "combined"]
        trained_keywords = ["trained", "finetune", "fine-tune", "custom"]
        
        # Check in name first (more reliable)
        for keyword in merge_keywords:
            if keyword in name:
                return "Merge"
        
        for keyword in trained_keywords:
            if keyword in name:
                return "Trained"
        
        # Check in description
        for keyword in merge_keywords:
            if keyword in description:
                return "Merge"
        
        # Default assumption: if no merge indicators, likely trained
        return "Trained"
    
    @staticmethod
    def filter_by_checkpoint_type(
        models_data: List[Dict[str, Any]], 
        checkpoint_type: str
    ) -> List[Dict[str, Any]]:
        """
        Filter checkpoints by type (Merge/Trained).
        
        Args:
            models_data: List of raw model data from API
            checkpoint_type: "Merge" or "Trained"
            
        Returns:
            Filtered list of model data
        """
        filtered = []
        for model_data in models_data:
            # Only apply to Checkpoint type models
            if model_data.get("type") == "Checkpoint":
                detected_type = CheckpointTypeFilter.detect_checkpoint_type(model_data)
                if detected_type == checkpoint_type:
                    filtered.append(model_data)
            else:
                # For non-checkpoint models, include all
                filtered.append(model_data)
        
        return filtered


class ModelSearchEngine:
    """Advanced model search engine with client-side filtering."""
    
    def __init__(self, client: CivitAIClient):
        """
        Initialize search engine.
        
        Args:
            client: CivitAI API client
        """
        self.client = client
        self.type_normalizer = ModelTypeNormalizer()
    
    def search(
        self,
        query: Optional[str] = None,
        search_filter: Optional[SearchFilter] = None,
        sort: str = "Highest Rated",
        limit: int = 20,
        max_pages: int = 5
    ) -> SearchResponse:
        """
        Search for models with advanced filtering.
        
        Args:
            query: Search query string
            search_filter: Search filter configuration
            sort: Sort order
            limit: Results per page
            max_pages: Maximum pages to fetch for client-side filtering
            
        Returns:
            SearchResponse with filtered results
        """
        if search_filter is None:
            search_filter = SearchFilter()
        
        # Normalize model types
        api_types = None
        if search_filter.model_types:
            api_types = self.type_normalizer.normalize_types(search_filter.model_types)
            
            # Validate types
            invalid_types = [t for t in api_types if not self.type_normalizer.validate_type(t)]
            if invalid_types:
                raise ValidationError(f"Invalid model types: {invalid_types}")
        
        # Perform API search
        api_response = self.client.search_models(
            query=query,
            model_types=api_types,
            tags=search_filter.tags[:1] if search_filter.tags else None,  # API only supports one tag
            username=search_filter.username,
            sort=sort,
            limit=min(limit * max_pages, 100),  # Get more results for filtering
            nsfw=search_filter.nsfw
        )
        
        # Apply client-side filters
        filtered_models = self._apply_client_filters(api_response.items, search_filter)
        
        # Limit results to requested amount
        final_models = filtered_models[:limit]
        
        return SearchResponse(
            items=final_models,
            metadata=api_response.metadata,
            total_items=len(filtered_models),
            current_page=1,
            total_pages=1,
            page_size=len(final_models)
        )
    
    def search_with_pagination(
        self,
        query: Optional[str] = None,
        search_filter: Optional[SearchFilter] = None,
        sort: str = "Highest Rated",
        limit: int = 20,
        max_results: int = 1000
    ) -> Iterator[ModelSummary]:
        """
        Search with cursor-based pagination for large result sets.
        
        Args:
            query: Search query string
            search_filter: Search filter configuration
            sort: Sort order
            limit: Results per API call
            max_results: Maximum total results to return
            
        Yields:
            ModelSummary objects
        """
        if search_filter is None:
            search_filter = SearchFilter()
        
        cursor = None
        total_yielded = 0
        
        while total_yielded < max_results:
            # Normalize model types
            api_types = None
            if search_filter.model_types:
                api_types = self.type_normalizer.normalize_types(search_filter.model_types)
            
            # Make API call
            try:
                response = self.client.search_models(
                    query=query,
                    model_types=api_types,
                    tags=search_filter.tags[:1] if search_filter.tags else None,
                    username=search_filter.username,
                    sort=sort,
                    limit=limit,
                    cursor=cursor,
                    nsfw=search_filter.nsfw
                )
                
                if not response.items:
                    break
                
                # Apply client-side filters to raw data
                # Note: We need to work with raw API data for proper filtering
                raw_items = []  # This would need to be passed from the client
                filtered_models = self._apply_client_filters(response.items, search_filter)
                
                for model in filtered_models:
                    if total_yielded >= max_results:
                        break
                    yield model
                    total_yielded += 1
                
                # Check for next page
                if not response.next_cursor:
                    break
                
                cursor = response.next_cursor
                
            except APIError as e:
                # Log error and break
                print(f"API error during pagination: {e}")
                break
    
    def _apply_client_filters(
        self, 
        models: List[ModelSummary], 
        search_filter: SearchFilter
    ) -> List[ModelSummary]:
        """
        Apply client-side filters to model list.
        
        Args:
            models: List of model summaries
            search_filter: Filter configuration
            
        Returns:
            Filtered list of models
        """
        filtered = list(models)
        
        # Note: For proper base model and checkpoint type filtering,
        # we would need access to the raw API data, not just ModelSummary objects.
        # This would require modifying the client to preserve raw data.
        
        # Apply stats-based filters
        if search_filter.min_downloads is not None:
            filtered = [
                m for m in filtered 
                if m.stats and m.stats.download_count >= search_filter.min_downloads
            ]
        
        if search_filter.min_rating is not None:
            filtered = [
                m for m in filtered 
                if m.stats and m.stats.rating >= search_filter.min_rating
            ]
        
        # Apply multiple tag filtering (since API only supports one tag)
        if search_filter.tags and len(search_filter.tags) > 1:
            remaining_tags = [tag.lower() for tag in search_filter.tags[1:]]
            filtered = [
                m for m in filtered
                if all(
                    any(tag in model_tag.lower() for model_tag in m.tags)
                    for tag in remaining_tags
                )
            ]
        
        return filtered
    
    def get_model_details(self, model_id: str) -> Dict[str, Any]:
        """
        Get detailed model information.
        
        Args:
            model_id: Model ID
            
        Returns:
            Detailed model information
        """
        return self.client.get_model(model_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get search engine statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "api_client_stats": self.client.get_rate_limiter_stats(),
            "supported_types": list(self.type_normalizer.VALID_API_TYPES),
            "type_mappings": self.type_normalizer.TYPE_MAPPING
        }