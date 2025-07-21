#!/usr/bin/env python3
"""
History Manager - Download history tracking and duplicate prevention.
Implements requirements 6.1 and 6.2: Download history tracking and duplicate prevention.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))

from database import DatabaseManager

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Download history manager with duplicate prevention.
    Implements requirement 6.1: Download history tracking.
    Implements requirement 6.2: Duplicate prevention system.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize history manager.
        
        Args:
            db_manager: Database manager instance (creates new if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        
        # In-memory cache for quick duplicate checks
        self._downloaded_cache: Set[tuple] = set()
        self._cache_loaded = False
        
        # Load existing downloads into cache
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load existing downloads into memory cache for fast lookups."""
        try:
            downloads = self.db_manager.get_download_history(limit=10000)  # Load recent downloads
            
            self._downloaded_cache = {
                (download['model_id'], download['file_id'])
                for download in downloads
                if download['status'] == 'completed'
            }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._downloaded_cache)} downloads into cache")
            
        except Exception as e:
            logger.error(f"Failed to load download cache: {e}")
            self._downloaded_cache = set()
            self._cache_loaded = False
    
    def record_download(self, download_info: Dict[str, Any]) -> bool:
        """
        Record a download in history per requirement 6.1.
        
        Args:
            download_info: Download information dictionary with keys:
                - model_id: Model ID
                - file_id: File ID  
                - file_name: Name of downloaded file
                - file_path: Local path where file was saved
                - download_url: Original download URL
                - file_size: Size in bytes
                - hash_sha256: SHA256 hash for verification
                - status: Download status ('completed', 'failed', etc.)
                - downloaded_at: Timestamp of download
                
        Returns:
            True if successfully recorded
        """
        try:
            # Ensure required fields are present
            required_fields = ['model_id', 'file_id', 'file_name']
            for field in required_fields:
                if field not in download_info:
                    logger.error(f"Missing required field '{field}' in download info")
                    return False
            
            # Set default values
            download_data = {
                'model_id': download_info['model_id'],
                'file_id': download_info['file_id'],
                'file_name': download_info['file_name'],
                'file_path': download_info.get('file_path'),
                'download_url': download_info.get('download_url'),
                'file_size': download_info.get('file_size', 0),
                'hash_sha256': download_info.get('hash_sha256'),
                'status': download_info.get('status', 'completed'),
                'downloaded_at': download_info.get('downloaded_at', datetime.now().isoformat())
            }
            
            # Record in database
            success = self.db_manager.record_download(download_data)
            
            if success and download_data['status'] == 'completed':
                # Update in-memory cache
                cache_key = (download_data['model_id'], download_data['file_id'])
                self._downloaded_cache.add(cache_key)
                
                logger.info(f"Recorded download: {download_data['file_name']} "
                          f"(Model: {download_data['model_id']}, File: {download_data['file_id']})")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to record download: {e}")
            return False
    
    def prevent_duplicates(self, model_id: int, file_id: int) -> bool:
        """
        Check if a download would be a duplicate per requirement 6.2.
        
        Args:
            model_id: Model ID to check
            file_id: File ID to check
            
        Returns:
            True if this would be a duplicate (already downloaded)
            False if safe to download
        """
        try:
            # First check in-memory cache for fast lookup
            cache_key = (model_id, file_id)
            if cache_key in self._downloaded_cache:
                logger.debug(f"Duplicate detected in cache: Model {model_id}, File {file_id}")
                return True
            
            # Fallback to database check if cache not loaded or miss
            if not self._cache_loaded:
                is_duplicate = self.db_manager.is_downloaded(model_id, file_id)
                if is_duplicate:
                    # Add to cache for future checks
                    self._downloaded_cache.add(cache_key)
                    logger.debug(f"Duplicate detected in database: Model {model_id}, File {file_id}")
                return is_duplicate
            
            # Not found in cache and cache is loaded = not a duplicate
            return False
            
        except Exception as e:
            logger.error(f"Failed to check duplicates for Model {model_id}, File {file_id}: {e}")
            # On error, assume it's not a duplicate to allow download attempt
            return False
    
    def is_already_downloaded(self, model_id: int, file_id: int) -> bool:
        """
        Alias for prevent_duplicates for clearer API.
        
        Args:
            model_id: Model ID to check
            file_id: File ID to check
            
        Returns:
            True if already downloaded
        """
        return self.prevent_duplicates(model_id, file_id)
    
    def get_download_history(self, limit: int = 100, model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get download history with optional filtering.
        
        Args:
            limit: Maximum number of records to return
            model_id: Optional model ID to filter by
            
        Returns:
            List of download history records
        """
        try:
            if model_id is not None:
                # Get model-specific history
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM downloads 
                        WHERE model_id = ?
                        ORDER BY downloaded_at DESC 
                        LIMIT ?
                    """, (model_id, limit))
                    
                    return [dict(row) for row in cursor.fetchall()]
            else:
                # Get general history
                return self.db_manager.get_download_history(limit)
                
        except Exception as e:
            logger.error(f"Failed to get download history: {e}")
            return []
    
    def get_download_stats(self) -> Dict[str, Any]:
        """
        Get download statistics.
        
        Returns:
            Dictionary with download statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total downloads
                cursor.execute("SELECT COUNT(*) FROM downloads WHERE status = 'completed'")
                total_downloads = cursor.fetchone()[0]
                
                # Total file size
                cursor.execute("SELECT SUM(file_size) FROM downloads WHERE status = 'completed'")
                total_size = cursor.fetchone()[0] or 0
                
                # Recent downloads (last 7 days)
                cursor.execute("""
                    SELECT COUNT(*) FROM downloads 
                    WHERE status = 'completed' 
                    AND datetime(downloaded_at) > datetime('now', '-7 days')
                """)
                recent_downloads = cursor.fetchone()[0]
                
                # Unique models downloaded
                cursor.execute("SELECT COUNT(DISTINCT model_id) FROM downloads WHERE status = 'completed'")
                unique_models = cursor.fetchone()[0]
                
                return {
                    'total_downloads': total_downloads,
                    'total_size_bytes': total_size,
                    'recent_downloads_7d': recent_downloads,
                    'unique_models': unique_models,
                    'cache_size': len(self._downloaded_cache)
                }
                
        except Exception as e:
            logger.error(f"Failed to get download stats: {e}")
            return {
                'total_downloads': 0,
                'total_size_bytes': 0,
                'recent_downloads_7d': 0,
                'unique_models': 0,
                'cache_size': len(self._downloaded_cache)
            }
    
    def cleanup_failed_downloads(self, max_age_days: int = 7) -> int:
        """
        Clean up old failed download records.
        
        Args:
            max_age_days: Maximum age in days for failed records
            
        Returns:
            Number of records cleaned up
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM downloads 
                    WHERE status = 'failed' 
                    AND datetime(created_at) < datetime('now', '-{} days')
                """.format(max_age_days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old failed download records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup failed downloads: {e}")
            return 0
    
    def refresh_cache(self) -> None:
        """Refresh the in-memory download cache."""
        self._load_cache()
    
    def clear_cache(self) -> None:
        """Clear the in-memory download cache."""
        self._downloaded_cache.clear()
        self._cache_loaded = False


if __name__ == "__main__":
    # Test history manager
    print("Testing History Manager...")
    
    # Create test manager
    history_manager = HistoryManager()
    
    # Test download recording
    test_download = {
        'model_id': 12345,
        'file_id': 67890,
        'file_name': 'test_model.safetensors',
        'file_path': './downloads/test_model.safetensors',
        'download_url': 'https://example.com/test.safetensors',
        'file_size': 1024*1024,
        'hash_sha256': 'dummy_hash',
        'status': 'completed'
    }
    
    record_success = history_manager.record_download(test_download)
    print(f"Download recording: {'✓' if record_success else '✗'}")
    
    # Test duplicate prevention
    is_duplicate = history_manager.prevent_duplicates(12345, 67890)
    print(f"Duplicate prevention: {'✓' if is_duplicate else '✗'}")
    
    # Test new download (should not be duplicate)
    is_new_duplicate = history_manager.prevent_duplicates(12345, 99999)
    print(f"New download check: {'✓' if not is_new_duplicate else '✗'}")
    
    # Test statistics
    stats = history_manager.get_download_stats()
    print(f"Statistics retrieval: {'✓' if stats['total_downloads'] > 0 else '✗'}")
    
    print("History Manager test completed!")