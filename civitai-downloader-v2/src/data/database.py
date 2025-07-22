#!/usr/bin/env python3
"""
Database Manager - SQLite database management implementation.
Implements requirement 6.1: SQLite database for metadata storage.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLite database manager for CivitAI downloader metadata storage.
    Implements requirement 6.1: Complete metadata storage system.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path) if db_path else Path("./data/civitai_downloader.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Note: Database schema will be initialized in initialize() method
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database - async version for CLI compatibility."""
        if not self._initialized:
            self._init_database()
            self._initialized = True
    
    def _init_database(self) -> None:
        """Initialize database schema if not exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Models table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT,
                    description TEXT,
                    creator_id INTEGER,
                    creator_username TEXT,
                    nsfw BOOLEAN,
                    allowCommercialUse TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    raw_data TEXT,
                    UNIQUE(id)
                )
            """)
            
            # Downloads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER,
                    file_id INTEGER,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    download_url TEXT,
                    file_size INTEGER,
                    hash_sha256 TEXT,
                    status TEXT DEFAULT 'pending',
                    downloaded_at TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(model_id) REFERENCES models(id),
                    UNIQUE(model_id, file_id)
                )
            """)
            
            # Search history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    filters TEXT,
                    results_count INTEGER,
                    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Metadata cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        Get SQLite database connection with proper resource management.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    check_same_thread=False
                )
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                # Set row factory for dict-like access
                conn.row_factory = sqlite3.Row
                yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def store_model(self, model_data: Dict[str, Any]) -> bool:
        """
        Store model metadata in database.
        
        Args:
            model_data: Model data dictionary
            
        Returns:
            True if stored successfully
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO models (
                        id, name, type, description, creator_id, creator_username,
                        nsfw, allowCommercialUse, created_at, updated_at, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    model_data.get('id'),
                    model_data.get('name'),
                    model_data.get('type'),
                    model_data.get('description'),
                    model_data.get('creator', {}).get('id'),
                    model_data.get('creator', {}).get('username'),
                    model_data.get('nsfw'),
                    model_data.get('allowCommercialUse'),
                    model_data.get('createdAt'),
                    model_data.get('updatedAt'),
                    str(model_data)  # Store raw JSON as string
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store model {model_data.get('id')}: {e}")
            return False
    
    def get_model(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve model from database.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM models WHERE id = ?", (model_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get model {model_id}: {e}")
            return None
    
    def record_download(self, download_data: Dict[str, Any]) -> bool:
        """
        Record download information in database.
        
        Args:
            download_data: Download data dictionary
            
        Returns:
            True if recorded successfully
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO downloads (
                        model_id, file_id, file_name, file_path, download_url,
                        file_size, hash_sha256, status, downloaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    download_data.get('model_id'),
                    download_data.get('file_id'),
                    download_data.get('file_name'),
                    download_data.get('file_path'),
                    download_data.get('download_url'),
                    download_data.get('file_size'),
                    download_data.get('hash_sha256'),
                    download_data.get('status', 'completed'),
                    download_data.get('downloaded_at')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to record download: {e}")
            return False
    
    def is_downloaded(self, model_id: int, file_id: int) -> bool:
        """
        Check if a file has been downloaded.
        
        Args:
            model_id: Model ID
            file_id: File ID
            
        Returns:
            True if already downloaded
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM downloads 
                    WHERE model_id = ? AND file_id = ? AND status = 'completed'
                """, (model_id, file_id))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to check download status: {e}")
            return False
    
    def get_download_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent download history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of download records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM downloads 
                    ORDER BY downloaded_at DESC 
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get download history: {e}")
            return []
    
    def cleanup_old_cache(self, max_age_hours: int = 24) -> bool:
        """
        Clean up expired cache entries.
        
        Args:
            max_age_hours: Maximum age in hours for cache entries
            
        Returns:
            True if cleanup successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM metadata_cache 
                    WHERE datetime(created_at) < datetime('now', '-{} hours')
                """.format(max_age_hours))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return False
    
    def close(self) -> None:
        """Close database connections and cleanup."""
        # SQLite connections are closed automatically in context managers
        pass


if __name__ == "__main__":
    # Test database manager
    print("Testing Database Manager...")
    
    # Create test database
    test_db = DatabaseManager(Path("./test_db.sqlite"))
    
    # Test model storage
    test_model = {
        'id': 12345,
        'name': 'Test Model',
        'type': 'Checkpoint',
        'description': 'A test model',
        'creator': {'id': 123, 'username': 'testuser'},
        'nsfw': False,
        'allowCommercialUse': 'Sell',
        'createdAt': '2023-01-01T00:00:00Z',
        'updatedAt': '2023-01-01T00:00:00Z'
    }
    
    success = test_db.store_model(test_model)
    print(f"Model storage: {'✓' if success else '✗'}")
    
    # Test model retrieval
    retrieved = test_db.get_model(12345)
    print(f"Model retrieval: {'✓' if retrieved else '✗'}")
    
    # Test download recording
    test_download = {
        'model_id': 12345,
        'file_id': 67890,
        'file_name': 'test_model.safetensors',
        'file_path': './downloads/test_model.safetensors',
        'download_url': 'https://example.com/test.safetensors',
        'file_size': 1024*1024,
        'hash_sha256': 'dummy_hash',
        'status': 'completed',
        'downloaded_at': '2023-01-01T01:00:00Z'
    }
    
    download_success = test_db.record_download(test_download)
    print(f"Download recording: {'✓' if download_success else '✗'}")
    
    # Test duplicate check
    is_duplicate = test_db.is_downloaded(12345, 67890)
    print(f"Duplicate detection: {'✓' if is_duplicate else '✗'}")
    
    print("Database Manager test completed!")