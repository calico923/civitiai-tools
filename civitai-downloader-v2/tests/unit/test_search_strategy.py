#!/usr/bin/env python3
"""
Search Strategy tests.
Tests for advanced search capabilities with filtering, sorting, and pagination.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.search.strategy import (
    SearchStrategy, SearchFilters, SearchResult, SearchMetadata,
    ModelType, SortOrder, Period,
    search_checkpoints, search_loras, search_by_creator
)
from api.auth import AuthManager


class TestSearchStrategy:
    """Test search strategy functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.auth_manager = AuthManager()
        self.strategy = SearchStrategy(self.auth_manager)
        
        # Mock API response
        self.mock_api_response = {
            'items': [
                {
                    'id': 12345,
                    'name': 'Test Model',
                    'description': 'A test model',
                    'type': 'Checkpoint',
                    'nsfw': False,
                    'tags': ['test', 'model', 'checkpoint'],
                    'stats': {
                        'rating': 4.5,
                        'downloadCount': 1000,
                        'favoriteCount': 50,
                        'commentCount': 25
                    },
                    'creator': {
                        'username': 'testuser',
                        'id': 123
                    },
                    'modelVersions': [
                        {
                            'id': 54321,
                            'name': 'v1.0',
                            'files': []
                        }
                    ],
                    'createdAt': '2024-01-01T00:00:00Z',
                    'updatedAt': '2024-01-02T00:00:00Z'
                }
            ],
            'metadata': {
                'totalItems': 100,
                'currentPage': 1,
                'pageSize': 20,
                'totalPages': 5,
                'nextPage': 'cursor123',
                'prevPage': None
            }
        }
    
    def test_search_filters_creation(self):
        """Test search filters can be created with various options."""
        filters = SearchFilters(
            query="anime",
            model_types=[ModelType.CHECKPOINT, ModelType.LORA],
            sort=SortOrder.HIGHEST_RATED,
            nsfw=False,
            rating=4
        )
        
        assert filters.query == "anime"
        assert len(filters.model_types) == 2
        assert ModelType.CHECKPOINT in filters.model_types
        assert filters.sort == SortOrder.HIGHEST_RATED
        assert filters.nsfw is False
        assert filters.rating == 4
    
    def test_build_search_params_basic(self):
        """Test building basic search parameters."""
        filters = SearchFilters(
            model_types=[ModelType.CHECKPOINT],
            sort=SortOrder.HIGHEST_RATED,
            nsfw=False
        )
        
        params = self.strategy.build_search_params(filters, page=1, limit=20)
        
        assert params['page'] == 1
        assert params['limit'] == 20
        assert params['types'] == ['Checkpoint']
        assert params['sort'] == 'Highest Rated'
        assert params['nsfw'] is False
    
    def test_build_search_params_with_query(self):
        """Test building search parameters with query (cursor-based)."""
        filters = SearchFilters(
            query="anime",
            sort=SortOrder.NEWEST
        )
        
        params = self.strategy.build_search_params(filters, page=1, limit=10, cursor="test_cursor")
        
        assert 'page' not in params  # Should not include page for query searches
        assert params['query'] == "anime"
        assert params['cursor'] == "test_cursor"
        assert params['limit'] == 10
        assert params['sort'] == 'Newest'
    
    def test_build_search_params_all_filters(self):
        """Test building parameters with all filter options."""
        filters = SearchFilters(
            query="test",
            username="testuser",
            tag="anime",
            model_types=[ModelType.LORA, ModelType.CHECKPOINT],
            sort=SortOrder.MOST_DOWNLOADED,
            period=Period.MONTH,
            rating=3,
            nsfw=True,
            favorites=True,
            hidden=False,
            primary_file_only=False,
            allow_no_credit=True,
            allow_derivatives=False,
            allow_different_license=True,
            allow_commercial_use=False
        )
        
        params = self.strategy.build_search_params(filters)
        
        assert params['query'] == "test"
        assert params['username'] == "testuser"
        assert params['tag'] == "anime"
        assert params['types'] == ['LORA', 'Checkpoint']
        assert params['sort'] == 'Most Downloaded'
        assert params['period'] == 'Month'
        assert params['rating'] == 3
        assert params['nsfw'] is True
        assert params['favorites'] is True
        assert params['hidden'] is False
        assert params['primaryFileOnly'] is False
        assert params['allowNoCredit'] is True
        assert params['allowDerivatives'] is False
        assert params['allowDifferentLicense'] is True
        assert params['allowCommercialUse'] is False
    
    @patch('requests.request')
    def test_search_success(self, mock_request):
        """Test successful search execution."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response
        mock_request.return_value = mock_response
        
        filters = SearchFilters(model_types=[ModelType.CHECKPOINT])
        results, metadata = self.strategy.search(filters, limit=1)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].id == 12345
        assert results[0].name == "Test Model"
        assert results[0].type == "Checkpoint"
        assert results[0].rating == 4.5
        assert results[0].download_count == 1000
        assert "test" in results[0].tags
        
        assert isinstance(metadata, SearchMetadata)
        assert metadata.total_items == 100
        assert metadata.current_page == 1
        assert metadata.total_pages == 5
    
    @patch('requests.request')
    def test_search_api_error(self, mock_request):
        """Test search handling API errors."""
        # Setup mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response
        
        filters = SearchFilters()
        
        with pytest.raises(Exception) as exc_info:
            self.strategy.search(filters)
        
        assert "API error: 400" in str(exc_info.value)
    
    def test_search_result_from_api_response_string_tags(self):
        """Test creating SearchResult from API response with string tags."""
        api_data = {
            'id': 123,
            'name': 'Test Model',
            'description': 'Test description',
            'type': 'LORA',
            'nsfw': True,
            'tags': ['anime', 'character', 'lora'],  # String tags
            'stats': {
                'rating': 4.2,
                'downloadCount': 5000,
                'favoriteCount': 100,
                'commentCount': 50
            },
            'creator': {'username': 'creator1'},
            'modelVersions': [],
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z'
        }
        
        result = SearchResult.from_api_response(api_data)
        
        assert result.id == 123
        assert result.name == "Test Model"
        assert result.type == "LORA"
        assert result.nsfw is True
        assert result.tags == ['anime', 'character', 'lora']
        assert result.rating == 4.2
        assert result.download_count == 5000
    
    def test_search_result_from_api_response_object_tags(self):
        """Test creating SearchResult from API response with object tags."""
        api_data = {
            'id': 456,
            'name': 'Another Model',
            'tags': [
                {'name': 'anime', 'id': 1},
                {'name': 'character', 'id': 2}
            ],  # Object tags
            'stats': {'rating': 3.5, 'downloadCount': 2000, 'favoriteCount': 25, 'commentCount': 10},
            'creator': {},
            'modelVersions': []
        }
        
        result = SearchResult.from_api_response(api_data)
        
        assert result.tags == ['anime', 'character']
    
    @patch('requests.request')
    def test_search_by_ids(self, mock_request):
        """Test searching for specific model IDs."""
        # Setup mock response for individual model fetch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response['items'][0]
        mock_request.return_value = mock_response
        
        model_ids = [12345, 67890]
        results = self.strategy.search_by_ids(model_ids)
        
        assert len(results) == 2  # Should fetch both IDs
        assert all(isinstance(r, SearchResult) for r in results)
        assert mock_request.call_count == 2  # One call per ID
    
    @patch('requests.request')
    def test_get_popular_tags(self, mock_request):
        """Test fetching popular tags."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'name': 'anime', 'count': 1000},
                {'name': 'realistic', 'count': 800},
                {'name': 'character', 'count': 600}
            ]
        }
        mock_request.return_value = mock_response
        
        tags = self.strategy.get_popular_tags(limit=10)
        
        assert len(tags) == 3
        assert tags[0]['name'] == 'anime'
        assert tags[0]['count'] == 1000
    
    def test_search_statistics_tracking(self):
        """Test search statistics are tracked correctly."""
        initial_stats = self.strategy.get_search_stats()
        assert initial_stats['total_searches'] == 0
        assert initial_stats['total_results'] == 0
        assert initial_stats['errors'] == 0
        
        # Update stats manually to test tracking
        self.strategy._update_stats(5, 1.5, success=True)
        self.strategy._update_stats(3, 2.0, success=True)
        self.strategy._update_stats(0, 0.5, success=False)
        
        stats = self.strategy.get_search_stats()
        assert stats['total_searches'] == 3
        assert stats['total_results'] == 8
        assert stats['errors'] == 1
        assert stats['avg_response_time'] == 1.75  # (1.5 + 2.0) / 2
    
    def test_reset_statistics(self):
        """Test resetting search statistics."""
        # Add some stats
        self.strategy._update_stats(5, 1.0, success=True)
        
        # Reset and verify
        self.strategy.reset_stats()
        stats = self.strategy.get_search_stats()
        
        assert stats['total_searches'] == 0
        assert stats['total_results'] == 0
        assert stats['avg_response_time'] == 0.0
        assert stats['errors'] == 0


class TestConvenienceFunctions:
    """Test convenience search functions."""
    
    @patch('core.search.strategy.SearchStrategy.search')
    def test_search_checkpoints(self, mock_search):
        """Test checkpoint search convenience function."""
        mock_search.return_value = ([], Mock())
        
        search_checkpoints(query="anime", nsfw=False, limit=10)
        
        # Verify search was called with correct filters
        call_args = mock_search.call_args
        filters = call_args[0][0]  # First argument is filters
        
        assert filters.query == "anime"
        assert ModelType.CHECKPOINT in filters.model_types
        assert filters.nsfw is False
        assert filters.sort == SortOrder.HIGHEST_RATED
    
    @patch('core.search.strategy.SearchStrategy.search')
    def test_search_loras(self, mock_search):
        """Test LoRA search convenience function."""
        mock_search.return_value = ([], Mock())
        
        search_loras(query="character", limit=5)
        
        call_args = mock_search.call_args
        filters = call_args[0][0]
        
        assert filters.query == "character"
        assert ModelType.LORA in filters.model_types
        assert filters.sort == SortOrder.MOST_DOWNLOADED
    
    @patch('core.search.strategy.SearchStrategy.search')
    def test_search_by_creator(self, mock_search):
        """Test creator search convenience function."""
        mock_search.return_value = ([], Mock())
        
        search_by_creator(username="testuser", limit=15)
        
        call_args = mock_search.call_args
        filters = call_args[0][0]
        
        assert filters.username == "testuser"
        assert filters.sort == SortOrder.NEWEST


class TestEnumTypes:
    """Test enum type definitions."""
    
    def test_model_type_enum(self):
        """Test ModelType enum values."""
        assert ModelType.CHECKPOINT.value == "Checkpoint"
        assert ModelType.LORA.value == "LORA"
        assert ModelType.TEXTUAL_INVERSION.value == "TextualInversion"
        assert ModelType.CONTROLNET.value == "Controlnet"
    
    def test_sort_order_enum(self):
        """Test SortOrder enum values."""
        assert SortOrder.HIGHEST_RATED.value == "Highest Rated"
        assert SortOrder.MOST_DOWNLOADED.value == "Most Downloaded"
        assert SortOrder.NEWEST.value == "Newest"
        assert SortOrder.MOST_LIKED.value == "Most Liked"
    
    def test_period_enum(self):
        """Test Period enum values."""
        assert Period.ALL_TIME.value == "AllTime"
        assert Period.MONTH.value == "Month"
        assert Period.WEEK.value == "Week"
        assert Period.DAY.value == "Day"


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])