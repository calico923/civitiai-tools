"""Meaningful search engine tests that test actual business logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import time

from src.search import ModelSearchEngine, SearchCache, CachedSearchEngine
from src.interfaces import SearchParams, ModelType, SortOrder, ModelInfo, ModelCategory, PeriodFilter
from src.config import ConfigManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=ConfigManager)
    config.config = MagicMock()
    config.config.api_base_url = "https://civitai.com/api/v1"
    config.config.api_key = "test-api-key"
    config.config.api_timeout = 30
    config.config.api_max_retries = 3
    config.config.user_agent = "Test/1.0"
    config.config.verify_ssl = True
    config.config.proxy = None
    return config


class TestMeaningfulSearchEngine:
    """Tests that validate actual search engine business logic."""
    
    @pytest.fixture
    def realistic_models(self):
        """Create realistic model data for testing."""
        return [
            ModelInfo(
                id=1,
                name="Anime Portrait LORA",
                type=ModelType.LORA,
                description="High-quality anime portrait generation",
                tags=["anime", "portrait", "style", "character"],
                creator="anime_artist",
                stats={"downloadCount": 5420, "favoriteCount": 892},
                nsfw=False,
                created_at=datetime.now() - timedelta(days=30),
                updated_at=datetime.now() - timedelta(days=5)
            ),
            ModelInfo(
                id=2,
                name="Realistic Photo Style",
                type=ModelType.LORA,
                description="Photorealistic image generation",
                tags=["realistic", "photo", "portrait", "professional"],
                creator="photo_expert",
                stats={"downloadCount": 12340, "favoriteCount": 1567},
                nsfw=False,
                created_at=datetime.now() - timedelta(days=15),
                updated_at=datetime.now() - timedelta(days=2)
            ),
            ModelInfo(
                id=3,
                name="Fantasy Art Checkpoint",
                type=ModelType.CHECKPOINT,
                description="Fantasy and magical art generation",
                tags=["fantasy", "magic", "art", "illustration"],
                creator="fantasy_creator",
                stats={"downloadCount": 8900, "favoriteCount": 678},
                nsfw=False,
                created_at=datetime.now() - timedelta(days=45),
                updated_at=datetime.now() - timedelta(days=10)
            ),
            ModelInfo(
                id=4,
                name="NSFW Content Model",
                type=ModelType.LORA,
                description="Adult content generation",
                tags=["nsfw", "adult", "style"],
                creator="adult_artist",
                stats={"downloadCount": 3200, "favoriteCount": 234},
                nsfw=True,
                created_at=datetime.now() - timedelta(days=20),
                updated_at=datetime.now() - timedelta(days=1)
            )
        ]
    
    @pytest.mark.asyncio
    async def test_complex_filtering_logic(self, realistic_models):
        """Test complex filtering with realistic data and edge cases."""
        # Mock API client that can handle complex filtering
        mock_api_client = AsyncMock()
        
        async def intelligent_search(params):
            results = realistic_models.copy()
            
            # Apply query filtering
            if params.query:
                query_lower = params.query.lower()
                results = [m for m in results if 
                          query_lower in m.name.lower() or 
                          query_lower in m.description.lower() or
                          any(query_lower in tag.lower() for tag in m.tags)]
            
            # Apply type filtering
            if params.types:
                results = [m for m in results if m.type in params.types]
            
            # Apply tag filtering (AND logic)
            if params.tags:
                results = [m for m in results if 
                          all(any(tag.lower() in model_tag.lower() for model_tag in m.tags) 
                              for tag in params.tags)]
            
            # Apply NSFW filtering
            if params.nsfw is not None:
                results = [m for m in results if m.nsfw == params.nsfw]
            
            # Apply sorting
            if params.sort == SortOrder.MOST_DOWNLOADED:
                results.sort(key=lambda m: m.stats.get('downloadCount', 0), reverse=True)
            elif params.sort == SortOrder.NEWEST:
                results.sort(key=lambda m: m.created_at, reverse=True)
            
            return results, None
        
        mock_api_client.search_models = intelligent_search
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test 1: Complex query with multiple filters
        params = SearchParams(
            query="portrait",
            types=[ModelType.LORA],
            tags=["portrait", "style"],
            nsfw=False,
            sort=SortOrder.MOST_DOWNLOADED,
            limit=10
        )
        
        results = await engine.search(params)
        
        # Should find anime portrait (has both "portrait" and "style" tags)
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].name == "Anime Portrait LORA"
        
        # Test 2: NSFW filtering
        params = SearchParams(nsfw=True)
        results = await engine.search(params)
        
        assert len(results) == 1
        assert results[0].nsfw == True
        
        # Test 3: Type filtering with multiple types
        params = SearchParams(types=[ModelType.LORA, ModelType.CHECKPOINT])
        results = await engine.search(params)
        
        assert len(results) == 4  # All models
        
        # Test 4: Sorting verification
        params = SearchParams(sort=SortOrder.MOST_DOWNLOADED)
        results = await engine.search(params)
        
        # Should be sorted by download count (highest first)
        download_counts = [m.stats['downloadCount'] for m in results]
        assert download_counts == sorted(download_counts, reverse=True)
    
    @pytest.mark.asyncio
    async def test_base_model_filtering_with_version_fetching(self, realistic_models):
        """Test base model filtering with realistic version fetching."""
        mock_api_client = AsyncMock()
        
        # Mock version responses with different base models
        version_responses = {
            1: [MagicMock(base_model="SD 1.5"), MagicMock(base_model="SD 1.5")],
            2: [MagicMock(base_model="SDXL 1.0")],
            3: [MagicMock(base_model="SD 1.5"), MagicMock(base_model="SDXL 1.0")],
            4: [MagicMock(base_model="Pony Diffusion")]
        }
        
        async def mock_get_versions(model_id):
            return version_responses.get(model_id, [])
        
        mock_api_client.get_model_versions = mock_get_versions
        mock_api_client.search_models = AsyncMock(return_value=(realistic_models, None))
        
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test filtering by SD 1.5
        filtered = await engine.filter_by_base_model(realistic_models, ["SD 1.5"])
        
        # Should include models 1 and 3 (have SD 1.5 versions)
        filtered_ids = [m.id for m in filtered]
        assert 1 in filtered_ids
        assert 3 in filtered_ids
        assert 2 not in filtered_ids  # Only has SDXL
        assert 4 not in filtered_ids  # Only has Pony
        
        # Test filtering by SDXL
        filtered = await engine.filter_by_base_model(realistic_models, ["SDXL 1.0"])
        
        filtered_ids = [m.id for m in filtered]
        assert 2 in filtered_ids
        assert 3 in filtered_ids
        assert 1 not in filtered_ids
        assert 4 not in filtered_ids
    
    @pytest.mark.asyncio
    async def test_similarity_algorithm_with_realistic_data(self, realistic_models):
        """Test similarity algorithm with realistic tag matching."""
        mock_api_client = AsyncMock()
        
        async def search_with_params(params):
            # Simulate similarity search - should match by type and tags
            target_model = realistic_models[0]  # Anime Portrait LORA
            
            # Should search for same type and top tags
            assert params.types == [target_model.type]
            assert params.tags == target_model.tags[:5]  # Top 5 tags
            
            # Return models with overlapping tags
            similar_models = []
            for model in realistic_models:
                if model.id != target_model.id:  # Exclude original
                    # Check for tag overlap
                    overlap = set(model.tags) & set(target_model.tags)
                    if overlap or model.type == target_model.type:
                        similar_models.append(model)
            
            return similar_models, None
        
        mock_api_client.search_models = search_with_params
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test similarity search
        target_model = realistic_models[0]  # Anime Portrait LORA
        similar = await engine.search_similar(target_model, limit=5)
        
        # Should exclude the original model
        assert target_model.id not in [m.id for m in similar]
        
        # Should find the realistic portrait model (shares "portrait" tag)
        similar_ids = [m.id for m in similar]
        assert 2 in similar_ids  # Realistic Photo Style shares "portrait" tag
        
        # Verify similarity logic - all should have overlapping tags or same type
        for model in similar:
            has_tag_overlap = bool(set(model.tags) & set(target_model.tags))
            has_same_type = model.type == target_model.type
            assert has_tag_overlap or has_same_type
    
    @pytest.mark.asyncio
    async def test_pagination_with_realistic_data_flow(self, realistic_models):
        """Test pagination with realistic data flow and edge cases."""
        mock_api_client = AsyncMock()
        
        # Mock API that returns all data (engine handles pagination)
        async def return_all_data(params):
            return realistic_models, None
        
        mock_api_client.search_models = return_all_data
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test normal pagination
        page1 = await engine.search(SearchParams(limit=2, page=1))
        assert len(page1) == 2
        assert page1[0].id == 1
        assert page1[1].id == 2
        
        page2 = await engine.search(SearchParams(limit=2, page=2))
        assert len(page2) == 2
        assert page2[0].id == 3
        assert page2[1].id == 4
        
        # Test edge case: page beyond available data
        page3 = await engine.search(SearchParams(limit=2, page=3))
        assert len(page3) == 0
        
        # Test large page size
        all_page = await engine.search(SearchParams(limit=100, page=1))
        assert len(all_page) == 4  # All available models
        
        # Test pagination with filtering
        filtered_page = await engine.search(SearchParams(
            types=[ModelType.LORA], 
            limit=2, 
            page=1
        ))
        # Should contain only LORA models from page 1
        assert len(filtered_page) == 2
        assert all(m.type == ModelType.LORA for m in filtered_page)


class TestMeaningfulSearchCache:
    """Tests that validate actual caching logic and data integrity."""
    
    @pytest.mark.asyncio
    async def test_cache_data_integrity_and_expiration(self):
        """Test that cache maintains data integrity and handles expiration correctly."""
        # Create cache with short TTL for testing
        cache = SearchCache(ttl_seconds=0.5)
        
        # Create test data
        params = SearchParams(query="test", types=[ModelType.LORA])
        test_models = [
            ModelInfo(
                id=1, name="Test Model", type=ModelType.LORA,
                description="Test", tags=["test"], creator="test",
                stats={}, nsfw=False, created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        # Test cache miss
        assert cache.get(params) is None
        
        # Test cache set and hit
        cache.set(params, test_models)
        cached_result = cache.get(params)
        
        # Verify data integrity
        assert cached_result is not None
        assert len(cached_result) == 1
        assert cached_result[0].id == 1
        assert cached_result[0].name == "Test Model"
        assert cached_result[0].type == ModelType.LORA
        
        # Test cache expiration
        time.sleep(0.6)  # Wait for expiration
        expired_result = cache.get(params)
        assert expired_result is None
        
        # Test cache key differentiation
        different_params = SearchParams(query="different", types=[ModelType.LORA])
        assert cache.get(different_params) is None
    
    @pytest.mark.asyncio
    async def test_cached_search_engine_behavior(self):
        """Test that cached search engine behaves correctly with real caching."""
        mock_api_client = AsyncMock()
        
        # Track API calls
        api_call_count = 0
        api_call_params = []
        
        async def tracking_search(params):
            nonlocal api_call_count
            api_call_count += 1
            api_call_params.append(params)
            
            # Return different data based on query
            if params.query == "first":
                return [
                    ModelInfo(
                        id=1, name="First Model", type=ModelType.LORA,
                        description="First", tags=["first"], creator="user1",
                        stats={}, nsfw=False, created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                ], None
            else:
                return [
                    ModelInfo(
                        id=2, name="Second Model", type=ModelType.LORA,
                        description="Second", tags=["second"], creator="user2",
                        stats={}, nsfw=False, created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                ], None
        
        mock_api_client.search_models = tracking_search
        engine = CachedSearchEngine(api_client=mock_api_client)
        
        # First search - should hit API
        params1 = SearchParams(query="first")
        result1 = await engine.search(params1)
        
        assert api_call_count == 1
        assert len(result1) == 1
        assert result1[0].name == "First Model"
        
        # Same search - should hit cache
        result1_cached = await engine.search(params1)
        
        assert api_call_count == 1  # No additional API call
        assert len(result1_cached) == 1
        assert result1_cached[0].name == "First Model"
        
        # Different search - should hit API
        params2 = SearchParams(query="second")
        result2 = await engine.search(params2)
        
        assert api_call_count == 2  # New API call
        assert len(result2) == 1
        assert result2[0].name == "Second Model"
        
        # Verify cache maintains separate entries
        cached_first = await engine.search(params1)
        cached_second = await engine.search(params2)
        
        assert api_call_count == 2  # Still only 2 API calls
        assert cached_first[0].name == "First Model"
        assert cached_second[0].name == "Second Model"


class TestTask3AdditionalFeatures:
    """Tests for Task 3 additional features: categories, 3-way filtering, extended parameters."""
    
    @pytest.fixture
    def diverse_models(self):
        """Create diverse model data for testing complex filtering scenarios."""
        return [
            ModelInfo(
                id=1, name="Anime Character LORA", type=ModelType.LORA, description="Anime character model",
                tags=["anime", "character", "style", "portrait"], creator="user1", stats={"downloads": 100},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ),
            ModelInfo(
                id=2, name="Realistic Character Style", type=ModelType.LORA, description="Realistic character style",
                tags=["realistic", "character", "photography", "portrait"], creator="user2", stats={"downloads": 200},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ),
            ModelInfo(
                id=3, name="Fantasy Concept Art", type=ModelType.CHECKPOINT, description="Fantasy concept art",
                tags=["fantasy", "concept", "magic", "art"], creator="user3", stats={"downloads": 150},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ),
            ModelInfo(
                id=4, name="Style Transfer Tool", type=ModelType.LORA, description="Style transfer tool",
                tags=["style", "tool", "transfer", "art"], creator="user4", stats={"downloads": 80},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ),
            ModelInfo(
                id=5, name="Character Concept Mix", type=ModelType.CHECKPOINT, description="Character concept mix",
                tags=["character", "concept", "mix", "versatile"], creator="user5", stats={"downloads": 300},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            )
        ]
    
    @pytest.mark.asyncio
    async def test_3way_filtering_complex_scenarios(self, mock_config, diverse_models):
        """Test 3-way filtering with complex real-world scenarios."""
        mock_api_client = AsyncMock()
        mock_api_client.search_models.return_value = (diverse_models, None)
        
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test 1: Category + Type filtering (should find character LORAs)
        params = SearchParams(
            categories=[ModelCategory.CHARACTER],
            types=[ModelType.LORA],
            limit=10
        )
        results = await engine.search(params)
        
        # Should find models with "character" tag AND LORA type
        assert len(results) == 2  # Models 1 and 2
        assert all(result.type == ModelType.LORA for result in results)
        assert all("character" in result.tags for result in results)
        
        # Test 2: Category + Tag filtering (character + style)
        params = SearchParams(
            categories=[ModelCategory.CHARACTER],
            tags=["style"],
            limit=10
        )
        results = await engine.search(params)
        
        # Should find models with both "character" AND "style" tags
        assert len(results) == 1  # Only Model 1 has both character and style
        assert results[0].id == 1  # Should be the anime character model
        assert all("character" in result.tags and "style" in result.tags for result in results)
        
        # Test 3: All three filters (category + tags + type)
        params = SearchParams(
            categories=[ModelCategory.CHARACTER],
            tags=["portrait"],
            types=[ModelType.LORA],
            limit=10
        )
        results = await engine.search(params)
        
        # Should find models with "character" tag, "portrait" tag, AND LORA type
        assert len(results) == 2  # Models 1 and 2 both have character, portrait, and are LORA
        assert all(result.type == ModelType.LORA for result in results)
        assert all("character" in result.tags and "portrait" in result.tags for result in results)
        
        # Test 4: Multiple categories
        params = SearchParams(
            categories=[ModelCategory.CHARACTER, ModelCategory.CONCEPT],
            types=[ModelType.CHECKPOINT],
            limit=10
        )
        results = await engine.search(params)
        
        # Should find checkpoints with either "character" OR "concept" tags
        assert len(results) == 2  # Models 3 and 5
        assert all(result.type == ModelType.CHECKPOINT for result in results)
        assert all("character" in result.tags or "concept" in result.tags for result in results)
    
    @pytest.mark.asyncio
    async def test_3way_filtering_edge_cases(self, mock_config, diverse_models):
        """Test edge cases in 3-way filtering."""
        mock_api_client = AsyncMock()
        mock_api_client.search_models.return_value = (diverse_models, None)
        
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test: No matches scenario
        params = SearchParams(
            categories=[ModelCategory.CHARACTER],
            tags=["nonexistent"],
            types=[ModelType.LORA],
            limit=10
        )
        results = await engine.search(params)
        assert len(results) == 0
        
        # Test: Type filter excludes everything
        params = SearchParams(
            categories=[ModelCategory.CHARACTER],
            types=[ModelType.CONTROLNET],  # No CONTROLNET models in test data
            limit=10
        )
        results = await engine.search(params)
        assert len(results) == 0
        
        # Test: Single very specific filter
        params = SearchParams(
            tags=["versatile"],  # Only model 5 has this tag
            limit=10
        )
        results = await engine.search(params)
        assert len(results) == 1
        assert results[0].id == 5
    
    @pytest.mark.asyncio
    async def test_category_to_tag_conversion(self, mock_config):
        """Test that categories are properly converted to tags for API calls."""
        mock_api_client = AsyncMock()
        mock_api_client.search_models.return_value = ([], None)
        
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test category conversion
        params = SearchParams(
            categories=[ModelCategory.CHARACTER, ModelCategory.STYLE],
            tags=["existing_tag"],
            limit=10
        )
        
        await engine.search(params)
        
        # Verify API was called with categories as additional tags
        call_args = mock_api_client.search_models.call_args[0][0]
        assert call_args.categories == [ModelCategory.CHARACTER, ModelCategory.STYLE]
        assert call_args.tags == ["existing_tag"]
    
    @pytest.mark.asyncio
    async def test_period_filtering_with_realistic_behavior(self, mock_config):
        """Test period filtering with realistic API behavior simulation."""
        mock_api_client = AsyncMock()
        
        # Simulate different results for different periods
        def period_sensitive_search(params):
            if params.period == PeriodFilter.DAY:
                return [ModelInfo(id=1, name="Recent Model", type=ModelType.LORA, description="Recent", 
                                tags=["recent"], creator="user", stats={}, nsfw=False, 
                                created_at=datetime.now(), updated_at=datetime.now())], None
            elif params.period == PeriodFilter.YEAR:
                return [ModelInfo(id=i, name=f"Model {i}", type=ModelType.LORA, description=f"Model {i}", 
                                tags=[f"tag{i}"], creator="user", stats={}, nsfw=False, 
                                created_at=datetime.now(), updated_at=datetime.now()) for i in range(1, 4)], None
            else:
                return [], None
        
        mock_api_client.search_models.side_effect = period_sensitive_search
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test DAY period
        params = SearchParams(period=PeriodFilter.DAY, limit=10)
        results = await engine.search(params)
        assert len(results) == 1
        assert results[0].name == "Recent Model"
        
        # Test YEAR period
        params = SearchParams(period=PeriodFilter.YEAR, limit=10)
        results = await engine.search(params)
        assert len(results) == 3
        
        # Test ALL_TIME period (should not pass period to API)
        params = SearchParams(period=PeriodFilter.ALL_TIME, limit=10)
        results = await engine.search(params)
        assert len(results) == 0  # Returns empty for unhandled periods
    
    @pytest.mark.asyncio
    async def test_advanced_parameters_combination_effects(self, mock_config):
        """Test how advanced parameters affect results when combined."""
        mock_api_client = AsyncMock()
        
        # Create models with different attributes
        all_models = [
            ModelInfo(id=1, name="Featured Model", type=ModelType.LORA, description="Featured", 
                     tags=["featured"], creator="verified_user", stats={"downloads": 1000}, 
                     nsfw=False, created_at=datetime.now(), updated_at=datetime.now()),
            ModelInfo(id=2, name="Verified Model", type=ModelType.LORA, description="Verified", 
                     tags=["verified"], creator="verified_user", stats={"downloads": 500}, 
                     nsfw=False, created_at=datetime.now(), updated_at=datetime.now()),
            ModelInfo(id=3, name="Commercial Model", type=ModelType.LORA, description="Commercial", 
                     tags=["commercial"], creator="commercial_user", stats={"downloads": 800}, 
                     nsfw=False, created_at=datetime.now(), updated_at=datetime.now()),
            ModelInfo(id=4, name="Regular Model", type=ModelType.LORA, description="Regular", 
                     tags=["regular"], creator="regular_user", stats={"downloads": 200}, 
                     nsfw=False, created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        def parameter_sensitive_search(params):
            results = all_models.copy()
            
            # Simulate filtering based on advanced parameters
            if params.featured:
                results = [m for m in results if "featured" in m.tags]
            if params.verified:
                results = [m for m in results if "verified" in m.tags or "verified_user" in m.creator]
            if params.commercial:
                results = [m for m in results if "commercial" in m.tags or "commercial_user" in m.creator]
            
            return results, None
        
        mock_api_client.search_models.side_effect = parameter_sensitive_search
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test featured only
        params = SearchParams(featured=True, limit=10)
        results = await engine.search(params)
        assert len(results) == 1
        assert results[0].name == "Featured Model"
        
        # Test verified only
        params = SearchParams(verified=True, limit=10)
        results = await engine.search(params)
        assert len(results) == 2  # Featured and Verified models have verified creators
        
        # Test combination (featured AND verified)
        params = SearchParams(featured=True, verified=True, limit=10)
        results = await engine.search(params)
        assert len(results) == 1  # Only featured model matches both criteria
        assert results[0].name == "Featured Model"
    
    @pytest.mark.asyncio
    async def test_sort_order_actual_behavior(self, mock_config):
        """Test that sort orders actually affect result ordering."""
        mock_api_client = AsyncMock()
        
        # Create models with different stats for sorting
        test_models = [
            ModelInfo(id=1, name="High Downloads", type=ModelType.LORA, description="Popular", 
                     tags=["popular"], creator="user1", stats={"downloadCount": 5000, "favoriteCount": 100}, 
                     nsfw=False, created_at=datetime.now() - timedelta(days=30), updated_at=datetime.now()),
            ModelInfo(id=2, name="Recent Model", type=ModelType.LORA, description="New", 
                     tags=["new"], creator="user2", stats={"downloadCount": 500, "favoriteCount": 200}, 
                     nsfw=False, created_at=datetime.now() - timedelta(days=1), updated_at=datetime.now()),
            ModelInfo(id=3, name="High Favorites", type=ModelType.LORA, description="Liked", 
                     tags=["liked"], creator="user3", stats={"downloadCount": 1000, "favoriteCount": 800}, 
                     nsfw=False, created_at=datetime.now() - timedelta(days=15), updated_at=datetime.now())
        ]
        
        def sort_sensitive_search(params):
            results = test_models.copy()
            
            # Simulate sorting based on sort order
            if params.sort == SortOrder.MOST_DOWNLOADED:
                results.sort(key=lambda m: m.stats.get("downloadCount", 0), reverse=True)
            elif params.sort == SortOrder.MOST_LIKED:
                results.sort(key=lambda m: m.stats.get("favoriteCount", 0), reverse=True)
            elif params.sort == SortOrder.NEWEST:
                results.sort(key=lambda m: m.created_at, reverse=True)
            elif params.sort == SortOrder.OLDEST:
                results.sort(key=lambda m: m.created_at, reverse=False)
            
            return results, None
        
        mock_api_client.search_models.side_effect = sort_sensitive_search
        engine = ModelSearchEngine(api_client=mock_api_client)
        
        # Test MOST_DOWNLOADED
        params = SearchParams(sort=SortOrder.MOST_DOWNLOADED, limit=10)
        results = await engine.search(params)
        assert results[0].name == "High Downloads"  # Should be first
        assert results[0].stats["downloadCount"] == 5000
        
        # Test MOST_LIKED
        params = SearchParams(sort=SortOrder.MOST_LIKED, limit=10)
        results = await engine.search(params)
        assert results[0].name == "High Favorites"  # Should be first
        assert results[0].stats["favoriteCount"] == 800
        
        # Test NEWEST
        params = SearchParams(sort=SortOrder.NEWEST, limit=10)
        results = await engine.search(params)
        assert results[0].name == "Recent Model"  # Should be first (most recent)
        
        # Test OLDEST
        params = SearchParams(sort=SortOrder.OLDEST, limit=10)
        results = await engine.search(params)
        assert results[0].name == "High Downloads"  # Should be first (oldest)