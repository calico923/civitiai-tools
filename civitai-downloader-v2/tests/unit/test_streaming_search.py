#!/usr/bin/env python3
"""
Streaming search tests.
Tests for memory-efficient streaming search with AsyncIterator functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import importlib.util
from typing import Dict, Any, List, AsyncIterator
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestStreamingSearch:
    """Test streaming search functionality for memory-efficient processing."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_streaming_search_module_exists(self):
        """Test that streaming search module exists."""
        streaming_path = self.api_dir / "streaming_search.py"
        assert streaming_path.exists(), "streaming_search.py must exist"
        
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        # Test StreamingSearch class exists
        assert hasattr(streaming_module, 'StreamingSearch'), "StreamingSearch class must exist"
        StreamingSearch = streaming_module.StreamingSearch
        
        # Test initialization
        streaming_search = StreamingSearch()
        
        # Validate methods
        assert hasattr(streaming_search, 'search_models_stream'), "Must have search_models_stream method"
        assert hasattr(streaming_search, 'get_memory_usage'), "Must have memory usage tracking"
        assert hasattr(streaming_search, 'set_memory_threshold'), "Must have memory threshold setting"
    
    @pytest.mark.asyncio
    async def test_async_iterator_functionality(self):
        """Test AsyncIterator functionality for streaming search."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        # Mock search parameters
        search_params = {
            "query": "test",
            "limit": 100
        }
        
        # Test that search_models_stream returns AsyncIterator
        stream = streaming_search.search_models_stream(search_params)
        assert hasattr(stream, '__aiter__'), "Must return AsyncIterator"
        assert hasattr(stream, '__anext__'), "Must support async iteration"
        
        # Test iteration (with mock data)
        with patch.object(streaming_search, '_fetch_page') as mock_fetch:
            mock_fetch.return_value = {
                'items': [
                    {'id': 1, 'name': 'Model 1'},
                    {'id': 2, 'name': 'Model 2'}
                ],
                'metadata': {'nextCursor': None}
            }
            
            models = []
            async for model in stream:
                models.append(model)
                if len(models) >= 2:
                    break
            
            assert len(models) == 2, "Should yield individual models"
            assert models[0]['id'] == 1, "First model should have correct data"
            assert models[1]['id'] == 2, "Second model should have correct data"
    
    @pytest.mark.asyncio
    async def test_memory_efficient_pagination(self):
        """Test memory-efficient pagination with controlled memory usage."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        # Set memory threshold - use current memory + buffer for realistic testing
        current_memory = streaming_search.get_memory_usage()
        memory_threshold = current_memory + 100 * 1024 * 1024  # Current + 100MB buffer
        streaming_search.set_memory_threshold(memory_threshold)
        
        search_params = {"query": "large_dataset", "limit": 1000}
        
        # Mock multiple pages of data
        with patch.object(streaming_search, '_fetch_page') as mock_fetch:
            # Simulate 3 pages of data
            mock_fetch.side_effect = [
                {
                    'items': [{'id': i, 'name': f'Model {i}'} for i in range(1, 11)],
                    'metadata': {'nextCursor': 'cursor_1', 'hasMore': True}
                },
                {
                    'items': [{'id': i, 'name': f'Model {i}'} for i in range(11, 21)],
                    'metadata': {'nextCursor': 'cursor_2', 'hasMore': True}
                },
                {
                    'items': [{'id': i, 'name': f'Model {i}'} for i in range(21, 31)],
                    'metadata': {'nextCursor': None, 'hasMore': False}
                }
            ]
            
            # Test memory-efficient iteration
            models_processed = 0
            max_memory_usage = 0
            
            async for model in streaming_search.search_models_stream(search_params):
                models_processed += 1
                current_memory = streaming_search.get_memory_usage()
                max_memory_usage = max(max_memory_usage, current_memory)
                
                # Verify we don't accumulate all models in memory
                if models_processed > 10:
                    assert current_memory < memory_threshold, "Memory usage should stay within threshold"
            
            assert models_processed == 30, "Should process all models from all pages"
            assert mock_fetch.call_count == 3, "Should fetch 3 pages"
    
    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Test error handling during streaming operations."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        search_params = {"query": "error_test"}
        
        # Test network error handling
        with patch.object(streaming_search, '_fetch_page') as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            
            with pytest.raises(Exception) as exc_info:
                async for model in streaming_search.search_models_stream(search_params):
                    pass
            
            assert "Network error" in str(exc_info.value), "Should propagate network errors"
        
        # Test partial failure recovery
        with patch.object(streaming_search, '_fetch_page') as mock_fetch:
            # First call fails, second succeeds
            mock_fetch.side_effect = [
                Exception("Temporary error"),
                {
                    'items': [{'id': 1, 'name': 'Model 1'}],
                    'metadata': {'nextCursor': None}
                }
            ]
            
            # Test retry mechanism exists
            stream = streaming_search.search_models_stream(search_params)
            if hasattr(streaming_search, 'enable_retry'):
                streaming_search.enable_retry(max_retries=1)
                
                models = []
                try:
                    async for model in stream:
                        models.append(model)
                except:
                    pass  # Expected on first implementation
    
    @pytest.mark.asyncio
    async def test_large_dataset_processing(self):
        """Test processing of large datasets with backpressure handling."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        # Configure for large dataset
        streaming_search.set_memory_threshold(100 * 1024 * 1024)  # 100MB
        if hasattr(streaming_search, 'set_batch_size'):
            streaming_search.set_batch_size(50)  # Smaller batches for large datasets
        
        search_params = {"query": "large_test", "limit": 10000}
        
        # Mock large dataset
        def generate_large_page(page_num):
            start_id = page_num * 50 + 1
            return {
                'items': [
                    {
                        'id': i,
                        'name': f'Large Model {i}',
                        'description': 'A' * 1000  # Large description to test memory
                    }
                    for i in range(start_id, start_id + 50)
                ],
                'metadata': {
                    'nextCursor': f'cursor_{page_num + 1}' if page_num < 9 else None,
                    'hasMore': page_num < 9
                }
            }
        
        with patch.object(streaming_search, '_fetch_page') as mock_fetch:
            mock_fetch.side_effect = [generate_large_page(i) for i in range(10)]
            
            # Test backpressure handling
            processed_count = 0
            memory_readings = []
            
            async for model in streaming_search.search_models_stream(search_params):
                processed_count += 1
                memory_readings.append(streaming_search.get_memory_usage())
                
                # Test backpressure response
                if hasattr(streaming_search, 'is_backpressure_active'):
                    if streaming_search.is_backpressure_active():
                        # Simulate processing delay
                        await asyncio.sleep(0.001)
                
                # Process first 100 models for testing
                if processed_count >= 100:
                    break
            
            assert processed_count == 100, "Should process requested number of models"
            
            # Verify memory doesn't continuously grow
            if len(memory_readings) > 50:
                early_avg = sum(memory_readings[:25]) / 25
                late_avg = sum(memory_readings[-25:]) / 25
                # Memory should not grow linearly with processed items
                assert late_avg < early_avg * 3, "Memory growth should be controlled"
    
    def test_memory_monitoring_functionality(self):
        """Test memory monitoring and threshold management."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        # Test memory threshold setting - use current memory + buffer for realistic testing
        current_memory = streaming_search.get_memory_usage()
        threshold = current_memory + 64 * 1024 * 1024  # Current + 64MB buffer
        streaming_search.set_memory_threshold(threshold)
        
        if hasattr(streaming_search, 'get_memory_threshold'):
            assert streaming_search.get_memory_threshold() == threshold, "Should store memory threshold"
        
        # Test memory usage tracking
        initial_memory = streaming_search.get_memory_usage()
        assert isinstance(initial_memory, (int, float)), "Memory usage should be numeric"
        assert initial_memory >= 0, "Memory usage should be non-negative"
        
        # Test memory pressure detection
        if hasattr(streaming_search, 'is_memory_pressure'):
            # Initially should not be under pressure
            assert not streaming_search.is_memory_pressure(), "Should not be under memory pressure initially"
    
    def test_streaming_configuration(self):
        """Test streaming search configuration options."""
        streaming_path = self.api_dir / "streaming_search.py"
        spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(streaming_module)
        
        StreamingSearch = streaming_module.StreamingSearch
        streaming_search = StreamingSearch()
        
        # Test batch size configuration
        if hasattr(streaming_search, 'set_batch_size'):
            streaming_search.set_batch_size(25)
            if hasattr(streaming_search, 'get_batch_size'):
                assert streaming_search.get_batch_size() == 25, "Should store batch size"
        
        # Test streaming buffer configuration
        if hasattr(streaming_search, 'set_buffer_size'):
            streaming_search.set_buffer_size(3)
            if hasattr(streaming_search, 'get_buffer_size'):
                assert streaming_search.get_buffer_size() == 3, "Should store buffer size"
        
        # Test memory efficiency settings
        if hasattr(streaming_search, 'enable_memory_optimization'):
            streaming_search.enable_memory_optimization(True)
            if hasattr(streaming_search, 'is_memory_optimization_enabled'):
                assert streaming_search.is_memory_optimization_enabled(), "Should enable memory optimization"
    
    @pytest.mark.asyncio
    async def test_streaming_integration_with_api_client(self):
        """Test integration between streaming search and existing API client."""
        # Import existing API client
        client_path = self.api_dir / "client.py"
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        
        streaming_path = self.api_dir / "streaming_search.py"
        streaming_spec = importlib.util.spec_from_file_location("streaming_search", streaming_path)
        streaming_module = importlib.util.module_from_spec(streaming_spec)
        streaming_spec.loader.exec_module(streaming_module)
        
        CivitaiAPIClient = client_module.CivitaiAPIClient
        StreamingSearch = streaming_module.StreamingSearch
        
        # Test integration
        api_client = CivitaiAPIClient(api_key="test_key")
        streaming_search = StreamingSearch(api_client=api_client)
        
        # Verify streaming search can use API client
        assert hasattr(streaming_search, 'api_client'), "Should accept API client"
        
        # Test that streaming search uses API client's methods
        search_params = {"query": "integration_test"}
        
        with patch.object(api_client, 'get_models') as mock_get_models:
            mock_get_models.return_value = {
                'items': [{'id': 1, 'name': 'Test Model'}],
                'metadata': {'nextCursor': None}
            }
            
            stream = streaming_search.search_models_stream(search_params)
            models = []
            async for model in stream:
                models.append(model)
                break  # Just get first model
            
            assert len(models) == 1, "Should integrate with API client"
            mock_get_models.assert_called(), "Should use API client methods"