#!/usr/bin/env python3
"""
Database Schema Manager - Centralized database schema initialization.
Eliminates code duplication across multiple components that need database initialization.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SchemaDefinition:
    """Definition of a database schema with tables and setup logic."""
    
    def __init__(self, name: str, tables: Dict[str, str], setup_func: Optional[Callable] = None):
        """
        Initialize schema definition.
        
        Args:
            name: Schema name/identifier
            tables: Dictionary of table_name -> CREATE TABLE SQL
            setup_func: Optional function for additional setup (indexes, triggers, etc.)
        """
        self.name = name
        self.tables = tables
        self.setup_func = setup_func


class DatabaseSchemaManager:
    """
    Centralized database schema management to eliminate code duplication.
    
    This class provides a common interface for database initialization across
    all components, replacing individual _init_database methods.
    """
    
    def __init__(self):
        """Initialize schema manager."""
        self._schemas: Dict[str, SchemaDefinition] = {}
        self._initialized_dbs: set = set()
        
        # Register all known schemas
        self._register_core_schemas()
    
    def register_schema(self, schema: SchemaDefinition) -> None:
        """Register a new database schema."""
        self._schemas[schema.name] = schema
        logger.debug(f"Registered database schema: {schema.name}")
    
    def initialize_database(self, db_path: Path, schema_name: str, 
                          additional_config: Optional[Dict] = None) -> None:
        """
        Initialize database with specified schema.
        
        Args:
            db_path: Path to database file
            schema_name: Name of registered schema to use
            additional_config: Optional additional configuration
        """
        if schema_name not in self._schemas:
            raise ValueError(f"Unknown schema: {schema_name}")
        
        schema = self._schemas[schema_name]
        db_key = f"{db_path}:{schema_name}"
        
        if db_key in self._initialized_dbs:
            logger.debug(f"Database already initialized: {db_key}")
            return
        
        logger.info(f"Initializing database {db_path} with schema {schema_name}")
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                # Create all tables
                for table_name, create_sql in schema.tables.items():
                    logger.debug(f"Creating table: {table_name}")
                    cursor.execute(create_sql)
                
                # Run additional setup if provided
                if schema.setup_func:
                    schema.setup_func(conn)
                
                conn.commit()
                self._initialized_dbs.add(db_key)
                logger.info(f"Successfully initialized database: {db_key}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database {db_path}: {e}")
            raise
    
    @contextmanager
    def _get_connection(self, db_path: Path):
        """Get database connection with proper setup."""
        conn = None
        try:
            conn = sqlite3.connect(
                str(db_path),
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
            raise
        finally:
            if conn:
                conn.close()
    
    def _register_core_schemas(self) -> None:
        """Register all core application schemas."""
        
        # Main application database schema
        main_schema = SchemaDefinition(
            name="main",
            tables={
                "models": """
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
                """,
                "categories": """
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 999,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "model_categories": """
                    CREATE TABLE IF NOT EXISTS model_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id INTEGER NOT NULL,
                        category_id INTEGER NOT NULL,
                        is_primary BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
                        FOREIGN KEY (category_id) REFERENCES categories(id),
                        UNIQUE(model_id, category_id)
                    )
                """,
                "downloads": """
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
                """,
                "search_history": """
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        filters TEXT,
                        results_count INTEGER,
                        searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "metadata_cache": """
                    CREATE TABLE IF NOT EXISTS metadata_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
            setup_func=self._setup_main_database
        )
        self.register_schema(main_schema)
        
        # Analytics database schema
        analytics_schema = SchemaDefinition(
            name="analytics",
            tables={
                "analytics_events": """
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        session_id TEXT,
                        user_id TEXT,
                        data TEXT,
                        tags TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
            }
        )
        self.register_schema(analytics_schema)
        
        # Uptime monitoring schema
        uptime_schema = SchemaDefinition(
            name="uptime",
            tables={
                "uptime_records": """
                    CREATE TABLE IF NOT EXISTS uptime_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        component TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time REAL,
                        error_message TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "incidents": """
                    CREATE TABLE IF NOT EXISTS incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component TEXT NOT NULL,
                        start_time REAL NOT NULL,
                        end_time REAL,
                        duration REAL,
                        severity TEXT NOT NULL,
                        description TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "availability_summary": """
                    CREATE TABLE IF NOT EXISTS availability_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component TEXT NOT NULL,
                        period_start REAL NOT NULL,
                        period_end REAL NOT NULL,
                        period_type TEXT NOT NULL,
                        uptime_seconds REAL NOT NULL,
                        downtime_seconds REAL NOT NULL,
                        availability_percentage REAL NOT NULL,
                        incident_count INTEGER DEFAULT 0,
                        average_response_time REAL,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """
            }
        )
        self.register_schema(uptime_schema)
    
    def _setup_main_database(self, conn: sqlite3.Connection) -> None:
        """メインデータベースの追加設定（インデックス、初期データなど）"""
        cursor = conn.cursor()
        
        # カテゴリの初期データを挿入（優先順位は参考値として保持）
        category_data = [
            ('character', 'Character', 1),
            ('style', 'Style', 2),
            ('concept', 'Concept', 3),
            ('background', 'Background', 4),
            ('poses', 'Poses', 5),
            ('vehicle', 'Vehicle', 6),
            ('clothing', 'Clothing', 7),
            ('action', 'Action', 8),
            ('animal', 'Animal', 9),
            ('assets', 'Assets', 10),
            ('base model', 'Base Model', 11),
            ('buildings', 'Buildings', 12),
            ('celebrity', 'Celebrity', 13),
            ('objects', 'Objects', 14),
            ('tool', 'Tool', 15),
            ('body', 'Body', 16),
            ('outfit', 'Outfit', 17),
            ('base', 'Base', 18),
            ('workflow', 'Workflow', 19),
            ('wildcards', 'Wildcards', 20),
            ('other', 'Other', 999)
        ]
        
        for name, display_name, priority in category_data:
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name, display_name, priority)
                VALUES (?, ?, ?)
            """, (name, display_name, priority))
        
        # インデックスを作成
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_categories_model_id 
            ON model_categories(model_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_categories_category_id 
            ON model_categories(category_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_categories_priority 
            ON categories(priority)
        """)
        
        # 主カテゴリの一意性を保証するインデックス
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_model_primary_category 
            ON model_categories(model_id) 
            WHERE is_primary = TRUE
        """)
        
        conn.commit()
        
        # Integrity monitoring schema
        integrity_schema = SchemaDefinition(
            name="integrity",
            tables={
                "file_integrity": """
                    CREATE TABLE IF NOT EXISTS file_integrity (
                        file_path TEXT PRIMARY KEY,
                        expected_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
                        file_size INTEGER,
                        last_verified REAL,
                        status TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "database_integrity": """
                    CREATE TABLE IF NOT EXISTS database_integrity (
                        db_path TEXT PRIMARY KEY,
                        table_counts TEXT,
                        integrity_result TEXT,
                        foreign_key_result TEXT,
                        last_verified REAL,
                        status TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "integrity_log": """
                    CREATE TABLE IF NOT EXISTS integrity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_path TEXT NOT NULL,
                        item_type TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        timestamp REAL DEFAULT (strftime('%s', 'now'))
                    )
                """
            }
        )
        self.register_schema(integrity_schema)
        
        # Security schemas (access control, audit, encryption)
        security_schema = SchemaDefinition(
            name="security",
            tables={
                "access_log": """
                    CREATE TABLE IF NOT EXISTS access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        resource TEXT NOT NULL,
                        action TEXT NOT NULL,
                        granted BOOLEAN NOT NULL,
                        reason TEXT,
                        ip_address TEXT,
                        risk_score REAL,
                        context TEXT,
                        timestamp REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "security_events": """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        user_id TEXT,
                        ip_address TEXT,  
                        description TEXT NOT NULL,
                        details TEXT,
                        timestamp REAL DEFAULT (strftime('%s', 'now'))
                    )
                """,
                "encryption_keys": """
                    CREATE TABLE IF NOT EXISTS encryption_keys (
                        key_id TEXT PRIMARY KEY,
                        key_type TEXT NOT NULL,
                        encrypted_key BLOB NOT NULL,
                        salt BLOB NOT NULL,
                        public_key TEXT,
                        fingerprint TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        last_used REAL,
                        usage_count INTEGER DEFAULT 0
                    )
                """,
                "key_metadata": """
                    CREATE TABLE IF NOT EXISTS key_metadata (
                        key_id TEXT PRIMARY KEY,
                        encryption_level TEXT NOT NULL,
                        purpose TEXT,
                        expiry_date REAL,
                        active BOOLEAN DEFAULT TRUE,
                        metadata TEXT,
                        FOREIGN KEY (key_id) REFERENCES encryption_keys(key_id)
                    )
                """
            }
        )
        self.register_schema(security_schema)


# Global schema manager instance
schema_manager = DatabaseSchemaManager()


def initialize_database(db_path: Path, schema_name: str, 
                       additional_config: Optional[Dict] = None) -> None:
    """
    Convenience function to initialize database with schema.
    
    Args:
        db_path: Path to database file
        schema_name: Name of schema to use
        additional_config: Optional additional configuration
    """
    schema_manager.initialize_database(db_path, schema_name, additional_config)


def register_custom_schema(schema: SchemaDefinition) -> None:
    """
    Convenience function to register custom schema.
    
    Args:
        schema: Schema definition to register
    """
    schema_manager.register_schema(schema)