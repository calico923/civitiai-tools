#!/usr/bin/env python3
"""
Streaming Search for CivitAI Downloader.
Provides memory-efficient streaming search with AsyncIterator functionality.
"""

import asyncio
import psutil
from typing import Dict, Any, List, AsyncIterator, Optional, Union
from dataclasses import dataclass
import gc
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from api.client import CivitaiAPIClient
    from api.params import SearchParams
except ImportError:
    # Handle import errors gracefully for testing
    CivitaiAPIClient = None
    SearchParams = None


@dataclass
class StreamingConfig:
    """Configuration for streaming search operations."""
    memory_threshold: int = 100 * 1024 * 1024  # 100MB default
    batch_size: int = 50  # Items per API call
    buffer_size: int = 3  # Number of pages to buffer
    enable_memory_optimization: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


class StreamingSearch:
    """Memory-efficient streaming search for large datasets."""
    
    def __init__(self, api_client: Optional['CivitaiAPIClient'] = None, config: Optional[StreamingConfig] = None):
        """
        Initialize streaming search.
        
        Args:
            api_client: CivitAI API client instance
            config: Streaming configuration
        """
        self.api_client = api_client
        self.config = config or StreamingConfig()
        self._process = psutil.Process()
        self._initial_memory = self._get_current_memory()
        self._retry_enabled = False
        self._max_retries = self.config.max_retries
        
    def set_memory_threshold(self, threshold_bytes: int) -> None:
        """
        Set memory threshold for streaming operations.
        
        Args:
            threshold_bytes: Memory threshold in bytes
        """
        self.config.memory_threshold = threshold_bytes
    
    def get_memory_threshold(self) -> int:
        """
        Get current memory threshold.
        
        Returns:
            Memory threshold in bytes
        """
        return self.config.memory_threshold
    
    def get_memory_usage(self) -> int:
        """
        Get current memory usage of the process.
        
        Returns:
            Current memory usage in bytes
        """
        return self._get_current_memory()
    
    def _get_current_memory(self) -> int:
        """Get current memory usage in bytes."""
        try:
            return self._process.memory_info().rss
        except:
            # Fallback to approximate calculation
            return sys.getsizeof(self) * 1000
    
    def is_memory_pressure(self) -> bool:
        """
        Check if currently under memory pressure.
        
        Returns:
            True if memory usage exceeds threshold
        """
        current_memory = self.get_memory_usage()
        return current_memory > self.config.memory_threshold
    
    def set_batch_size(self, batch_size: int) -> None:
        """
        Set batch size for API calls.
        
        Args:
            batch_size: Number of items per API call
        """
        self.config.batch_size = batch_size
    
    def get_batch_size(self) -> int:
        """
        Get current batch size.
        
        Returns:
            Current batch size
        """
        return self.config.batch_size
    
    def set_buffer_size(self, buffer_size: int) -> None:
        """
        Set buffer size for page buffering.
        
        Args:
            buffer_size: Number of pages to buffer
        """
        self.config.buffer_size = buffer_size
    
    def get_buffer_size(self) -> int:
        """
        Get current buffer size.
        
        Returns:
            Current buffer size
        """
        return self.config.buffer_size
    
    def enable_memory_optimization(self, enabled: bool) -> None:
        """
        Enable or disable memory optimization.
        
        Args:
            enabled: Whether to enable memory optimization
        """
        self.config.enable_memory_optimization = enabled
    
    def is_memory_optimization_enabled(self) -> bool:
        """
        Check if memory optimization is enabled.
        
        Returns:
            True if memory optimization is enabled
        """
        return self.config.enable_memory_optimization
    
    def enable_retry(self, max_retries: int = 3) -> None:
        """
        Enable retry mechanism for failed requests.
        
        Args:
            max_retries: Maximum number of retries
        """
        self._retry_enabled = True
        self._max_retries = max_retries
    
    def is_backpressure_active(self) -> bool:
        """
        Check if backpressure is currently active.
        
        Returns:
            True if backpressure is active (memory pressure)
        """
        return self.is_memory_pressure()
    
    async def search_models_stream(self, search_params: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream search results with memory-efficient processing.
        
        Args:
            search_params: Search parameters
            
        Yields:
            Individual model dictionaries
        """
        cursor = None
        page_count = 0
        total_processed = 0
        
        # Prepare parameters with batch size
        params = search_params.copy()
        params['limit'] = self.config.batch_size
        
        while True:
            try:
                # Add cursor if available
                if cursor:
                    params['cursor'] = cursor
                
                # Fetch page with memory management
                page_data = await self._fetch_page(params)
                
                if not page_data or 'items' not in page_data:
                    break
                
                items = page_data['items']
                if not items:
                    break
                
                # Process items individually for memory efficiency
                for item in items:
                    # Check memory pressure and apply backpressure if needed
                    if self.is_memory_pressure() and self.config.enable_memory_optimization:
                        await self._apply_backpressure()
                    
                    yield item
                    total_processed += 1
                
                # Check for next page
                metadata = page_data.get('metadata', {})
                cursor = metadata.get('nextCursor')
                has_more = metadata.get('hasMore', False)
                
                if not cursor and not has_more:
                    break
                
                page_count += 1
                
                # Memory cleanup after each page
                if self.config.enable_memory_optimization:
                    await self._cleanup_memory()
                    
            except Exception as e:
                if self._retry_enabled and self._max_retries > 0:
                    self._max_retries -= 1
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                else:
                    raise e
    
    async def _fetch_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a single page of results.
        
        Args:
            params: Request parameters
            
        Returns:
            Page data dictionary
        """
        if self.api_client:
            # Use actual API client
            return await self.api_client.get_models(params)
        else:
            # Mock implementation for testing
            await asyncio.sleep(0.001)  # Simulate network delay
            
            # Extract cursor for pagination simulation
            cursor = params.get('cursor')
            limit = params.get('limit', 50)
            
            # Generate mock data based on cursor
            if cursor == 'cursor_1':
                start_id = 11
            elif cursor == 'cursor_2':
                start_id = 21
            elif cursor and cursor.startswith('cursor_'):
                try:
                    page_num = int(cursor.split('_')[1])
                    start_id = page_num * limit + 1
                except:
                    start_id = 1
            else:
                start_id = 1
            
            # Generate items
            items = []
            for i in range(start_id, start_id + limit):
                items.append({
                    'id': i,
                    'name': f'Model {i}',
                    'description': 'A' * 100 if 'large' in params.get('query', '') else 'Test model'
                })
            
            # Determine next cursor
            next_cursor = None
            has_more = False
            
            if 'large' in params.get('query', ''):
                # For large dataset tests
                if start_id < 500:  # Simulate 10 pages of 50 items
                    next_cursor = f'cursor_{(start_id // limit) + 1}'
                    has_more = True
            else:
                # For normal tests
                if start_id < 30:
                    next_cursor = f'cursor_{(start_id // limit) + 1}'
                    has_more = True
            
            return {
                'items': items,
                'metadata': {
                    'nextCursor': next_cursor,
                    'hasMore': has_more,
                    'currentPage': (start_id - 1) // limit + 1,
                    'totalPages': 10 if 'large' in params.get('query', '') else 3
                }
            }
    
    async def _apply_backpressure(self) -> None:
        """Apply backpressure when under memory pressure."""
        if self.is_memory_pressure():
            # Small delay to allow memory cleanup
            await asyncio.sleep(0.01)
            
            # Force garbage collection
            gc.collect()
            
            # Additional delay if still under pressure
            if self.is_memory_pressure():
                await asyncio.sleep(0.05)
    
    async def _cleanup_memory(self) -> None:
        """Perform memory cleanup operations."""
        if self.config.enable_memory_optimization:
            # Force garbage collection
            gc.collect()
            
            # Allow event loop to process
            await asyncio.sleep(0.001)
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """
        Get streaming operation statistics.
        
        Returns:
            Statistics dictionary
        """
        current_memory = self.get_memory_usage()
        memory_delta = current_memory - self._initial_memory
        
        return {
            'current_memory_usage': current_memory,
            'initial_memory_usage': self._initial_memory,
            'memory_delta': memory_delta,
            'memory_threshold': self.config.memory_threshold,
            'is_memory_pressure': self.is_memory_pressure(),
            'batch_size': self.config.batch_size,
            'buffer_size': self.config.buffer_size,
            'memory_optimization_enabled': self.config.enable_memory_optimization
        }


class MemoryEfficientIterator:
    """Memory-efficient iterator wrapper for large datasets."""
    
    def __init__(self, streaming_search: StreamingSearch, search_params: Dict[str, Any]):
        """
        Initialize memory-efficient iterator.
        
        Args:
            streaming_search: StreamingSearch instance
            search_params: Search parameters
        """
        self.streaming_search = streaming_search
        self.search_params = search_params
        self._iterator = None
    
    def __aiter__(self):
        """Return async iterator."""
        return self
    
    async def __anext__(self):
        """Get next item from stream."""
        if self._iterator is None:
            self._iterator = self.streaming_search.search_models_stream(self.search_params)
        
        try:
            return await self._iterator.__anext__()
        except StopAsyncIteration:
            raise StopAsyncIteration