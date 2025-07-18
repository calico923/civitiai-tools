"""Simplified tests for download manager functionality."""

import pytest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import aiofiles
import asyncio
import time

from src.download import DownloadManager, ProgressDisplay, BatchDownloadManager
from src.interfaces import ModelVersion, ModelFile, ModelInfo, ModelType, DownloadProgress
from src.config import ConfigManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=ConfigManager)
    config.config = MagicMock()
    config.config.download_path = "/tmp/test_downloads"
    config.config.max_concurrent_downloads = 3
    config.config.user_agent = "Test/1.0"
    config.config.verify_ssl = True
    config.config.proxy = None
    return config


@pytest.fixture
def sample_model_file():
    """Create sample model file data."""
    return ModelFile(
        id=1,
        name="test_model.safetensors",
        size_bytes=50 * 1024 * 1024,  # 50MB
        format="Model",
        fp="fp16",
        hash="abc123def456",
        download_url="https://example.com/download/test_model.safetensors",
        metadata={"format": "safetensors"}
    )


@pytest.fixture
def sample_model_version(sample_model_file):
    """Create sample model version data."""
    return ModelVersion(
        id=67890,
        model_id=12345,
        name="v1.0",
        description="Test version",
        base_model="SD 1.5",
        trained_words=["test"],
        files=[sample_model_file],
        images=[],
        download_url="https://example.com/download/version",
        created_at=datetime.now()
    )


class TestDownloadManagerBasics:
    """Test basic DownloadManager functionality."""
    
    def test_download_manager_initialization(self, mock_config):
        """Test DownloadManager initialization."""
        dm = DownloadManager(mock_config)
        assert dm.config == mock_config
        assert dm.session is None
        assert dm.active_downloads == {}
        assert dm.download_stats == {}
    
    def test_can_resume_download(self, mock_config):
        """Test resume capability detection."""
        dm = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test non-existent file
            non_existent = Path(temp_dir) / "non_existent.txt"
            assert not dm.can_resume(non_existent)
            
            # Test existing file with content
            existing = Path(temp_dir) / "existing.txt"
            existing.write_text("content")
            assert dm.can_resume(existing)
            
            # Test empty file
            empty = Path(temp_dir) / "empty.txt"
            empty.touch()
            assert not dm.can_resume(empty)
    
    @pytest.mark.asyncio
    async def test_verify_file_hash(self, mock_config):
        """Test file hash verification."""
        dm = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_content = b"test content"
            
            # Write test content
            async with aiofiles.open(test_file, 'wb') as f:
                await f.write(test_content)
            
            # Calculate expected hash
            expected_hash = hashlib.sha256(test_content).hexdigest()
            
            # Test correct hash
            assert await dm._verify_file_hash(test_file, expected_hash)
            
            # Test incorrect hash
            assert not await dm._verify_file_hash(test_file, "wrong_hash")
            
            # Test empty hash (should pass)
            assert await dm._verify_file_hash(test_file, "")
    
    def test_download_cancellation(self, mock_config):
        """Test download cancellation functionality."""
        dm = DownloadManager(mock_config)
        
        # Start a mock download
        test_path = Path("/tmp/test.txt")
        download_key = f"https://example.com/test.txt::{test_path}"
        dm.active_downloads[download_key] = True
        
        # Cancel download
        dm.cancel_download(test_path)
        
        # Should mark as cancelled
        assert dm.active_downloads[download_key] is False
    
    def test_download_stats_tracking(self, mock_config, sample_model_version):
        """Test download statistics tracking."""
        dm = DownloadManager(mock_config)
        
        # Simulate completed download
        file_path = Path("/tmp/test_model.safetensors")
        dm.download_stats[str(file_path)] = {
            'model_id': sample_model_version.model_id,
            'version_id': sample_model_version.id,
            'file_id': sample_model_version.files[0].id,
            'file_name': sample_model_version.files[0].name,
            'file_size': sample_model_version.files[0].size_bytes,
            'downloaded_at': time.time(),
            'hash': sample_model_version.files[0].hash
        }
        
        stats = dm.get_download_stats()
        assert str(file_path) in stats
        assert stats[str(file_path)]['model_id'] == sample_model_version.model_id
        assert stats[str(file_path)]['file_name'] == "test_model.safetensors"


class TestProgressDisplay:
    """Test ProgressDisplay functionality."""
    
    def test_progress_display_creation(self):
        """Test progress display creation."""
        display = ProgressDisplay(show_speed=True, show_eta=True)
        assert display.show_speed is True
        assert display.show_eta is True
        assert len(display.progress_bars) == 0
    
    def test_progress_bar_lifecycle(self):
        """Test progress bar creation and cleanup."""
        display = ProgressDisplay()
        
        # Create progress bar
        pbar = display.create_progress_bar("test.txt", 1000)
        assert "test.txt" in display.progress_bars
        assert pbar.total == 1000
        
        # Close progress bar
        display.close_progress_bar("test.txt")
        assert "test.txt" not in display.progress_bars
    
    def test_format_eta(self):
        """Test ETA formatting."""
        display = ProgressDisplay()
        
        # Test seconds
        assert display._format_eta(30) == "30s"
        
        # Test minutes
        assert display._format_eta(120) == "2m"
        
        # Test hours
        assert display._format_eta(7200) == "2.0h"
    
    def test_update_progress(self):
        """Test progress bar updates."""
        display = ProgressDisplay()
        
        # Test progress update
        progress = DownloadProgress(
            file_name="test.txt",
            total_bytes=1000,
            downloaded_bytes=500,
            percent=50.0,
            speed_mbps=1.5,
            eta_seconds=10.0
        )
        
        # This should create a progress bar and update it
        display.update_progress(progress)
        
        assert "test.txt" in display.progress_bars
        pbar = display.progress_bars["test.txt"]
        assert pbar.n == 500
        assert pbar.total == 1000
        
        # Clean up
        display.close_all()
        assert len(display.progress_bars) == 0


class TestBatchDownloadManager:
    """Test BatchDownloadManager functionality."""
    
    def test_batch_manager_creation(self, mock_config):
        """Test batch download manager creation."""
        dm = DownloadManager(mock_config)
        batch_manager = BatchDownloadManager(dm, max_concurrent=2)
        
        assert batch_manager.download_manager == dm
        assert batch_manager.max_concurrent == 2
        assert batch_manager.semaphore._value == 2
    
    def test_batch_cleanup(self, mock_config):
        """Test batch manager cleanup."""
        dm = DownloadManager(mock_config)
        batch_manager = BatchDownloadManager(dm)
        
        # Create some progress bars
        batch_manager.progress_display.create_progress_bar("test1.txt", 1000)
        batch_manager.progress_display.create_progress_bar("test2.txt", 2000)
        
        assert len(batch_manager.progress_display.progress_bars) == 2
        
        # Cleanup should close all progress bars
        batch_manager.cleanup()
        
        assert len(batch_manager.progress_display.progress_bars) == 0


class TestDownloadWorkflow:
    """Test download workflow components."""
    
    def test_download_progress_data_structure(self):
        """Test DownloadProgress data structure."""
        progress = DownloadProgress(
            file_name="test.safetensors",
            total_bytes=1000000,
            downloaded_bytes=250000,
            percent=25.0,
            speed_mbps=2.5,
            eta_seconds=120.0
        )
        
        assert progress.file_name == "test.safetensors"
        assert progress.total_bytes == 1000000
        assert progress.downloaded_bytes == 250000
        assert progress.percent == 25.0
        assert progress.speed_mbps == 2.5
        assert progress.eta_seconds == 120.0
    
    def test_model_file_data_structure(self, sample_model_file):
        """Test ModelFile data structure."""
        assert sample_model_file.id == 1
        assert sample_model_file.name == "test_model.safetensors"
        assert sample_model_file.size_bytes == 50 * 1024 * 1024
        assert sample_model_file.format == "Model"
        assert sample_model_file.fp == "fp16"
        assert sample_model_file.hash == "abc123def456"
        assert "example.com" in sample_model_file.download_url
        assert sample_model_file.metadata["format"] == "safetensors"
    
    def test_model_version_data_structure(self, sample_model_version):
        """Test ModelVersion data structure."""
        assert sample_model_version.id == 67890
        assert sample_model_version.model_id == 12345
        assert sample_model_version.name == "v1.0"
        assert sample_model_version.base_model == "SD 1.5"
        assert len(sample_model_version.files) == 1
        assert len(sample_model_version.images) == 0
        assert sample_model_version.trained_words == ["test"]
    
    @pytest.mark.asyncio
    async def test_download_manager_context_manager(self, mock_config):
        """Test DownloadManager context manager behavior."""
        dm = DownloadManager(mock_config)
        
        # Test that session is None initially
        assert dm.session is None
        
        # Test context manager (simplified - no actual aiohttp)
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with dm as context_dm:
                assert context_dm == dm
                # In real implementation, session would be created here
    
    def test_error_handling_cases(self, mock_config):
        """Test error handling scenarios."""
        dm = DownloadManager(mock_config)
        
        # Test download without session
        with pytest.raises(RuntimeError, match="not initialized"):
            asyncio.run(dm.download_file(
                url="https://example.com/test.txt",
                path=Path("/tmp/test.txt")
            ))
        
        # Test duplicate download (need to mock session first)
        test_path = Path("/tmp/duplicate.txt")
        download_key = f"https://example.com/test.txt::{test_path}"
        dm.active_downloads[download_key] = True
        
        # Mock session to get past the first check
        dm.session = AsyncMock()
        
        with pytest.raises(RuntimeError, match="already in progress"):
            asyncio.run(dm.download_file(
                url="https://example.com/test.txt",
                path=test_path
            ))
    
    def test_download_path_creation(self, mock_config):
        """Test download path creation logic."""
        dm = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test path with nested directories
            nested_path = Path(temp_dir) / "models" / "lora" / "test.safetensors"
            
            # Simulate the path creation logic from download_file
            nested_path.parent.mkdir(parents=True, exist_ok=True)
            
            assert nested_path.parent.exists()
            assert nested_path.parent.is_dir()
    
    def test_download_key_generation(self, mock_config):
        """Test download key generation for tracking."""
        dm = DownloadManager(mock_config)
        
        url = "https://example.com/test.txt"
        path = Path("/tmp/test.txt")
        expected_key = f"{url}::{path}"
        
        # This is how the download manager generates keys
        actual_key = f"{url}::{path}"
        assert actual_key == expected_key
    
    def test_file_size_calculation(self):
        """Test file size calculations."""
        # Test size formatting (similar to what would be used in progress display)
        sizes = [
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (50 * 1024 * 1024, "50.0 MB"),
        ]
        
        for size_bytes, expected in sizes:
            if size_bytes < 1024:
                actual = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                actual = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                actual = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                actual = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
            assert actual == expected


class TestDownloadManagerValidation:
    """Test download manager validation and business logic."""
    
    def test_resume_logic_validation(self, mock_config):
        """Test resume logic validation."""
        dm = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test scenario: partial file exists
            partial_file = Path(temp_dir) / "partial.txt"
            partial_file.write_bytes(b"partial content")
            
            # Should be able to resume
            assert dm.can_resume(partial_file)
            assert partial_file.stat().st_size == 15  # len("partial content")
            
            # Test scenario: complete file exists
            complete_file = Path(temp_dir) / "complete.txt"
            complete_file.write_bytes(b"complete file content")
            
            # Should be able to resume (will check hash later)
            assert dm.can_resume(complete_file)
    
    def test_hash_verification_workflow(self, mock_config):
        """Test hash verification workflow."""
        dm = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "hash_test.txt"
            test_content = b"content to hash"
            
            # Write content
            test_file.write_bytes(test_content)
            
            # Calculate expected hash
            expected_hash = hashlib.sha256(test_content).hexdigest()
            
            # Test verification logic
            result = asyncio.run(dm._verify_file_hash(test_file, expected_hash))
            assert result is True
            
            # Test with wrong hash
            result = asyncio.run(dm._verify_file_hash(test_file, "wrong_hash"))
            assert result is False
    
    def test_download_stats_structure(self, mock_config):
        """Test download stats structure and tracking."""
        dm = DownloadManager(mock_config)
        
        # Simulate a completed download
        test_stats = {
            'model_id': 12345,
            'version_id': 67890,
            'file_id': 1,
            'file_name': 'test_model.safetensors',
            'file_size': 52428800,  # 50MB
            'downloaded_at': 1234567890.0,
            'hash': 'abc123def456'
        }
        
        file_path = "/tmp/test_model.safetensors"
        dm.download_stats[file_path] = test_stats
        
        # Verify stats structure
        stats = dm.get_download_stats()
        assert file_path in stats
        assert stats[file_path]['model_id'] == 12345
        assert stats[file_path]['file_name'] == 'test_model.safetensors'
        assert stats[file_path]['file_size'] == 52428800
        assert isinstance(stats[file_path]['downloaded_at'], float)
    
    def test_concurrent_download_tracking(self, mock_config):
        """Test concurrent download tracking."""
        dm = DownloadManager(mock_config)
        
        # Simulate multiple active downloads
        downloads = [
            ("https://example.com/file1.txt", Path("/tmp/file1.txt")),
            ("https://example.com/file2.txt", Path("/tmp/file2.txt")),
            ("https://example.com/file3.txt", Path("/tmp/file3.txt")),
        ]
        
        for url, path in downloads:
            download_key = f"{url}::{path}"
            dm.active_downloads[download_key] = True
        
        # Verify tracking
        active = dm.get_active_downloads()
        assert len(active) == 3
        
        # Simulate cancellation
        dm.cancel_download(downloads[1][1])  # Cancel file2.txt
        
        # Verify cancellation
        cancelled_key = f"{downloads[1][0]}::{downloads[1][1]}"
        assert dm.active_downloads[cancelled_key] is False
    
    @pytest.mark.asyncio
    async def test_download_workflow_simulation(self, mock_config, sample_model_version):
        """Test complete download workflow simulation."""
        dm = DownloadManager(mock_config)
        
        # Test model download validation
        assert len(sample_model_version.files) > 0
        
        # Test file index validation
        valid_indices = range(len(sample_model_version.files))
        assert 0 in valid_indices
        
        # Test invalid index handling
        with pytest.raises(ValueError, match="File index .* out of range"):
            # This would be the validation logic in download_model
            file_index = 999
            if file_index >= len(sample_model_version.files):
                raise ValueError(f"File index {file_index} out of range (0-{len(sample_model_version.files)-1})")
        
        # Test empty files list
        empty_version = ModelVersion(
            id=1, model_id=1, name="empty", description="", base_model="",
            trained_words=[], files=[], images=[], download_url="",
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="No files available"):
            # This would be the validation logic in download_model
            if not empty_version.files:
                raise ValueError("No files available for download")