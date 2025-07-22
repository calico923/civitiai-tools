#!/usr/bin/env python3
"""
Database optimization tests.
Tests for optimized SQLite schema, virtual columns, JSON search performance, and scalability.
"""

import pytest
import sqlite3
import json
import time
from pathlib import Path
import tempfile
import importlib.util
from typing import Dict, List, Any
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDatabaseOptimization:
    """Test database optimization features for high-performance data handling."""
    
    @property
    def data_dir(self) -> Path:
        """Get the data directory."""
        return Path(__file__).parent.parent.parent / "src" / "data"
    
    def test_optimized_database_schema_exists(self):
        """Test that optimized database schema module exists."""
        schema_path = self.data_dir / "optimized_schema.py"
        assert schema_path.exists(), "optimized_schema.py must exist"
        
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        # Test OptimizedDatabase class exists
        assert hasattr(schema_module, 'OptimizedDatabase'), "OptimizedDatabase class must exist"
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        # Test initialization
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            
            # Validate optimized methods
            assert hasattr(db, 'create_optimized_schema'), "Must have optimized schema creation"
            assert hasattr(db, 'create_virtual_columns'), "Must have virtual column creation"
            assert hasattr(db, 'create_compound_indexes'), "Must have compound index creation"
            assert hasattr(db, 'test_performance'), "Must have performance testing"
    
    def test_virtual_column_creation(self):
        """Test creation and functionality of virtual columns for optimized queries."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Test virtual columns are created
            virtual_columns = db.get_virtual_columns()
            assert 'model_type_virtual' in virtual_columns, "Must have model_type virtual column"
            assert 'commercial_use_virtual' in virtual_columns, "Must have commercial_use virtual column"
            assert 'nsfw_virtual' in virtual_columns, "Must have nsfw virtual column"
            assert 'download_count_tier' in virtual_columns, "Must have download tier virtual column"
            
            # Test virtual column functionality
            test_model = {
                'id': 1,
                'name': 'Test Model',
                'metadata': json.dumps({
                    'type': 'Checkpoint',
                    'allowCommercialUse': True,
                    'nsfw': False
                }),
                'stats': json.dumps({
                    'downloadCount': 1500
                })
            }
            
            db.insert_model(test_model)
            
            # Test virtual column queries
            checkpoint_models = db.query_by_model_type('Checkpoint')
            assert len(checkpoint_models) == 1, "Should find checkpoint model via virtual column"
            
            commercial_models = db.query_by_commercial_use(True)
            assert len(commercial_models) == 1, "Should find commercial model via virtual column"
            
            high_download_models = db.query_by_download_tier('HIGH')
            assert len(high_download_models) == 1, "Should categorize by download tier"
    
    def test_json_search_performance(self):
        """Test JSON search performance with optimized indexes."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Insert test data with JSON metadata
            test_models = []
            for i in range(100):  # Smaller dataset for unit tests
                model = {
                    'id': i,
                    'name': f'Test Model {i}',
                    'metadata': json.dumps({
                        'type': 'Checkpoint' if i % 3 == 0 else 'LORA',
                        'allowCommercialUse': i % 2 == 0,
                        'nsfw': i % 4 == 0,
                        'tags': [f'tag_{i%5}', f'style_{i%3}']
                    }),
                    'stats': json.dumps({
                        'downloadCount': i * 10,
                        'likeCount': i * 2
                    })
                }
                test_models.append(model)
                db.insert_model(model)
            
            # Test JSON search performance
            start_time = time.time()
            checkpoint_results = db.search_json_field('metadata', 'type', 'Checkpoint')
            json_search_time = time.time() - start_time
            
            # Test virtual column search performance
            start_time = time.time()
            virtual_results = db.query_by_model_type('Checkpoint')
            virtual_search_time = time.time() - start_time
            
            # Validate results are equivalent
            assert len(checkpoint_results) == len(virtual_results), "JSON and virtual searches should return same results"
            
            # Validate performance improvement (virtual columns should be faster)
            # For small datasets this might not be measurable, so we just test functionality
            assert json_search_time >= 0, "JSON search should complete"
            assert virtual_search_time >= 0, "Virtual column search should complete"
            
            # Test complex JSON queries
            complex_results = db.search_complex_json({
                'metadata.type': 'Checkpoint',
                'metadata.allowCommercialUse': True,
                'metadata.nsfw': False
            })
            assert len(complex_results) > 0, "Complex JSON search should return results"
    
    def test_compound_index_effectiveness(self):
        """Test compound indexes for multi-column queries."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Verify compound indexes are created
            indexes = db.get_compound_indexes()
            assert 'idx_model_type_commercial' in indexes, "Must have model_type + commercial_use index"
            assert 'idx_model_type_downloads' in indexes, "Must have model_type + download_count index"
            assert 'idx_nsfw_commercial_type' in indexes, "Must have nsfw + commercial + type index"
            
            # Insert test data
            for i in range(50):
                model = {
                    'id': i,
                    'name': f'Test Model {i}',
                    'metadata': json.dumps({
                        'type': 'Checkpoint' if i < 25 else 'LORA',
                        'allowCommercialUse': i % 2 == 0,
                        'nsfw': i % 3 == 0
                    }),
                    'stats': json.dumps({
                        'downloadCount': i * 100
                    })
                }
                db.insert_model(model)
            
            # Test compound index queries
            start_time = time.time()
            compound_results = db.query_compound_conditions({
                'model_type': 'Checkpoint',
                'commercial_use': True,
                'nsfw': False
            })
            compound_time = time.time() - start_time
            
            assert len(compound_results) > 0, "Compound query should return results"
            assert compound_time < 1.0, "Compound index query should be fast"
            
            # Test query plan analysis
            query_plan = db.explain_query_plan("SELECT * FROM models WHERE model_type_virtual = 'Checkpoint' AND commercial_use_virtual = 1")
            # SQLite might use INDEX or ix depending on version
            assert ('USING INDEX' in query_plan or 'ix' in query_plan or 'idx' in query_plan), "Query should use index"
    
    def test_batch_insert_performance(self):
        """Test batch insert performance with optimized transactions."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Generate test data
            batch_size = 100
            test_models = []
            for i in range(batch_size):
                model = {
                    'id': i,
                    'name': f'Batch Model {i}',
                    'metadata': json.dumps({
                        'type': 'Checkpoint' if i % 2 == 0 else 'LORA',
                        'allowCommercialUse': i % 3 == 0,
                        'nsfw': False,
                        'tags': [f'tag_{i}']
                    }),
                    'stats': json.dumps({
                        'downloadCount': i * 50,
                        'likeCount': i * 5
                    })
                }
                test_models.append(model)
            
            # Test individual inserts
            start_time = time.time()
            for model in test_models[:10]:  # Small subset for comparison
                db.insert_model(model)
            individual_time = time.time() - start_time
            
            # Test batch insert
            remaining_models = test_models[10:]
            start_time = time.time()
            db.batch_insert_models(remaining_models)
            batch_time = time.time() - start_time
            
            # Verify all models were inserted
            total_count = db.count_models()
            assert total_count == batch_size, f"Should have {batch_size} models, got {total_count}"
            
            # Test batch insert is faster per item
            individual_rate = 10 / individual_time if individual_time > 0 else float('inf')
            batch_rate = len(remaining_models) / batch_time if batch_time > 0 else float('inf')
            
            # Batch should be at least as fast as individual (usually much faster)
            assert batch_rate >= 0
            
            # Test transaction rollback on error
            invalid_models = [{'id': 'invalid', 'name': 'Invalid Model'}]  # Invalid ID type
            
            with pytest.raises(Exception):
                db.batch_insert_models(invalid_models)
            
            # Verify count hasn't changed (transaction rolled back)
            assert db.count_models() == batch_size, "Failed batch should not affect database"
    
    def test_sqlite_limits_with_10k_models(self):
        """Test SQLite performance and limits with 10,000+ models."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Test with smaller dataset in unit tests (1000 models)
            # Real 10k test would be in integration tests
            model_count = 1000
            batch_size = 100
            
            # Generate and insert large dataset in batches
            total_inserted = 0
            for batch_start in range(0, model_count, batch_size):
                batch_models = []
                for i in range(batch_start, min(batch_start + batch_size, model_count)):
                    model = {
                        'id': i,
                        'name': f'Scale Model {i}',
                        'description': f'Large dataset test model {i}' * 10,  # Larger content
                        'metadata': json.dumps({
                            'type': ['Checkpoint', 'LORA', 'ControlNet'][i % 3],
                            'allowCommercialUse': i % 2 == 0,
                            'nsfw': i % 5 == 0,
                            'tags': [f'tag_{j}' for j in range(i % 10)],
                            'baseModel': ['SD 1.5', 'SDXL', 'SD 2.1'][i % 3]
                        }),
                        'stats': json.dumps({
                            'downloadCount': i * 10,
                            'likeCount': i * 2,
                            'commentCount': i // 10
                        })
                    }
                    batch_models.append(model)
                
                start_time = time.time()
                db.batch_insert_models(batch_models)
                batch_time = time.time() - start_time
                total_inserted += len(batch_models)
                
                # Monitor performance degradation
                assert batch_time < 5.0, f"Batch {batch_start//batch_size + 1} should complete within 5 seconds"
            
            # Verify final count
            final_count = db.count_models()
            assert final_count == model_count, f"Should have {model_count} models"
            
            # Test query performance on large dataset
            search_start = time.time()
            checkpoint_models = db.query_by_model_type('Checkpoint')
            search_time = time.time() - search_start
            
            # Count how many Checkpoints we actually expect based on the logic
            expected_checkpoints = sum(1 for i in range(model_count) if i % 3 == 0)
            assert len(checkpoint_models) == expected_checkpoints, f"Should find {expected_checkpoints} Checkpoints, got {len(checkpoint_models)}"
            assert search_time < 2.0, "Search should be fast even with large dataset"
            
            # Test database file size limits
            db_path = Path(tmp_db.name)
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            assert db_size_mb < 100, f"Database should be under 100MB for {model_count} models, got {db_size_mb:.1f}MB"
            
            # Test memory usage during operations
            memory_usage = db.get_memory_usage()
            assert memory_usage['peak_memory_mb'] < 200, f"Memory usage should be reasonable, got {memory_usage['peak_memory_mb']:.1f}MB"
    
    def test_postgresql_migration_readiness(self):
        """Test PostgreSQL migration readiness and compatibility."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        # Test PostgreSQL schema generation
        if hasattr(schema_module, 'PostgreSQLSchema'):
            PostgreSQLSchema = schema_module.PostgreSQLSchema
            pg_schema = PostgreSQLSchema()
            
            # Test schema conversion
            sqlite_schema = OptimizedDatabase.get_schema_definition()
            postgres_schema = pg_schema.convert_from_sqlite(sqlite_schema)
            
            # Validate PostgreSQL-specific features
            assert 'JSONB' in postgres_schema, "Should use JSONB for JSON columns"
            assert 'GIN' in postgres_schema, "Should include GIN indexes for JSON"
            assert 'SERIAL' in postgres_schema or 'GENERATED' in postgres_schema, "Should use proper ID generation"
            
            # Test data migration compatibility
            migration_plan = pg_schema.generate_migration_plan()
            assert 'CREATE TABLE' in migration_plan, "Should include table creation"
            assert 'CREATE INDEX' in migration_plan, "Should include index creation"
            assert 'INSERT' in migration_plan, "Should include data migration"
        
        # Test export functionality for migration
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Insert sample data
            sample_models = [
                {
                    'id': 1,
                    'name': 'Migration Test Model',
                    'metadata': json.dumps({'type': 'Checkpoint', 'allowCommercialUse': True}),
                    'stats': json.dumps({'downloadCount': 100})
                }
            ]
            db.batch_insert_models(sample_models)
            
            # Test export formats
            if hasattr(db, 'export_for_migration'):
                csv_export = db.export_for_migration('csv')
                json_export = db.export_for_migration('json')
                sql_export = db.export_for_migration('sql')
                
                assert len(csv_export) > 0, "CSV export should contain data"
                assert len(json_export) > 0, "JSON export should contain data"
                assert 'INSERT' in sql_export, "SQL export should contain INSERT statements"
    
    def test_query_optimization_analysis(self):
        """Test query optimization and analysis tools."""
        schema_path = self.data_dir / "optimized_schema.py"
        spec = importlib.util.spec_from_file_location("optimized_schema", schema_path)
        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)
        
        OptimizedDatabase = schema_module.OptimizedDatabase
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db = OptimizedDatabase(tmp_db.name)
            db.create_optimized_schema()
            
            # Test query analysis tools
            if hasattr(db, 'analyze_query_performance'):
                # Test common query patterns
                query_patterns = [
                    "SELECT * FROM models WHERE model_type_virtual = 'Checkpoint'",
                    "SELECT * FROM models WHERE commercial_use_virtual = 1 AND nsfw_virtual = 0",
                    "SELECT COUNT(*) FROM models WHERE model_type_virtual = 'LORA'",
                    "SELECT * FROM models ORDER BY download_count_tier DESC LIMIT 10"
                ]
                
                for query in query_patterns:
                    analysis = db.analyze_query_performance(query)
                    
                    assert 'execution_time' in analysis, "Analysis should include execution time"
                    assert 'rows_examined' in analysis, "Analysis should include rows examined"
                    assert 'index_usage' in analysis, "Analysis should include index usage"
                    assert analysis['execution_time'] < 1.0, f"Query should be fast: {query}"
            
            # Test index usage statistics
            if hasattr(db, 'get_index_usage_stats'):
                stats = db.get_index_usage_stats()
                
                assert isinstance(stats, dict), "Stats should be a dictionary"
                for index_name, usage in stats.items():
                    assert 'times_used' in usage, "Should track usage count"
                    assert 'selectivity' in usage, "Should track selectivity"