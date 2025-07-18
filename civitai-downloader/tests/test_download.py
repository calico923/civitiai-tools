"""Tests for download manager functionality."""

import pytest
import asyncio
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
import aiofiles
import json
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


@pytest.fixture
def sample_model_info():
    """Create sample model info."""
    return ModelInfo(
        id=12345,
        name="Test Model",
        type=ModelType.LORA,
        description="Test model",
        tags=["test"],
        creator="test_user",
        stats={"downloadCount": 100},
        nsfw=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestDownloadManager:
    """Test DownloadManager functionality."""
    
    @pytest.mark.asyncio
    async def test_download_manager_context_manager(self, mock_config):
        """Test DownloadManager as async context manager."""
        download_manager = DownloadManager(mock_config)
        
        # Test context manager
        async with download_manager as dm:
            assert dm.session is not None
            assert dm.session.connector._limit == 3  # max_concurrent_downloads
    
    @pytest.mark.asyncio
    async def test_can_resume_download(self, mock_config):
        """Test resume capability detection."""
        download_manager = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test non-existent file
            non_existent_path = Path(temp_dir) / "non_existent.txt"
            assert not download_manager.can_resume(non_existent_path)
            
            # Test existing file with content
            existing_path = Path(temp_dir) / "existing.txt"
            existing_path.write_text("test content")
            assert download_manager.can_resume(existing_path)
            
            # Test empty file
            empty_path = Path(temp_dir) / "empty.txt"
            empty_path.touch()
            assert not download_manager.can_resume(empty_path)
    
    @pytest.mark.asyncio
    async def test_get_file_size(self, mock_config):
        """Test remote file size detection."""
        download_manager = DownloadManager(mock_config)
        
        # Mock the session properly
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.headers = {'Content-Length': '1048576'}  # 1MB
        mock_response.raise_for_status.return_value = None
        
        # Create proper async context manager
        async def mock_head(url):
            return mock_response
        
        mock_session.head = mock_head
        download_manager.session = mock_session
        
        file_size = await download_manager._get_file_size("https://example.com/file.txt")
        assert file_size == 1048576
        
        # Test missing Content-Length
        mock_response.headers = {}
        file_size = await download_manager._get_file_size("https://example.com/file.txt")
        assert file_size is None
    
    @pytest.mark.asyncio
    async def test_verify_file_hash(self, mock_config):
        """Test file hash verification."""
        download_manager = DownloadManager(mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_content = b"test content for hash verification"
            
            # Write test content
            async with aiofiles.open(test_file, 'wb') as f:
                await f.write(test_content)
            
            # Calculate expected hash
            expected_hash = hashlib.sha256(test_content).hexdigest()
            
            # Test correct hash
            assert await download_manager._verify_file_hash(test_file, expected_hash)
            
            # Test incorrect hash
            wrong_hash = "wrong_hash_value"
            assert not await download_manager._verify_file_hash(test_file, wrong_hash)
            
            # Test empty hash (should pass)
            assert await download_manager._verify_file_hash(test_file, "")
    
    @pytest.mark.asyncio
    async def test_download_file_basic(self, mock_config):
        """Test basic file download functionality."""
        download_manager = DownloadManager(mock_config)
        
        # Mock response data
        test_content = b"test file content for download"
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': str(len(test_content))}
            mock_response.raise_for_status.return_value = None
            
            # Mock content iteration
            async def mock_iter_chunked(chunk_size):
                yield test_content
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "downloaded_file.txt"
                
                # Track progress updates
                progress_updates = []
                
                def progress_callback(progress: DownloadProgress):
                    progress_updates.append(progress)
                
                await download_manager.download_file(
                    url="https://example.com/test.txt",
                    path=download_path,
                    progress_callback=progress_callback
                )
                
                # Verify file was created and has correct content
                assert download_path.exists()
                assert download_path.read_bytes() == test_content
                
                # Verify progress updates were sent
                assert len(progress_updates) > 0
                final_progress = progress_updates[-1]
                assert final_progress.percent == 100.0
                assert final_progress.downloaded_bytes == len(test_content)
    
    @pytest.mark.asyncio
    async def test_download_file_with_resume(self, mock_config):
        """Test file download with resume capability."""
        download_manager = DownloadManager(mock_config)
        
        partial_content = b"partial content"
        remaining_content = b" remaining content"
        full_content = partial_content + remaining_content
        
        with tempfile.TemporaryDirectory() as temp_dir:
            download_path = Path(temp_dir) / "resume_test.txt"
            
            # Write partial content to simulate interrupted download
            download_path.write_bytes(partial_content)
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                
                # Mock HEAD response
                mock_head_response = AsyncMock()
                mock_head_response.headers = {'Content-Length': str(len(full_content))}
                mock_head_response.raise_for_status.return_value = None
                
                # Mock GET response (resume)
                mock_get_response = AsyncMock()
                mock_get_response.headers = {'Content-Length': str(len(remaining_content))}
                mock_get_response.raise_for_status.return_value = None
                
                async def mock_iter_chunked(chunk_size):
                    yield remaining_content
                
                mock_get_response.content.iter_chunked = mock_iter_chunked
                
                mock_session.head.return_value.__aenter__.return_value = mock_head_response
                mock_session.get.return_value.__aenter__.return_value = mock_get_response
                download_manager.session = mock_session
                
                await download_manager.download_file(
                    url="https://example.com/test.txt",
                    path=download_path
                )
                
                # Verify file has full content
                assert download_path.read_bytes() == full_content
                
                # Verify range header was sent
                mock_session.get.assert_called_with(
                    "https://example.com/test.txt",
                    headers={'Range': f'bytes={len(partial_content)}-'}
                )
    
    @pytest.mark.asyncio
    async def test_download_file_with_hash_verification(self, mock_config):
        """Test file download with hash verification."""
        download_manager = DownloadManager(mock_config)
        
        test_content = b"content for hash verification"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': str(len(test_content))}
            mock_response.raise_for_status.return_value = None
            
            async def mock_iter_chunked(chunk_size):
                yield test_content
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "hash_test.txt"
                
                # Test successful hash verification
                await download_manager.download_file(
                    url="https://example.com/test.txt",
                    path=download_path,
                    expected_hash=expected_hash
                )
                
                assert download_path.exists()
                assert download_path.read_bytes() == test_content
                
                # Test hash mismatch (should remove file and raise error)
                download_path2 = Path(temp_dir) / "hash_fail.txt"
                wrong_hash = "wrong_hash_value"
                
                with pytest.raises(RuntimeError, match="File integrity check failed"):
                    await download_manager.download_file(
                        url="https://example.com/test.txt",
                        path=download_path2,
                        expected_hash=wrong_hash
                    )
                
                # File should be removed after hash failure
                assert not download_path2.exists()
    
    @pytest.mark.asyncio
    async def test_download_model_single_file(self, mock_config, sample_model_version):
        """Test downloading a single model file."""
        download_manager = DownloadManager(mock_config)
        
        test_content = b"fake model file content"
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': str(len(test_content))}
            mock_response.raise_for_status.return_value = None
            
            async def mock_iter_chunked(chunk_size):
                yield test_content
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir)
                
                progress_updates = []
                
                def progress_callback(progress: DownloadProgress):
                    progress_updates.append(progress)
                
                await download_manager.download_model(
                    version=sample_model_version,
                    path=download_path,
                    file_index=0,
                    progress_callback=progress_callback
                )
                
                # Verify file structure
                expected_path = download_path / f"model_{sample_model_version.model_id}" / f"version_{sample_model_version.id}" / "test_model.safetensors"
                assert expected_path.exists()
                assert expected_path.read_bytes() == test_content
                
                # Verify progress was tracked
                assert len(progress_updates) > 0
                
                # Verify download stats were recorded
                stats = download_manager.get_download_stats()
                assert str(expected_path) in stats
                assert stats[str(expected_path)]['model_id'] == sample_model_version.model_id
    
    @pytest.mark.asyncio
    async def test_download_all_model_files(self, mock_config, sample_model_version):
        """Test downloading all files for a model version."""
        # Add a second file to the version
        second_file = ModelFile(
            id=2,
            name="config.json",
            size_bytes=1024,
            format="Config",
            fp=None,
            hash="config_hash",
            download_url="https://example.com/config.json",
            metadata={}
        )
        sample_model_version.files.append(second_file)
        
        download_manager = DownloadManager(mock_config)
        
        # Mock different content for each file
        file_contents = {
            "test_model.safetensors": b"model file content",
            "config.json": b'{"test": "config"}'
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            def create_mock_response(url):
                mock_response = AsyncMock()
                filename = url.split('/')[-1]
                content = file_contents.get(filename, b"default content")
                mock_response.headers = {'Content-Length': str(len(content))}
                mock_response.raise_for_status.return_value = None
                
                async def mock_iter_chunked(chunk_size):
                    yield content
                
                mock_response.content.iter_chunked = mock_iter_chunked
                return mock_response
            
            async def mock_head_call(url):
                response = create_mock_response(url)
                return response
            
            async def mock_get_call(url, headers=None):
                response = create_mock_response(url)
                return response
            
            mock_session.head.side_effect = lambda url: mock_head_call(url)
            mock_session.get.side_effect = lambda url, headers=None: mock_get_call(url, headers)
            
            # Mock context manager returns
            mock_session.head.return_value.__aenter__.side_effect = lambda: mock_head_call(mock_session.head.call_args[0][0])
            mock_session.get.return_value.__aenter__.side_effect = lambda: mock_get_call(mock_session.get.call_args[0][0])
            
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir)
                
                progress_updates = []
                
                def progress_callback(file_desc: str, progress: DownloadProgress):
                    progress_updates.append((file_desc, progress))
                
                await download_manager.download_all_model_files(
                    version=sample_model_version,
                    path=download_path,
                    progress_callback=progress_callback
                )
                
                # Verify both files were downloaded
                model_dir = download_path / f"model_{sample_model_version.model_id}" / f"version_{sample_model_version.id}"
                
                model_file_path = model_dir / "test_model.safetensors"
                config_file_path = model_dir / "config.json"
                
                assert model_file_path.exists()
                assert config_file_path.exists()
                
                # Verify content
                assert model_file_path.read_bytes() == file_contents["test_model.safetensors"]
                assert config_file_path.read_bytes() == file_contents["config.json"]
                
                # Verify progress tracking for both files
                assert len(progress_updates) > 0
    
    @pytest.mark.asyncio
    async def test_download_cancellation(self, mock_config):
        """Test download cancellation functionality."""
        download_manager = DownloadManager(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': '1000'}
            mock_response.raise_for_status.return_value = None
            
            # Mock slow download with multiple chunks
            async def mock_iter_chunked(chunk_size):
                for i in range(10):
                    await asyncio.sleep(0.1)  # Simulate slow download
                    yield b"chunk_data"
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "cancelled_download.txt"
                
                # Start download and cancel after short delay
                async def cancel_after_delay():
                    await asyncio.sleep(0.2)
                    download_manager.cancel_download(download_path)
                
                # Run download and cancellation concurrently
                download_task = asyncio.create_task(
                    download_manager.download_file(
                        url="https://example.com/slow.txt",
                        path=download_path
                    )
                )
                
                cancel_task = asyncio.create_task(cancel_after_delay())
                
                # Wait for both tasks
                await asyncio.gather(download_task, cancel_task, return_exceptions=True)
                
                # Verify download was cancelled (file should be incomplete or not exist)
                # The exact behavior depends on timing, but we should have some indication
                # that cancellation was processed
                active_downloads = download_manager.get_active_downloads()
                assert len(active_downloads) == 0  # Should be cleaned up
    
    def test_download_error_handling(self, mock_config):
        """Test error handling in download manager."""
        download_manager = DownloadManager(mock_config)
        
        # Test error when session not initialized
        with pytest.raises(RuntimeError, match="Download manager not initialized"):
            asyncio.run(download_manager.download_file(
                url="https://example.com/test.txt",
                path=Path("/tmp/test.txt")
            ))
        
        # Test invalid file index
        version = ModelVersion(
            id=1, model_id=1, name="test", description="", base_model="",
            trained_words=[], files=[], images=[], download_url="",
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="No files available for download"):
            asyncio.run(download_manager.download_model(version, Path("/tmp"), 0))


class TestProgressDisplay:
    """Test ProgressDisplay functionality."""
    
    def test_progress_display_creation(self):
        """Test progress display creation and configuration."""
        display = ProgressDisplay(show_speed=True, show_eta=True)
        assert display.show_speed is True
        assert display.show_eta is True
        assert len(display.progress_bars) == 0
        
        display_minimal = ProgressDisplay(show_speed=False, show_eta=False)
        assert display_minimal.show_speed is False
        assert display_minimal.show_eta is False
    
    def test_progress_bar_lifecycle(self):
        """Test progress bar creation and cleanup."""
        display = ProgressDisplay()
        
        # Create progress bar
        pbar = display.create_progress_bar("test_file.txt", 1000)
        assert "test_file.txt" in display.progress_bars
        assert pbar.total == 1000
        
        # Update progress
        progress = DownloadProgress(
            file_name="test_file.txt",
            total_bytes=1000,
            downloaded_bytes=500,
            percent=50.0,
            speed_mbps=1.5,
            eta_seconds=10.0
        )
        
        display.update_progress(progress)
        assert pbar.n == 500
        
        # Close progress bar
        display.close_progress_bar("test_file.txt")
        assert "test_file.txt" not in display.progress_bars
    
    def test_format_eta(self):
        """Test ETA formatting."""
        display = ProgressDisplay()
        
        # Test seconds
        assert display._format_eta(30) == "30s"
        
        # Test minutes
        assert display._format_eta(120) == "2m"
        
        # Test hours
        assert display._format_eta(7200) == "2.0h"
        
        # Test fractional minutes
        assert display._format_eta(90) == "2m"  # 1.5 minutes rounds to 2


class TestBatchDownloadManager:
    """Test BatchDownloadManager functionality."""
    
    @pytest.mark.asyncio
    async def test_batch_download_creation(self, mock_config):
        """Test batch download manager creation."""
        download_manager = DownloadManager(mock_config)
        batch_manager = BatchDownloadManager(download_manager, max_concurrent=2)
        
        assert batch_manager.download_manager == download_manager
        assert batch_manager.max_concurrent == 2
        assert batch_manager.semaphore._value == 2
    
    @pytest.mark.asyncio
    async def test_batch_download_multiple_models(self, mock_config):
        """Test downloading multiple models in batch."""
        download_manager = DownloadManager(mock_config)
        batch_manager = BatchDownloadManager(download_manager, max_concurrent=2)
        
        # Create multiple test versions
        versions = []
        for i in range(3):
            file_info = ModelFile(
                id=i,
                name=f"model_{i}.safetensors",
                size_bytes=1024,
                format="Model",
                fp="fp16",
                hash=f"hash_{i}",
                download_url=f"https://example.com/model_{i}.safetensors",
                metadata={}
            )
            
            version = ModelVersion(
                id=i,
                model_id=i,
                name=f"v{i}",
                description=f"Version {i}",
                base_model="SD 1.5",
                trained_words=[],
                files=[file_info],
                images=[],
                download_url=f"https://example.com/version_{i}",
                created_at=datetime.now()
            )
            versions.append(version)
        
        # Mock download manager
        with patch.object(download_manager, 'download_all_model_files') as mock_download:
            mock_download.return_value = None
            
            with tempfile.TemporaryDirectory() as temp_dir:
                await batch_manager.download_multiple_models(
                    versions=versions,
                    base_path=Path(temp_dir)
                )
                
                # Verify all versions were processed
                assert mock_download.call_count == 3
                
                # Verify each version was called with correct parameters
                for i, call in enumerate(mock_download.call_args_list):
                    args, kwargs = call
                    assert kwargs['version'].id == i
                    assert kwargs['path'] == Path(temp_dir)
    
    def test_batch_cleanup(self, mock_config):
        """Test batch manager cleanup."""
        download_manager = DownloadManager(mock_config)
        batch_manager = BatchDownloadManager(download_manager)
        
        # Create some progress bars
        batch_manager.progress_display.create_progress_bar("test1.txt", 1000)
        batch_manager.progress_display.create_progress_bar("test2.txt", 2000)
        
        assert len(batch_manager.progress_display.progress_bars) == 2
        
        # Cleanup should close all progress bars
        batch_manager.cleanup()
        
        assert len(batch_manager.progress_display.progress_bars) == 0


class TestDownloadIntegration:
    """Integration tests for download functionality."""
    
    @pytest.mark.asyncio
    async def test_full_download_workflow(self, mock_config, sample_model_version, sample_model_info):
        """Test complete download workflow from model info to file."""
        download_manager = DownloadManager(mock_config)
        
        test_content = b"complete model file content"
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': str(len(test_content))}
            mock_response.raise_for_status.return_value = None
            
            async def mock_iter_chunked(chunk_size):
                yield test_content
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir)
                
                # Track complete workflow
                progress_history = []
                
                def progress_callback(progress: DownloadProgress):
                    progress_history.append({
                        'file_name': progress.file_name,
                        'percent': progress.percent,
                        'downloaded_bytes': progress.downloaded_bytes,
                        'total_bytes': progress.total_bytes,
                        'speed_mbps': progress.speed_mbps
                    })
                
                # Execute full download
                await download_manager.download_model(
                    version=sample_model_version,
                    path=download_path,
                    file_index=0,
                    progress_callback=progress_callback
                )
                
                # Verify final state
                expected_path = download_path / f"model_{sample_model_version.model_id}" / f"version_{sample_model_version.id}" / "test_model.safetensors"
                assert expected_path.exists()
                assert expected_path.read_bytes() == test_content
                
                # Verify progress tracking
                assert len(progress_history) > 0
                assert progress_history[-1]['percent'] == 100.0
                assert progress_history[-1]['file_name'] == "test_model.safetensors"
                
                # Verify download stats
                stats = download_manager.get_download_stats()
                assert str(expected_path) in stats
                
                stat_entry = stats[str(expected_path)]
                assert stat_entry['model_id'] == sample_model_version.model_id
                assert stat_entry['version_id'] == sample_model_version.id
                assert stat_entry['file_name'] == "test_model.safetensors"
                assert stat_entry['hash'] == "abc123def456"
    
    @pytest.mark.asyncio
    async def test_concurrent_downloads(self, mock_config):
        """Test concurrent download handling."""
        download_manager = DownloadManager(mock_config)
        
        test_content = b"concurrent test content"
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'Content-Length': str(len(test_content))}
            mock_response.raise_for_status.return_value = None
            
            async def mock_iter_chunked(chunk_size):
                await asyncio.sleep(0.1)  # Simulate network delay
                yield test_content
            
            mock_response.content.iter_chunked = mock_iter_chunked
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir)
                
                # Create multiple download tasks
                tasks = []
                for i in range(3):
                    file_path = download_path / f"concurrent_file_{i}.txt"
                    task = asyncio.create_task(
                        download_manager.download_file(
                            url=f"https://example.com/file_{i}.txt",
                            path=file_path
                        )
                    )
                    tasks.append(task)
                
                # Wait for all downloads to complete
                await asyncio.gather(*tasks)
                
                # Verify all files were downloaded
                for i in range(3):
                    file_path = download_path / f"concurrent_file_{i}.txt"
                    assert file_path.exists()
                    assert file_path.read_bytes() == test_content
    
    @pytest.mark.asyncio
    async def test_download_with_network_error_recovery(self, mock_config):
        """Test download behavior with network errors."""
        download_manager = DownloadManager(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("Network error")
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            download_manager.session = mock_session
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "error_test.txt"
                
                # Download should fail with network error
                with pytest.raises(Exception, match="Network error"):
                    await download_manager.download_file(
                        url="https://example.com/error_file.txt",
                        path=download_path
                    )
                
                # Verify file was not created
                assert not download_path.exists()