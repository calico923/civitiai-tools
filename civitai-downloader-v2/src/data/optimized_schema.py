#!/usr/bin/env python3
"""
Optimized Database Schema for CivitAI Downloader.
Implements high-performance SQLite schema with virtual columns, compound indexes,
and JSON search optimization for handling 10,000+ models efficiently.
"""

import sqlite3
import json
import time
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import logging


class OptimizedDatabase:
    """High-performance SQLite database with optimized schema for CivitAI models."""
    
    def __init__(self, db_path: str):
        """
        Initialize optimized database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._peak_memory = 0
        self.logger = logging.getLogger(__name__)
        
        # Enable SQLite optimizations
        self._connect()
        self._configure_sqlite()
    
    def _connect(self) -> None:
        """Create database connection with optimizations."""
        self.connection = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
    
    def _configure_sqlite(self) -> None:
        """Configure SQLite for optimal performance."""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        # Performance optimizations
        cursor.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous = NORMAL")  # Balanced safety/performance
        cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store = MEMORY")  # Memory-based temp storage
        cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
        cursor.execute("PRAGMA optimize")  # Enable query optimizer
        
        self.connection.commit()
    
    def create_optimized_schema(self) -> None:
        """Create optimized database schema with virtual columns and indexes."""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        # Main models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                metadata TEXT NOT NULL,  -- JSON data
                stats TEXT NOT NULL,     -- JSON stats
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Virtual columns for optimized queries
                model_type_virtual TEXT GENERATED ALWAYS AS (
                    CASE 
                        WHEN json_extract(metadata, '$.type') IS NOT NULL 
                        THEN json_extract(metadata, '$.type')
                        ELSE 'Unknown'
                    END
                ) STORED,
                
                commercial_use_virtual BOOLEAN GENERATED ALWAYS AS (
                    CASE 
                        WHEN json_extract(metadata, '$.allowCommercialUse') = 1 
                        THEN 1
                        WHEN json_extract(metadata, '$.allowCommercialUse') = 'true'
                        THEN 1
                        ELSE 0
                    END
                ) STORED,
                
                nsfw_virtual BOOLEAN GENERATED ALWAYS AS (
                    CASE 
                        WHEN json_extract(metadata, '$.nsfw') = 1 
                        THEN 1
                        WHEN json_extract(metadata, '$.nsfw') = 'true'
                        THEN 1
                        ELSE 0
                    END
                ) STORED,
                
                download_count_virtual INTEGER GENERATED ALWAYS AS (
                    CAST(json_extract(stats, '$.downloadCount') AS INTEGER)
                ) STORED,
                
                download_count_tier TEXT GENERATED ALWAYS AS (
                    CASE 
                        WHEN CAST(json_extract(stats, '$.downloadCount') AS INTEGER) >= 10000 THEN 'VERY_HIGH'
                        WHEN CAST(json_extract(stats, '$.downloadCount') AS INTEGER) >= 1000 THEN 'HIGH'
                        WHEN CAST(json_extract(stats, '$.downloadCount') AS INTEGER) >= 100 THEN 'MEDIUM'
                        WHEN CAST(json_extract(stats, '$.downloadCount') AS INTEGER) >= 10 THEN 'LOW'
                        ELSE 'VERY_LOW'
                    END
                ) STORED
            )
        """)
        
        self.create_compound_indexes()
        self.connection.commit()
    
    def create_virtual_columns(self) -> List[str]:
        """
        Create virtual columns for optimized queries.
        
        Returns:
            List of created virtual column names
        """
        # Virtual columns are created as part of the table schema
        return [
            'model_type_virtual',
            'commercial_use_virtual', 
            'nsfw_virtual',
            'download_count_virtual',
            'download_count_tier'
        ]
    
    def get_virtual_columns(self) -> List[str]:
        """Get list of virtual columns in the schema."""
        return self.create_virtual_columns()
    
    def create_compound_indexes(self) -> None:
        """Create compound indexes for multi-column queries."""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        # Compound indexes for common query patterns
        indexes = [
            ("idx_model_type_commercial", "model_type_virtual, commercial_use_virtual"),
            ("idx_model_type_downloads", "model_type_virtual, download_count_virtual DESC"),
            ("idx_nsfw_commercial_type", "nsfw_virtual, commercial_use_virtual, model_type_virtual"),
            ("idx_download_tier", "download_count_tier"),
            ("idx_created_at", "created_at DESC"),
            ("idx_name_search", "name COLLATE NOCASE")
        ]
        
        for index_name, columns in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON models ({columns})")
        
        # JSON indexes for flexible queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_json ON models (metadata)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_json ON models (stats)")
    
    def get_compound_indexes(self) -> List[str]:
        """Get list of compound indexes."""
        return [
            'idx_model_type_commercial',
            'idx_model_type_downloads', 
            'idx_nsfw_commercial_type',
            'idx_download_tier',
            'idx_created_at',
            'idx_name_search',
            'idx_metadata_json',
            'idx_stats_json'
        ]
    
    def insert_model(self, model: Dict[str, Any]) -> None:
        """
        Insert a single model into the database.
        
        Args:
            model: Model data dictionary
        """
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT INTO models (id, name, description, metadata, stats)
            VALUES (?, ?, ?, ?, ?)
        """, (
            model['id'],
            model['name'],
            model.get('description', ''),
            model['metadata'] if isinstance(model['metadata'], str) else json.dumps(model['metadata']),
            model['stats'] if isinstance(model['stats'], str) else json.dumps(model['stats'])
        ))
        
        self.connection.commit()
    
    def batch_insert_models(self, models: List[Dict[str, Any]]) -> None:
        """
        Insert multiple models in an optimized batch operation.
        
        Args:
            models: List of model data dictionaries
        """
        if not self.connection or not models:
            return
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Prepare data for batch insert
            batch_data = []
            for model in models:
                batch_data.append((
                    model['id'],
                    model['name'],
                    model.get('description', ''),
                    model['metadata'] if isinstance(model['metadata'], str) else json.dumps(model['metadata']),
                    model['stats'] if isinstance(model['stats'], str) else json.dumps(model['stats'])
                ))
            
            cursor.executemany("""
                INSERT INTO models (id, name, description, metadata, stats)
                VALUES (?, ?, ?, ?, ?)
            """, batch_data)
            
            cursor.execute("COMMIT")
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            raise e
    
    def query_by_model_type(self, model_type: str) -> List[Dict[str, Any]]:
        """
        Query models by type using virtual column.
        
        Args:
            model_type: Model type to search for
            
        Returns:
            List of matching models
        """
        if not self.connection:
            return []
            
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE model_type_virtual = ?
        """, (model_type,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def query_by_commercial_use(self, commercial_use: bool) -> List[Dict[str, Any]]:
        """
        Query models by commercial use permission using virtual column.
        
        Args:
            commercial_use: Whether to allow commercial use
            
        Returns:
            List of matching models
        """
        if not self.connection:
            return []
            
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE commercial_use_virtual = ?
        """, (1 if commercial_use else 0,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def query_by_download_tier(self, tier: str) -> List[Dict[str, Any]]:
        """
        Query models by download count tier.
        
        Args:
            tier: Download tier (VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH)
            
        Returns:
            List of matching models
        """
        if not self.connection:
            return []
            
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE download_count_tier = ?
        """, (tier,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_json_field(self, json_column: str, field: str, value: Any) -> List[Dict[str, Any]]:
        """
        Search JSON field using SQLite JSON functions.
        
        Args:
            json_column: JSON column name (metadata or stats)
            field: JSON field to search
            value: Value to search for
            
        Returns:
            List of matching models
        """
        if not self.connection:
            return []
            
        cursor = self.connection.cursor()
        cursor.execute(f"""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE json_extract({json_column}, '$.{field}') = ?
        """, (value,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_complex_json(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search using complex JSON criteria.
        
        Args:
            criteria: Dictionary of JSON path to value mappings
            
        Returns:
            List of matching models
        """
        if not self.connection or not criteria:
            return []
        
        cursor = self.connection.cursor()
        
        # Build WHERE clause from criteria
        where_conditions = []
        values = []
        
        for json_path, value in criteria.items():
            column, path = json_path.split('.', 1)
            where_conditions.append(f"json_extract({column}, '$.{path}') = ?")
            values.append(value)
        
        where_clause = " AND ".join(where_conditions)
        
        cursor.execute(f"""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE {where_clause}
        """, values)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def query_compound_conditions(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query using compound conditions with virtual columns.
        
        Args:
            conditions: Dictionary of virtual column conditions
            
        Returns:
            List of matching models
        """
        if not self.connection or not conditions:
            return []
        
        cursor = self.connection.cursor()
        
        # Map condition keys to virtual columns
        column_mapping = {
            'model_type': 'model_type_virtual',
            'commercial_use': 'commercial_use_virtual',
            'nsfw': 'nsfw_virtual'
        }
        
        where_conditions = []
        values = []
        
        for key, value in conditions.items():
            if key in column_mapping:
                column = column_mapping[key]
                if isinstance(value, bool):
                    value = 1 if value else 0
                where_conditions.append(f"{column} = ?")
                values.append(value)
        
        if not where_conditions:
            return []
        
        where_clause = " AND ".join(where_conditions)
        
        cursor.execute(f"""
            SELECT id, name, description, metadata, stats
            FROM models 
            WHERE {where_clause}
        """, values)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def explain_query_plan(self, query: str) -> str:
        """
        Get query execution plan for optimization analysis.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Query plan as string
        """
        if not self.connection:
            return ""
            
        cursor = self.connection.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {query}")
        
        plan_rows = cursor.fetchall()
        # Convert Row objects to string properly
        plan_text = []
        for row in plan_rows:
            if hasattr(row, 'keys'):
                # Convert Row to dict then to string
                row_dict = dict(row)
                plan_text.append(str(row_dict))
            else:
                plan_text.append(str(row))
        
        plan_string = "\n".join(plan_text)
        return plan_string
    
    def count_models(self) -> int:
        """
        Get total count of models in database.
        
        Returns:
            Number of models
        """
        if not self.connection:
            return 0
            
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM models")
        
        return cursor.fetchone()[0]
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.
        
        Returns:
            Memory usage information
        """
        try:
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 * 1024)  # MB
            self._peak_memory = max(self._peak_memory, current_memory)
            
            return {
                'current_memory_mb': current_memory,
                'peak_memory_mb': self._peak_memory,
                'memory_percent': process.memory_percent()
            }
        except:
            return {
                'current_memory_mb': 0.0,
                'peak_memory_mb': 0.0,
                'memory_percent': 0.0
            }
    
    def test_performance(self) -> Dict[str, float]:
        """
        Run performance tests on current database.
        
        Returns:
            Performance metrics
        """
        metrics = {}
        
        if not self.connection:
            return metrics
        
        # Test query performance
        start_time = time.time()
        self.count_models()
        metrics['count_query_time'] = time.time() - start_time
        
        # Test index usage
        start_time = time.time()
        self.query_by_model_type('Checkpoint')
        metrics['virtual_column_query_time'] = time.time() - start_time
        
        # Test JSON query
        start_time = time.time()
        self.search_json_field('metadata', 'type', 'LORA')
        metrics['json_query_time'] = time.time() - start_time
        
        return metrics
    
    def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """
        Analyze query performance with detailed metrics.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Performance analysis results
        """
        if not self.connection:
            return {}
        
        cursor = self.connection.cursor()
        
        # Get query plan
        plan = self.explain_query_plan(query)
        
        # Measure execution time
        start_time = time.time()
        cursor.execute(query)
        results = cursor.fetchall()
        execution_time = time.time() - start_time
        
        return {
            'execution_time': execution_time,
            'rows_returned': len(results),
            'rows_examined': len(results),  # Simplified for this implementation
            'index_usage': 'USING INDEX' in plan,
            'query_plan': plan
        }
    
    def get_index_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get index usage statistics.
        
        Returns:
            Index usage information
        """
        if not self.connection:
            return {}
        
        # Simplified implementation - real stats would require query logging
        indexes = self.get_compound_indexes()
        stats = {}
        
        for index in indexes:
            stats[index] = {
                'times_used': 0,  # Would track actual usage
                'selectivity': 0.5,  # Would calculate from data distribution
                'size_kb': 0  # Would get from SQLite stats
            }
        
        return stats
    
    @staticmethod
    def get_schema_definition() -> str:
        """
        Get the complete schema definition for migration purposes.
        
        Returns:
            SQL schema definition
        """
        return """
        CREATE TABLE models (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            metadata TEXT NOT NULL,
            stats TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_type_virtual TEXT GENERATED ALWAYS AS (
                json_extract(metadata, '$.type')
            ) STORED,
            commercial_use_virtual BOOLEAN GENERATED ALWAYS AS (
                CASE WHEN json_extract(metadata, '$.allowCommercialUse') = 1 THEN 1 ELSE 0 END
            ) STORED
        );
        """
    
    def export_for_migration(self, format_type: str) -> str:
        """
        Export data for database migration.
        
        Args:
            format_type: Export format (csv, json, sql)
            
        Returns:
            Exported data as string
        """
        if not self.connection:
            return ""
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM models")
        rows = cursor.fetchall()
        
        if format_type == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            if rows:
                writer.writerow(rows[0].keys())
                for row in rows:
                    writer.writerow(row)
            return output.getvalue()
        
        elif format_type == 'json':
            return json.dumps([dict(row) for row in rows], indent=2)
        
        elif format_type == 'sql':
            sql_statements = []
            for row in rows:
                values = ", ".join([f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" for v in row])
                sql_statements.append(f"INSERT INTO models VALUES ({values});")
            return "\n".join(sql_statements)
        
        return ""
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None


class PostgreSQLSchema:
    """PostgreSQL schema conversion for future migration."""
    
    def convert_from_sqlite(self, sqlite_schema: str) -> str:
        """
        Convert SQLite schema to PostgreSQL.
        
        Args:
            sqlite_schema: SQLite schema definition
            
        Returns:
            PostgreSQL schema definition
        """
        # Convert SQLite types to PostgreSQL
        postgres_schema = sqlite_schema.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
        postgres_schema = postgres_schema.replace("TEXT NOT NULL,", "JSONB NOT NULL,")  # Convert JSON columns
        postgres_schema = postgres_schema.replace("metadata TEXT NOT NULL", "metadata JSONB NOT NULL")
        postgres_schema = postgres_schema.replace("stats TEXT NOT NULL", "stats JSONB NOT NULL")
        postgres_schema = postgres_schema.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP DEFAULT NOW()")
        
        # Add PostgreSQL-specific optimizations
        postgres_schema += "\n-- PostgreSQL optimizations\n"
        postgres_schema += "CREATE INDEX CONCURRENTLY idx_metadata_gin ON models USING GIN (metadata);\n"
        postgres_schema += "CREATE INDEX CONCURRENTLY idx_stats_gin ON models USING GIN (stats);\n"
        
        return postgres_schema
    
    def generate_migration_plan(self) -> str:
        """
        Generate a complete migration plan.
        
        Returns:
            Migration plan as SQL
        """
        return """
        -- PostgreSQL Migration Plan
        CREATE TABLE models (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            metadata JSONB NOT NULL,
            stats JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX CONCURRENTLY idx_metadata_gin ON models USING GIN (metadata);
        CREATE INDEX CONCURRENTLY idx_stats_gin ON models USING GIN (stats);
        CREATE INDEX idx_model_type ON models ((metadata->>'type'));
        CREATE INDEX idx_commercial_use ON models ((metadata->>'allowCommercialUse'));
        
        INSERT INTO models (name, description, metadata, stats)
        SELECT name, description, metadata::jsonb, stats::jsonb FROM sqlite_models;
        """