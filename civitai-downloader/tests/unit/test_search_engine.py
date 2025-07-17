"""Unit tests for Model Search Engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from src.core.search import (
    ModelSearchEngine, SearchFilter, ModelTypeNormalizer,
    BaseModelFilter, CheckpointTypeFilter
)
from src.api.client import CivitAIClient
from src.api.models import SearchResponse, ModelSummary, ModelStats
from src.api.exceptions import ValidationError


class TestModelTypeNormalizer:
    """Test cases for model type normalization."""
    
    def test_normalize_type_mapping(self):
        """Test model type normalization mappings."""
        assert ModelTypeNormalizer.normalize_type("LoRA") == "LORA"
        assert ModelTypeNormalizer.normalize_type("LyCORIS") == "LoCon"
        assert ModelTypeNormalizer.normalize_type("Embedding") == "TextualInversion"
        assert ModelTypeNormalizer.normalize_type("ControlNet") == "Controlnet"
        assert ModelTypeNormalizer.normalize_type("Motion") == "Other"
    
    def test_normalize_type_no_mapping(self):
        """Test normalization for types without mapping."""
        assert ModelTypeNormalizer.normalize_type("Checkpoint") == "Checkpoint"
        assert ModelTypeNormalizer.normalize_type("VAE") == "VAE"
        assert ModelTypeNormalizer.normalize_type("Unknown") == "Unknown"
    
    def test_normalize_types_list(self):
        """Test normalizing a list of types."""
        input_types = ["LoRA", "Checkpoint", "LyCORIS"]
        expected = ["LORA", "Checkpoint", "LoCon"]
        assert ModelTypeNormalizer.normalize_types(input_types) == expected
    
    def test_validate_type_valid(self):
        """Test validation of valid model types."""
        assert ModelTypeNormalizer.validate_type("Checkpoint") == True
        assert ModelTypeNormalizer.validate_type("LORA") == True
        assert ModelTypeNormalizer.validate_type("LoRA") == True  # Gets normalized to LORA
    
    def test_validate_type_invalid(self):
        """Test validation of invalid model types."""
        assert ModelTypeNormalizer.validate_type("InvalidType") == False
        assert ModelTypeNormalizer.validate_type("") == False


class TestBaseModelFilter:
    """Test cases for base model filtering."""
    
    def test_extract_base_model_success(self):
        """Test successful base model extraction."""
        model_data = {
            "modelVersions": [
                {"baseModel": "Illustrious"},
                {"baseModel": "SD 1.5"}
            ]
        }
        assert BaseModelFilter.extract_base_model(model_data) == "Illustrious"
    
    def test_extract_base_model_no_versions(self):
        """Test base model extraction with no versions."""
        model_data = {"modelVersions": []}
        assert BaseModelFilter.extract_base_model(model_data) is None
        
        model_data = {}
        assert BaseModelFilter.extract_base_model(model_data) is None
    
    def test_matches_base_model_exact(self):
        """Test exact base model matching."""
        model_data = {
            "modelVersions": [{"baseModel": "Illustrious"}]
        }
        assert BaseModelFilter.matches_base_model(model_data, "Illustrious") == True
        assert BaseModelFilter.matches_base_model(model_data, "SD 1.5") == False
    
    def test_matches_base_model_partial(self):
        """Test partial base model matching."""
        model_data = {
            "modelVersions": [{"baseModel": "Illustrious XL"}]
        }
        assert BaseModelFilter.matches_base_model(model_data, "Illustrious") == True
        assert BaseModelFilter.matches_base_model(model_data, "illustrious") == True  # Case insensitive
    
    def test_filter_by_base_models(self):
        """Test filtering models by base models."""
        models_data = [
            {"id": 1, "modelVersions": [{"baseModel": "Illustrious"}]},
            {"id": 2, "modelVersions": [{"baseModel": "SD 1.5"}]},
            {"id": 3, "modelVersions": [{"baseModel": "Pony"}]},
            {"id": 4, "modelVersions": [{"baseModel": "Illustrious XL"}]}
        ]
        
        filtered = BaseModelFilter.filter_by_base_models(models_data, ["Illustrious"])
        assert len(filtered) == 2  # Models 1 and 4
        assert filtered[0]["id"] == 1
        assert filtered[1]["id"] == 4
        
        filtered = BaseModelFilter.filter_by_base_models(models_data, ["SD 1.5", "Pony"])
        assert len(filtered) == 2  # Models 2 and 3


class TestCheckpointTypeFilter:
    """Test cases for checkpoint type filtering."""
    
    def test_detect_checkpoint_type_merge(self):
        """Test detection of merge checkpoints."""
        model_data = {"name": "Amazing Merge v1.0", "type": "Checkpoint"}
        assert CheckpointTypeFilter.detect_checkpoint_type(model_data) == "Merge"
        
        model_data = {"name": "Test Model", "description": "This is a merge of multiple models"}
        assert CheckpointTypeFilter.detect_checkpoint_type(model_data) == "Merge"
    
    def test_detect_checkpoint_type_trained(self):
        """Test detection of trained checkpoints."""
        model_data = {"name": "Custom Trained Model", "type": "Checkpoint"}
        assert CheckpointTypeFilter.detect_checkpoint_type(model_data) == "Trained"
        
        model_data = {"name": "Regular Model", "description": "Finetuned for anime"}
        assert CheckpointTypeFilter.detect_checkpoint_type(model_data) == "Trained"
    
    def test_detect_checkpoint_type_default(self):
        """Test default detection (assumes trained)."""
        model_data = {"name": "Regular Model", "description": "A normal model"}
        assert CheckpointTypeFilter.detect_checkpoint_type(model_data) == "Trained"
    
    def test_filter_by_checkpoint_type(self):
        """Test filtering by checkpoint type."""
        models_data = [
            {"id": 1, "type": "Checkpoint", "name": "Merge Model v1"},
            {"id": 2, "type": "Checkpoint", "name": "Trained Model v1"},
            {"id": 3, "type": "LORA", "name": "LORA Model"},
            {"id": 4, "type": "Checkpoint", "name": "Another mix"}
        ]
        
        merge_models = CheckpointTypeFilter.filter_by_checkpoint_type(models_data, "Merge")
        assert len(merge_models) == 3  # 2 checkpoints + 1 non-checkpoint
        
        trained_models = CheckpointTypeFilter.filter_by_checkpoint_type(models_data, "Trained")
        assert len(trained_models) == 2  # 1 checkpoint + 1 non-checkpoint


class TestModelSearchEngine:
    """Test cases for Model Search Engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=CivitAIClient)
        self.search_engine = ModelSearchEngine(self.mock_client)
    
    def test_init(self):
        """Test search engine initialization."""
        assert self.search_engine.client == self.mock_client
        assert isinstance(self.search_engine.type_normalizer, ModelTypeNormalizer)
    
    def test_search_with_type_normalization(self):
        """Test search with model type normalization."""
        mock_response = SearchResponse(items=[], metadata={})
        self.mock_client.search_models.return_value = mock_response
        
        search_filter = SearchFilter(model_types=["LoRA", "LyCORIS"])
        self.search_engine.search(search_filter=search_filter)
        
        # Verify normalized types were passed to client
        call_args = self.mock_client.search_models.call_args
        assert call_args[1]["model_types"] == ["LORA", "LoCon"]
    
    def test_search_with_invalid_types(self):
        """Test search with invalid model types."""
        search_filter = SearchFilter(model_types=["InvalidType"])
        
        with pytest.raises(ValidationError) as exc_info:
            self.search_engine.search(search_filter=search_filter)
        
        assert "Invalid model types" in str(exc_info.value)
    
    def test_search_with_filters(self):
        """Test search with various filters."""
        mock_models = [
            ModelSummary(
                id="123",
                name="High Rated Model",
                type="Checkpoint",
                stats=ModelStats(download_count=5000, rating=4.8),
                tags=["anime", "style"]
            ),
            ModelSummary(
                id="124",
                name="Low Rated Model",
                type="Checkpoint",
                stats=ModelStats(download_count=100, rating=2.0),
                tags=["anime"]
            )
        ]
        
        mock_response = SearchResponse(items=mock_models, metadata={})
        self.mock_client.search_models.return_value = mock_response
        
        # Test with min rating filter
        search_filter = SearchFilter(min_rating=4.0)
        result = self.search_engine.search(search_filter=search_filter)
        
        assert len(result.items) == 1
        assert result.items[0].name == "High Rated Model"
    
    def test_get_model_details(self):
        """Test getting model details."""
        mock_model_details = {"id": "123", "name": "Test Model"}
        self.mock_client.get_model.return_value = mock_model_details
        
        result = self.search_engine.get_model_details("123")
        
        assert result == mock_model_details
        self.mock_client.get_model.assert_called_once_with("123")
    
    def test_get_stats(self):
        """Test getting search engine statistics."""
        mock_stats = {"calls_made": 5, "average_rate": 0.5}
        self.mock_client.get_rate_limiter_stats.return_value = mock_stats
        
        result = self.search_engine.get_stats()
        
        assert "api_client_stats" in result
        assert "supported_types" in result
        assert "type_mappings" in result
        assert result["api_client_stats"] == mock_stats
        assert "Checkpoint" in result["supported_types"]
        assert result["type_mappings"]["LoRA"] == "LORA"


class TestSearchFilter:
    """Test cases for SearchFilter dataclass."""
    
    def test_default_values(self):
        """Test default filter values."""
        filter_obj = SearchFilter()
        
        assert filter_obj.model_types is None
        assert filter_obj.tags is None
        assert filter_obj.base_models is None
        assert filter_obj.username is None
        assert filter_obj.nsfw is None
        assert filter_obj.min_downloads is None
        assert filter_obj.min_rating is None
        assert filter_obj.checkpoint_type is None
    
    def test_custom_values(self):
        """Test custom filter values."""
        filter_obj = SearchFilter(
            model_types=["Checkpoint"],
            tags=["anime"],
            min_rating=4.0,
            checkpoint_type="Merge"
        )
        
        assert filter_obj.model_types == ["Checkpoint"]
        assert filter_obj.tags == ["anime"]
        assert filter_obj.min_rating == 4.0
        assert filter_obj.checkpoint_type == "Merge"