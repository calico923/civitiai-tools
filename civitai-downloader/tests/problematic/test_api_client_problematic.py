"""Problematic API client tests that over-mock business logic.

These tests have been moved here because they mock the _make_request method,
which bypasses all the core API client logic they're supposed to test.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import ClientResponseError

from src.api_client import CivitAIAPIClient
from src.interfaces import SearchParams, ModelType


class TestProblematicAPIClientTests:
    """Tests that over-mock business logic instead of testing it."""
    
    @pytest.mark.asyncio
    async def test_search_models_problematic(self, mock_config, mock_model_response):
        """Test model search - PROBLEMATIC VERSION."""
        client = CivitAIAPIClient(mock_config)
        
        # PROBLEM: Mocks the entire _make_request method, bypassing all logic
        client._make_request = AsyncMock(return_value={
            "items": [mock_model_response],
            "metadata": {"nextCursor": "next123"}
        })
        
        # Test search
        params = SearchParams(
            query="anime",
            types=[ModelType.LORA],
            limit=10
        )
        
        models, next_cursor = await client.search_models(params)
        
        # PROBLEM: Only tests that mock data comes back unchanged
        assert len(models) == 1
        assert models[0].id == 123456
        assert models[0].name == "Test Model"
        assert models[0].type == ModelType.LORA
        assert next_cursor == "next123"
    
    @pytest.mark.asyncio
    async def test_get_model_details_problematic(self, mock_config, mock_model_response):
        """Test getting model details - PROBLEMATIC VERSION."""
        client = CivitAIAPIClient(mock_config)
        
        # PROBLEM: Mocks the entire _make_request method
        client._make_request = AsyncMock(return_value=mock_model_response)
        
        # Test get details
        model = await client.get_model_details(123456)
        
        # PROBLEM: Only tests that mock data comes back unchanged
        assert model.id == 123456
        assert model.name == "Test Model"
        assert model.creator == "testuser"
        assert model.stats['downloadCount'] == 1000
    
    @pytest.mark.asyncio
    async def test_get_model_version_problematic(self, mock_config, mock_version_response):
        """Test getting model version - PROBLEMATIC VERSION."""
        client = CivitAIAPIClient(mock_config)
        
        # PROBLEM: Mocks the entire _make_request method
        client._make_request = AsyncMock(return_value=mock_version_response)
        
        # Test get version
        version = await client.get_model_version(789)
        
        # PROBLEM: Only tests that mock data comes back unchanged
        assert version.id == 789
        assert version.name == "v1.0"
        assert version.base_model == "SD 1.5"
        assert len(version.files) == 1
        assert version.files[0].size_bytes == 144320 * 1024
    
    @pytest.mark.asyncio
    async def test_context_manager_problematic(self, mock_config):
        """Test async context manager - PROBLEMATIC VERSION."""
        # PROBLEM: Tests implementation detail (session.closed) not functional behavior
        async with CivitAIAPIClient(mock_config) as client:
            assert client.session is not None
            assert client.headers['Authorization'] == 'Bearer test-api-key'
        
        # PROBLEM: Testing internal state, not behavior
        assert client.session.closed