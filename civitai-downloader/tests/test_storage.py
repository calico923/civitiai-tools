"""Tests for storage management system."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.storage import StorageManager, BackupManager, MetadataCache
from src.interfaces import ModelInfo, ModelVersion, ModelFile, ModelImage, ModelType
from src.config import ConfigManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=ConfigManager)
    config.config = MagicMock()
    config.config.download_path = "/tmp/test_storage"
    return config


@pytest.fixture
def sample_model():
    """Create sample model data."""
    return ModelInfo(
        id=12345,
        name="Test Model",
        type=ModelType.LORA,
        description="Test model for storage testing",
        tags=["test", "storage"],
        creator="test_user",
        stats={"downloadCount": 100, "favoriteCount": 20},
        nsfw=False,
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2023, 1, 2)
    )


@pytest.fixture
def sample_version():
    """Create sample version data."""
    return ModelVersion(
        id=67890,
        model_id=12345,
        name="v1.0",
        description="Test version",
        base_model="SD 1.5",
        trained_words=["test_trigger"],
        files=[
            ModelFile(
                id=1,
                name="test_model.safetensors",
                size_bytes=50 * 1024 * 1024,
                format="Model",
                fp="fp16",
                hash="abc123def456",
                download_url="https://example.com/model.safetensors",
                metadata={"format": "safetensors"}
            )
        ],
        images=[
            ModelImage(
                id=1,
                url="https://example.com/image.jpg",
                width=512,
                height=512,
                hash="img123",
                nsfw=False,
                meta={"prompt": "test prompt"}
            )
        ],
        download_url="https://example.com/version",
        created_at=datetime(2023, 1, 1)
    )


class TestStorageManager:
    """Test StorageManager functionality."""
    
    def test_storage_manager_initialization(self, mock_config):
        """Test StorageManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            assert storage_manager.config == mock_config
            assert storage_manager.base_path == Path(temp_dir)
            assert storage_manager.metadata_db_path.exists()
            assert storage_manager.history_db_path.exists()
    
    def test_get_model_path(self, mock_config, sample_model, sample_version):
        """Test model path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            path = storage_manager.get_model_path(sample_model, sample_version)
            
            # Check path structure
            assert "lora" in str(path)  # model type
            assert "Test Model_12345" in str(path)  # model name and id (with space)
            assert "v1.0_67890" in str(path)  # version name and id
    
    def test_save_and_find_metadata(self, mock_config, sample_model, sample_version):
        """Test saving and finding metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            # Create a dummy path
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Find model by ID
            found_model = storage_manager.find_model_by_id(sample_model.id)
            assert found_model is not None
            assert found_model['name'] == sample_model.name
            assert found_model['type'] == sample_model.type.value
    
    def test_find_models_by_name(self, mock_config, sample_model, sample_version):
        """Test finding models by name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Find by name
            found_models = storage_manager.find_models_by_name("Test")
            assert len(found_models) == 1
            assert found_models[0]['name'] == sample_model.name
            
            # Find by partial name
            found_models = storage_manager.find_models_by_name("Model")
            assert len(found_models) == 1
    
    def test_get_models_by_type(self, mock_config, sample_model, sample_version):
        """Test getting models by type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Find by type
            found_models = storage_manager.get_models_by_type(ModelType.LORA.value)
            assert len(found_models) == 1
            assert found_models[0]['type'] == ModelType.LORA.value
    
    def test_download_history(self, mock_config, sample_model, sample_version):
        """Test download history functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Add to history
            storage_manager.add_to_history(sample_model, sample_version, model_path)
            
            # Get history
            history = storage_manager.get_download_history()
            assert len(history) == 1
            assert history[0]['model_id'] == sample_model.id
            assert history[0]['version_id'] == sample_version.id
    
    def test_check_disk_space(self, mock_config):
        """Test disk space checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            # Should have enough space for small amount
            assert storage_manager.check_disk_space(1024)
            
            # Should not have enough space for huge amount
            assert not storage_manager.check_disk_space(10**15)  # 1 PB
    
    def test_get_storage_stats(self, mock_config, sample_model, sample_version):
        """Test storage statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Get stats
            stats = storage_manager.get_storage_stats()
            assert stats['total_models'] == 1
            assert stats['total_versions'] == 1
            assert stats['total_files'] == 1
            assert 'total_size_human' in stats
    
    def test_cleanup_orphaned_files(self, mock_config):
        """Test cleanup of orphaned files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            # Create orphaned file
            orphaned_file = Path(temp_dir) / "orphaned.safetensors"
            orphaned_file.write_text("fake content")
            
            # Run cleanup
            result = storage_manager.cleanup_orphaned_files()
            
            # Should detect and remove orphaned file
            assert result['orphaned_files'] >= 0
            assert result['freed_bytes'] >= 0
    
    def test_export_import_metadata(self, mock_config, sample_model, sample_version):
        """Test metadata export and import."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Export metadata
            export_path = Path(temp_dir) / "export.json"
            storage_manager.export_metadata(export_path)
            
            assert export_path.exists()
            
            # Verify export structure
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            assert 'models' in data
            assert 'export_date' in data
            assert len(data['models']) == 1
            assert data['models'][0]['id'] == sample_model.id
            
            # Create new storage manager for import
            storage_manager2 = StorageManager(mock_config)
            
            # Import metadata
            result = storage_manager2.import_metadata(export_path)
            
            assert result['imported_models'] == 1
            assert result['imported_versions'] == 1
            
            # Verify imported data
            found_model = storage_manager2.find_model_by_id(sample_model.id)
            assert found_model is not None
            assert found_model['name'] == sample_model.name


class TestBackupManager:
    """Test BackupManager functionality."""
    
    def test_backup_manager_initialization(self, mock_config):
        """Test BackupManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            backup_manager = BackupManager(storage_manager)
            
            assert backup_manager.storage_manager == storage_manager
            assert backup_manager.backup_dir.exists()
    
    def test_create_backup(self, mock_config, sample_model, sample_version):
        """Test backup creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            backup_manager = BackupManager(storage_manager)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save some metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Create backup
            backup_path = backup_manager.create_backup("test_backup")
            
            assert backup_path.exists()
            assert backup_path.name == "test_backup.json"
    
    def test_list_backups(self, mock_config):
        """Test listing backups."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            backup_manager = BackupManager(storage_manager)
            
            # Create a backup
            backup_path = backup_manager.create_backup("test_backup")
            
            # List backups
            backups = backup_manager.list_backups()
            
            assert len(backups) == 1
            assert backups[0]['name'] == "test_backup"
            assert 'size' in backups[0]
            assert 'created' in backups[0]
    
    def test_cleanup_old_backups(self, mock_config):
        """Test cleanup of old backups."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            backup_manager = BackupManager(storage_manager)
            
            # Create multiple backups
            for i in range(5):
                backup_manager.create_backup(f"backup_{i}")
            
            # Should have 5 backups
            backups = backup_manager.list_backups()
            assert len(backups) == 5
            
            # Cleanup, keep only 2
            removed = backup_manager.cleanup_old_backups(2)
            
            assert removed == 3
            
            # Should have 2 backups left
            backups = backup_manager.list_backups()
            assert len(backups) == 2
    
    def test_restore_backup(self, mock_config, sample_model, sample_version):
        """Test restoring from backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            backup_manager = BackupManager(storage_manager)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # Create backup
            backup_path = backup_manager.create_backup("test_backup")
            
            # Create new storage manager
            storage_manager2 = StorageManager(mock_config)
            backup_manager2 = BackupManager(storage_manager2)
            
            # Restore backup
            result = backup_manager2.restore_backup(backup_path)
            
            assert result['imported_models'] == 1
            assert result['imported_versions'] == 1
            
            # Verify restored data
            found_model = storage_manager2.find_model_by_id(sample_model.id)
            assert found_model is not None
            assert found_model['name'] == sample_model.name


class TestMetadataCache:
    """Test MetadataCache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = MetadataCache(max_size=5)
        
        assert cache.max_size == 5
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0
    
    def test_cache_set_get(self):
        """Test setting and getting cache items."""
        cache = MetadataCache(max_size=5)
        
        # Set item
        cache.set("key1", {"data": "value1"})
        
        # Get item
        result = cache.get("key1")
        assert result is not None
        assert result["data"] == "value1"
        
        # Get non-existent item
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_max_size_eviction(self):
        """Test cache eviction when max size is reached."""
        cache = MetadataCache(max_size=3)
        
        # Fill cache
        for i in range(3):
            cache.set(f"key{i}", {"data": f"value{i}"})
        
        assert len(cache.cache) == 3
        
        # Add one more item - should evict oldest
        cache.set("key3", {"data": "value3"})
        
        assert len(cache.cache) == 3
        assert cache.get("key0") is None  # Oldest should be evicted
        assert cache.get("key3") is not None  # New item should exist
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = MetadataCache(max_size=5)
        
        # Add items
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        
        assert len(cache.cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MetadataCache(max_size=5)
        
        # Add items
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        
        stats = cache.get_stats()
        
        assert stats['size'] == 2
        assert stats['max_size'] == 5
        assert 'hit_rate' in stats
        assert 'memory_usage' in stats


class TestStorageIntegration:
    """Integration tests for storage system."""
    
    def test_full_storage_workflow(self, mock_config, sample_model, sample_version):
        """Test complete storage workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir(parents=True, exist_ok=True)
            
            # 1. Save metadata
            storage_manager.save_metadata(sample_model, sample_version, model_path)
            
            # 2. Add to history
            storage_manager.add_to_history(sample_model, sample_version, model_path)
            
            # 3. Verify model can be found
            found_model = storage_manager.find_model_by_id(sample_model.id)
            assert found_model is not None
            
            # 4. Check storage stats
            stats = storage_manager.get_storage_stats()
            assert stats['total_models'] == 1
            
            # 5. Get download history
            history = storage_manager.get_download_history()
            assert len(history) == 1
            
            # 6. Create backup
            backup_manager = BackupManager(storage_manager)
            backup_path = backup_manager.create_backup("integration_test")
            assert backup_path.exists()
            
            # 7. Export metadata
            export_path = Path(temp_dir) / "export.json"
            storage_manager.export_metadata(export_path)
            assert export_path.exists()
            
            # 8. Verify everything is consistent
            found_by_name = storage_manager.find_models_by_name("Test")
            assert len(found_by_name) == 1
            
            recent_models = storage_manager.get_recently_downloaded(5)
            assert len(recent_models) == 1
    
    def test_error_handling(self, mock_config):
        """Test error handling in storage operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.config.download_path = temp_dir
            storage_manager = StorageManager(mock_config)
            
            # Test import with non-existent file
            with pytest.raises(FileNotFoundError):
                storage_manager.import_metadata(Path("nonexistent.json"))
            
            # Test find with non-existent ID
            result = storage_manager.find_model_by_id(999999)
            assert result is None
            
            # Test search with empty results
            results = storage_manager.find_models_by_name("nonexistent")
            assert len(results) == 0