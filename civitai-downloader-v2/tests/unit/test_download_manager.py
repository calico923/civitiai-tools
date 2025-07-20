#!/usr/bin/env python3
"""
Download Manager tests.
Tests for concurrent downloads with resume capability, progress tracking, and integrity verification.
"""

import pytest
import asyncio
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.download.manager import (
    DownloadManager, DownloadTask, FileInfo, ProgressUpdate,
    DownloadStatus, DownloadPriority,
    download_model_file, create_file_info_from_api
)
from api.auth import AuthManager


class TestFileInfo:
    """Test FileInfo data class."""
    
    def test_file_info_creation(self):
        """Test FileInfo object creation."""
        file_info = FileInfo(
            id=12345,
            name="test_model.safetensors",
            url="https://example.com/test.safetensors",
            size=1024*1024,
            hash_sha256="abcdef123456",
            type="Model",
            primary=True
        )
        
        assert file_info.id == 12345
        assert file_info.name == "test_model.safetensors"
        assert file_info.url == "https://example.com/test.safetensors"
        assert file_info.size == 1024*1024
        assert file_info.hash_sha256 == "abcdef123456"
        assert file_info.type == "Model"
        assert file_info.primary is True
    
    def test_create_file_info_from_api(self):
        """Test creating FileInfo from API data."""
        api_data = {
            'id': 54321,
            'name': 'model_v2.ckpt',
            'downloadUrl': 'https://civitai.com/api/download/models/54321',
            'sizeKB': 2048,
            'hashes': {
                'SHA256': 'hash256',
                'BLAKE3': 'hash_blake3'
            },
            'type': 'Model',
            'virusScanResult': 'Success',
            'primary': False
        }
        
        file_info = create_file_info_from_api(api_data)
        
        assert file_info.id == 54321
        assert file_info.name == 'model_v2.ckpt'
        assert file_info.url == 'https://civitai.com/api/download/models/54321'
        assert file_info.size == 2048 * 1024  # KB to bytes conversion
        assert file_info.hash_sha256 == 'hash256'
        assert file_info.hash_blake3 == 'hash_blake3'
        assert file_info.type == 'Model'
        assert file_info.scan_result == 'Success'
        assert file_info.primary is False


class TestDownloadTask:
    """Test DownloadTask data class."""
    
    def test_download_task_creation(self):
        """Test DownloadTask creation with defaults."""
        file_info = FileInfo(
            id=123,
            name="test.safetensors",
            url="https://example.com/test.safetensors",
            size=1000000
        )
        
        output_path = Path("/tmp/test.safetensors")
        
        task = DownloadTask(
            id="task_123",
            file_info=file_info,
            output_path=output_path
        )
        
        assert task.id == "task_123"
        assert task.file_info == file_info
        assert task.output_path == output_path
        assert task.status == DownloadStatus.PENDING
        assert task.priority == DownloadPriority.NORMAL
        assert task.downloaded_bytes == 0
        assert task.max_retries == 3
        assert task.resume is True
        assert task.verify_integrity is True


class TestDownloadManager:
    """Test DownloadManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.auth_manager = AuthManager()
        
        # Use temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Mock configuration
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'download.concurrent_downloads': 2,
            'download.chunk_size': 1024,
            'download.paths.models': str(self.temp_path / 'models'),
            'download.paths.temp': str(self.temp_path / 'temp')
        }.get(key, default)
        
        self.manager = DownloadManager(self.auth_manager, mock_config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_initialization(self):
        """Test download manager initialization."""
        assert self.manager.auth_manager == self.auth_manager
        assert self.manager.max_concurrent == 2
        assert self.manager.chunk_size == 1024
        assert self.manager.default_output_dir.exists()
        assert self.manager.temp_dir.exists()
        assert len(self.manager.tasks) == 0
        assert len(self.manager.active_downloads) == 0
    
    def test_create_download_task(self):
        """Test creating a download task."""
        file_info = FileInfo(
            id=123,
            name="test_model.safetensors",
            url="https://example.com/test.safetensors",
            size=1000000
        )
        
        task_id = self.manager.create_download_task(
            file_info,
            priority=DownloadPriority.HIGH
        )
        
        assert task_id in self.manager.tasks
        assert task_id in self.manager.download_queue
        
        task = self.manager.tasks[task_id]
        assert task.file_info == file_info
        assert task.priority == DownloadPriority.HIGH
        assert task.status == DownloadStatus.PENDING
        assert task.output_path.parent == self.manager.default_output_dir
        assert task.temp_path.parent == self.manager.temp_dir
    
    def test_task_priority_queue(self):
        """Test download queue is sorted by priority."""
        # Create tasks with different priorities
        file_info = FileInfo(id=1, name="test.txt", url="http://example.com", size=100)
        
        task_low = self.manager.create_download_task(file_info, priority=DownloadPriority.LOW)
        task_normal = self.manager.create_download_task(file_info, priority=DownloadPriority.NORMAL)
        task_high = self.manager.create_download_task(file_info, priority=DownloadPriority.HIGH)
        task_urgent = self.manager.create_download_task(file_info, priority=DownloadPriority.URGENT)
        
        # Queue should be sorted by priority (highest first)
        priorities = [self.manager.tasks[tid].priority.value for tid in self.manager.download_queue]
        assert priorities == sorted(priorities, reverse=True)
        
        # First task should be URGENT
        first_task_id = self.manager.download_queue[0]
        assert self.manager.tasks[first_task_id].priority == DownloadPriority.URGENT
    
    def test_filename_sanitization(self):
        """Test filename sanitization for safe storage."""
        dangerous_names = [
            "model<>:\"|?*.safetensors",
            "very_long_name_" + "x" * 200 + ".ckpt",
            "model/with\\path.safetensors",
            "normal_name.safetensors"
        ]
        
        for name in dangerous_names:
            sanitized = self.manager._sanitize_filename(name)
            
            # Should not contain dangerous characters
            dangerous_chars = '<>:"|?*\\/\x00'
            for char in dangerous_chars:
                assert char not in sanitized
            
            # Should not be too long
            assert len(sanitized) <= 200
            
            # Should preserve extension if reasonable
            if '.' in name and len(name) < 200:
                assert '.' in sanitized
    
    def test_unique_path_generation(self):
        """Test generation of unique paths for duplicate files."""
        base_path = self.temp_path / "test.txt"
        
        # Create the base file
        base_path.touch()
        
        # Generate unique path
        unique_path = self.manager._generate_unique_path(base_path)
        
        assert unique_path != base_path
        assert not unique_path.exists()
        assert unique_path.stem == "test_1"
        assert unique_path.suffix == ".txt"
        
        # Create that file too and test again
        unique_path.touch()
        unique_path2 = self.manager._generate_unique_path(base_path)
        
        assert unique_path2.stem == "test_2"
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test aiohttp session management."""
        session1 = await self.manager._get_session()
        session2 = await self.manager._get_session()
        
        # Should reuse the same session
        assert session1 is session2
        assert not session1.closed
        
        # Test cleanup
        await self.manager.close()
        assert session1.closed
    
    def test_progress_callback_management(self):
        """Test progress callback management."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        self.manager.add_progress_callback(callback1)
        self.manager.add_progress_callback(callback2)
        
        assert len(self.manager.progress_callbacks) == 2
        assert callback1 in self.manager.progress_callbacks
        assert callback2 in self.manager.progress_callbacks
        
        # Remove callback
        self.manager.remove_progress_callback(callback1)
        
        assert len(self.manager.progress_callbacks) == 1
        assert callback1 not in self.manager.progress_callbacks
        assert callback2 in self.manager.progress_callbacks
    
    def test_progress_notification(self):
        """Test progress notification system."""
        callback = Mock()
        self.manager.add_progress_callback(callback)
        
        # Create a task
        file_info = FileInfo(id=123, name="test.txt", url="http://example.com", size=1000)
        task_id = self.manager.create_download_task(file_info)
        task = self.manager.tasks[task_id]
        
        # Update task progress
        task.downloaded_bytes = 500
        task.current_speed = 1024.0
        
        # Notify progress
        self.manager._notify_progress(task)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Check progress update data
        update = callback.call_args[0][0]
        assert isinstance(update, ProgressUpdate)
        assert update.task_id == task_id
        assert update.status == DownloadStatus.PENDING
        assert update.downloaded_bytes == 500
        assert update.total_bytes == 1000
        assert update.progress_percent == 50.0
        assert update.current_speed == 1024.0
    
    @pytest.mark.asyncio
    async def test_pause_resume_cancel(self):
        """Test pause, resume, and cancel operations."""
        file_info = FileInfo(id=123, name="test.txt", url="http://example.com", size=1000)
        task_id = self.manager.create_download_task(file_info)
        task = self.manager.tasks[task_id]
        
        # Set task as downloading
        task.status = DownloadStatus.DOWNLOADING
        
        # Test pause
        result = await self.manager.pause_download(task_id)
        assert result is True
        assert task.status == DownloadStatus.PAUSED
        
        # Test resume
        result = await self.manager.resume_download(task_id)
        assert result is True
        assert task.status == DownloadStatus.DOWNLOADING
        
        # Test cancel
        result = await self.manager.cancel_download(task_id)
        assert result is True
        assert task.status == DownloadStatus.CANCELLED
    
    def test_get_task_status(self):
        """Test getting task status."""
        file_info = FileInfo(id=123, name="test.txt", url="http://example.com", size=1000)
        task_id = self.manager.create_download_task(file_info)
        
        # Get existing task
        task = self.manager.get_task_status(task_id)
        assert task is not None
        assert task.id == task_id
        
        # Get non-existent task
        non_existent = self.manager.get_task_status("non_existent")
        assert non_existent is None
    
    def test_get_all_tasks(self):
        """Test getting all tasks."""
        file_info = FileInfo(id=123, name="test.txt", url="http://example.com", size=1000)
        
        # Create multiple tasks
        task_id1 = self.manager.create_download_task(file_info)
        task_id2 = self.manager.create_download_task(file_info)
        
        all_tasks = self.manager.get_all_tasks()
        
        assert len(all_tasks) == 2
        task_ids = [task.id for task in all_tasks]
        assert task_id1 in task_ids
        assert task_id2 in task_ids
    
    def test_download_stats(self):
        """Test download statistics tracking."""
        initial_stats = self.manager.get_download_stats()
        
        expected_keys = [
            'total_downloads', 'successful_downloads', 'failed_downloads',
            'total_bytes_downloaded', 'average_speed'
        ]
        
        for key in expected_keys:
            assert key in initial_stats
            assert initial_stats[key] == 0 or initial_stats[key] == 0.0


class TestProgressUpdate:
    """Test ProgressUpdate data class."""
    
    def test_progress_update_creation(self):
        """Test ProgressUpdate creation."""
        update = ProgressUpdate(
            task_id="task_123",
            status=DownloadStatus.DOWNLOADING,
            downloaded_bytes=512000,
            total_bytes=1024000,
            progress_percent=50.0,
            current_speed=1024.0,
            eta_seconds=500.0
        )
        
        assert update.task_id == "task_123"
        assert update.status == DownloadStatus.DOWNLOADING
        assert update.downloaded_bytes == 512000
        assert update.total_bytes == 1024000
        assert update.progress_percent == 50.0
        assert update.current_speed == 1024.0
        assert update.eta_seconds == 500.0
        assert update.error_message is None


class TestDownloadEnums:
    """Test download-related enums."""
    
    def test_download_status_enum(self):
        """Test DownloadStatus enum values."""
        assert DownloadStatus.PENDING.value == "pending"
        assert DownloadStatus.DOWNLOADING.value == "downloading"
        assert DownloadStatus.PAUSED.value == "paused"
        assert DownloadStatus.COMPLETED.value == "completed"
        assert DownloadStatus.FAILED.value == "failed"
        assert DownloadStatus.CANCELLED.value == "cancelled"
    
    def test_download_priority_enum(self):
        """Test DownloadPriority enum values."""
        assert DownloadPriority.LOW.value == 1
        assert DownloadPriority.NORMAL.value == 2
        assert DownloadPriority.HIGH.value == 3
        assert DownloadPriority.URGENT.value == 4
        
        # Test priority ordering
        assert DownloadPriority.URGENT.value > DownloadPriority.HIGH.value
        assert DownloadPriority.HIGH.value > DownloadPriority.NORMAL.value
        assert DownloadPriority.NORMAL.value > DownloadPriority.LOW.value


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_download_model_file_function(self):
        """Test download_model_file utility function."""
        file_info = FileInfo(
            id=123,
            name="test.txt",
            url="http://example.com/test.txt",
            size=1000
        )
        
        progress_callback = Mock()
        
        # Mock the actual download to avoid real HTTP requests
        with patch('core.download.manager.DownloadManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.create_download_task.return_value = "task_123"
            mock_manager.start_download = AsyncMock(return_value=True)
            mock_manager.process_download_queue = AsyncMock(return_value=None)
            
            task_id = await download_model_file(file_info, None, progress_callback)
            
            assert task_id == "task_123"
            mock_manager.add_progress_callback.assert_called_once_with(progress_callback)
            mock_manager.create_download_task.assert_called_once_with(file_info, None)
            mock_manager.start_download.assert_called_once_with("task_123")
            mock_manager.process_download_queue.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])