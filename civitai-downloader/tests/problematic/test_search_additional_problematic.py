"""Additional problematic search tests.

These tests have been moved here because they are too shallow or use
overly simplified mocks that don't test real business logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.search import ModelSearchEngine, SearchCache, CachedSearchEngine
from src.interfaces import SearchParams, ModelType


class TestAdditionalProblematicSearchTests:
    """Tests that are too shallow or use unrealistic mocks."""
    
    @pytest.mark.asyncio
    async def test_basic_search_problematic(self, mock_api_client, mock_models):
        """Test basic search functionality - PROBLEMATIC VERSION."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        params = SearchParams(limit=10)
        results = await engine.search(params)
        
        # PROBLEM: Only tests that mocked data comes back unchanged
        assert len(results) == 3
        assert results[0].name == "Anime Style LORA"
    
    @pytest.mark.asyncio
    async def test_search_with_query_problematic(self, mock_api_client):
        """Test search with query string - PROBLEMATIC VERSION."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        params = SearchParams(query="anime", limit=10)
        results = await engine.search(params)
        
        # PROBLEM: Mock filtering is too simple, doesn't test real complexity
        assert len(results) == 1
        assert results[0].name == "Anime Style LORA"
    
    @pytest.mark.asyncio
    async def test_search_by_type_problematic(self, mock_api_client):
        """Test search filtering by type - PROBLEMATIC VERSION."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        params = SearchParams(types=[ModelType.LORA], limit=10)
        results = await engine.search(params)
        
        # PROBLEM: Mock filtering is trivial
        assert len(results) == 2
        assert all(m.type == ModelType.LORA for m in results)
    
    @pytest.mark.asyncio
    async def test_filter_by_base_model_problematic(self, mock_api_client, mock_models):
        """Test filtering by base model - PROBLEMATIC VERSION."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test filtering
        filtered = await engine.filter_by_base_model(mock_models, ["SD 1.5"])
        
        # PROBLEM: Mock always returns SD 1.5 for all models
        # This test will pass even if version fetching is broken
        assert len(filtered) == 3
    
    @pytest.mark.asyncio
    async def test_cached_search_problematic(self, mock_api_client):
        """Test that search results are cached - PROBLEMATIC VERSION."""
        engine = CachedSearchEngine(api_client=mock_api_client)
        
        params = SearchParams(query="anime")
        
        # First search - should hit API
        call_count = 0
        original_search = mock_api_client.search_models
        
        async def counting_search(p):
            nonlocal call_count
            call_count += 1
            return await original_search(p)
        
        mock_api_client.search_models = counting_search
        
        results1 = await engine.search(params)
        assert call_count == 1
        
        # Second search - should hit cache
        results2 = await engine.search(params)
        assert call_count == 1  # No additional API call
        
        # PROBLEM: Only tests call counting, not cache correctness
        # Could pass even if cache returns wrong data or expires incorrectly
        assert results1 == results2