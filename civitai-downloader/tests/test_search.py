"""Tests for search engine."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.search import ModelSearchEngine, SearchCache, CachedSearchEngine
from src.interfaces import ModelInfo, ModelType, SearchParams, SortOrder
from src.config import ConfigManager


@pytest.fixture
def mock_models():
    """Create mock models for testing."""
    return [
        ModelInfo(
            id=1,
            name="Anime Style LORA",
            type=ModelType.LORA,
            description="Anime style model",
            tags=["anime", "style", "illustration"],
            creator="user1",
            stats={"downloadCount": 1000},
            nsfw=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        ModelInfo(
            id=2,
            name="Realistic Portrait",
            type=ModelType.LORA,
            description="Realistic portrait model",
            tags=["realistic", "portrait", "photo"],
            creator="user2",
            stats={"downloadCount": 2000},
            nsfw=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        ModelInfo(
            id=3,
            name="Fantasy Checkpoint",
            type=ModelType.CHECKPOINT,
            description="Fantasy themed checkpoint",
            tags=["fantasy", "illustration", "art"],
            creator="user1",
            stats={"downloadCount": 3000},
            nsfw=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]


@pytest.fixture
def mock_api_client(mock_models):
    """Create mock API client."""
    client = AsyncMock()
    
    async def mock_search(params):
        # Simple filtering based on params
        results = mock_models.copy()
        
        if params.query:
            results = [m for m in results if params.query.lower() in m.name.lower()]
        
        if params.types:
            type_values = [t for t in params.types]
            results = [m for m in results if m.type in type_values]
        
        if params.tags:
            results = [m for m in results if any(tag in m.tags for tag in params.tags)]
        
        return results[:params.limit], None
    
    client.search_models = mock_search
    
    # Mock version fetching
    async def mock_get_versions(model_id):
        return [MagicMock(base_model="SD 1.5")]
    
    client.get_model_versions = mock_get_versions
    
    return client


class TestModelSearchEngine:
    """Test model search engine."""
    
    
    
    
    @pytest.mark.asyncio
    async def test_search_by_tags(self, mock_api_client):
        """Test search filtering by tags."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        results = await engine.search_by_tags(["anime"])
        
        assert len(results) == 1
        assert "anime" in results[0].tags
    
    @pytest.mark.asyncio
    async def test_search_similar(self, mock_api_client, mock_models):
        """Test finding similar models with proper business logic testing."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Mock the search to return models with overlapping tags
        async def mock_search(params):
            # Should search by type only (no tags for similarity)
            assert params.types == [mock_models[0].type]
            assert params.tags is None  # No tags in similarity search
            
            # Return all models for similarity comparison
            return mock_models.copy(), None
        
        mock_api_client.search_models = mock_search
        
        # Find models similar to the anime LORA
        similar = await engine.search_similar(mock_models[0], limit=5)
        
        # Should exclude the original model
        assert mock_models[0].id not in [m.id for m in similar]
        
        # Should return other models with same type
        for model in similar:
            assert model.type == mock_models[0].type or any(
                tag in model.tags for tag in mock_models[0].tags
            )
    
    @pytest.mark.asyncio
    async def test_get_by_creator(self, mock_api_client, mock_models):
        """Test getting models by creator with proper business logic testing."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Mock the search to simulate creator search
        async def mock_search(params):
            # Should search with creator query
            assert params.query == "creator:user1"
            
            # Return models filtered by creator
            filtered_models = [m for m in mock_models if m.creator == "user1"]
            return filtered_models, None
        
        mock_api_client.search_models = mock_search
        
        # Test creator search
        results = await engine.get_by_creator("user1")
        
        # Should return models by the specified creator
        assert len(results) == 2  # user1 has 2 models in mock_models
        assert all(m.creator == "user1" for m in results)
        
        # Should not return models by other creators
        assert not any(m.creator == "user2" for m in results)
    
    
    @pytest.mark.asyncio
    async def test_pagination(self, mock_api_client, mock_models):
        """Test search pagination with proper business logic testing."""
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Mock the search to return all models for pagination processing
        async def mock_search(params):
            # The search engine does its own pagination by slicing results
            # So we always return all models
            return mock_models, None
        
        mock_api_client.search_models = mock_search
        
        # Test page 1 - should return first 2 models
        params = SearchParams(limit=2, page=1)
        page1 = await engine.search(params)
        assert len(page1) == 2
        assert page1[0].id == 1  # First model
        assert page1[1].id == 2  # Second model
        
        # Test page 2 - should return remaining model
        params = SearchParams(limit=2, page=2)
        page2 = await engine.search(params)
        assert len(page2) == 1
        assert page2[0].id == 3  # Third model
        
        # Test page 3 - should return empty (no more models)
        params = SearchParams(limit=2, page=3)
        page3 = await engine.search(params)
        assert len(page3) == 0
        
        # Test that pagination calculation is correct
        # Page 1: start_idx = (1-1) * 2 = 0, end_idx = 0 + 2 = 2 -> [0:2]
        # Page 2: start_idx = (2-1) * 2 = 2, end_idx = 2 + 2 = 4 -> [2:4]
        # Page 3: start_idx = (3-1) * 2 = 4, end_idx = 4 + 2 = 6 -> [4:6] -> empty


class TestSearchCache:
    """Test search cache functionality."""
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = SearchCache()
        
        params1 = SearchParams(query="test", types=[ModelType.LORA])
        params2 = SearchParams(query="test", types=[ModelType.LORA])
        params3 = SearchParams(query="different", types=[ModelType.LORA])
        
        key1 = cache._make_key(params1)
        key2 = cache._make_key(params2)
        key3 = cache._make_key(params3)
        
        assert key1 == key2
        assert key1 != key3
    
    def test_cache_get_set(self, mock_models):
        """Test cache get/set operations."""
        cache = SearchCache()
        
        params = SearchParams(query="test")
        
        # Cache miss
        assert cache.get(params) is None
        
        # Cache set
        cache.set(params, mock_models)
        
        # Cache hit
        cached = cache.get(params)
        assert cached == mock_models
    
    def test_cache_expiration(self, mock_models):
        """Test cache expiration."""
        import time
        
        cache = SearchCache(ttl_seconds=0.1)  # 100ms TTL
        
        params = SearchParams(query="test")
        cache.set(params, mock_models)
        
        # Should be in cache
        assert cache.get(params) is not None
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get(params) is None
    
    def test_cache_clear(self, mock_models):
        """Test cache clearing."""
        cache = SearchCache()
        
        params = SearchParams(query="test")
        cache.set(params, mock_models)
        
        assert cache.get(params) is not None
        
        cache.clear()
        
        assert cache.get(params) is None


class TestCachedSearchEngine:
    """Test cached search engine."""
    
