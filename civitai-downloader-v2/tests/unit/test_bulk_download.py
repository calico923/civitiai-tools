#!/usr/bin/env python3
"""
Tests for Bulk Download Manager.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
import time
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.bulk.download_manager import (
    BulkDownloadManager, BulkDownloadJob, BulkStatus,
    BatchStrategy, BatchConfig, create_bulk_download_from_search
)
from core.download.manager import FileInfo, DownloadStatus, DownloadPriority
from core.search.strategy import SearchResult, ModelType


class TestBulkDownloadJob:
    """Test BulkDownloadJob data class."""
    
    def test_bulk_download_job_creation(self):
        """Test BulkDownloadJob creation."""
        job = BulkDownloadJob(
            job_id="test-job-1",
            name="Test Bulk Download",
            search_results=[],
            total_files=10,
            total_size=1024 * 1024 * 100  # 100MB
        )
        
        assert job.job_id == "test-job-1"
        assert job.name == "Test Bulk Download"
        assert job.status == BulkStatus.PENDING
        assert job.total_files == 10
        assert job.total_size == 104857600
        assert job.downloaded_files == 0
        assert job.failed_files == 0
        assert isinstance(job.created_at, float)
        assert job.started_at is None
        assert job.completed_at is None
    
    def test_bulk_download_job_to_dict(self):
        """Test BulkDownloadJob serialization."""
        job = BulkDownloadJob(
            job_id="test-job-2",
            name="Test Job",
            search_results=[],
            total_files=5,
            options={'batch_size': 3}
        )
        
        job_dict = job.to_dict()
        
        assert job_dict['job_id'] == "test-job-2"
        assert job_dict['name'] == "Test Job"
        assert job_dict['status'] == "pending"
        assert job_dict['total_files'] == 5
        assert job_dict['options'] == {'batch_size': 3}
        assert 'created_at' in job_dict
        assert isinstance(job_dict['errors'], list)


class TestBatchConfig:
    """Test BatchConfig data class."""
    
    def test_batch_config_defaults(self):
        """Test BatchConfig default values."""
        config = BatchConfig()
        
        assert config.batch_size == 5
        assert config.concurrent_batches == 2
        assert config.strategy == BatchStrategy.ADAPTIVE
        assert config.auto_retry is True
        assert config.max_retries == 3
        assert config.pause_between_batches == 0.0
        assert config.priority_boost is True
    
    def test_batch_config_custom_values(self):
        """Test BatchConfig with custom values."""
        config = BatchConfig(
            batch_size=10,
            concurrent_batches=4,
            strategy=BatchStrategy.PARALLEL,
            auto_retry=False,
            priority_boost=False
        )
        
        assert config.batch_size == 10
        assert config.concurrent_batches == 4
        assert config.strategy == BatchStrategy.PARALLEL
        assert config.auto_retry is False
        assert config.priority_boost is False


class TestBulkDownloadManager:
    """Test BulkDownloadManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock configuration
        self.mock_config = Mock()
        self.mock_config.get.side_effect = lambda key, default=None: {
            'bulk.batch_size': 3,
            'bulk.concurrent_batches': 2,
            'bulk.strategy': 'adaptive',
            'bulk.auto_retry': True,
            'bulk.max_retries': 3,
            'bulk.pause_between_batches': 0.1,
            'bulk.priority_boost': True
        }.get(key, default)
        
        # Mock download manager
        self.mock_download_manager = Mock()
        self.mock_download_manager.create_download_task = Mock(side_effect=lambda **kwargs: f"task-{uuid.uuid4()}")
        self.mock_download_manager.start_download = AsyncMock(return_value=True)
        self.mock_download_manager.get_task_status = Mock()
        self.mock_download_manager.pause_download = AsyncMock(return_value=True)
        self.mock_download_manager.resume_download = AsyncMock(return_value=True)
        self.mock_download_manager.cancel_download = Mock()
        
        # Mock security scanner
        self.mock_security_scanner = Mock()
        self.mock_security_scanner.scan_file = Mock()
        
        # Create bulk download manager
        self.bulk_manager = BulkDownloadManager(
            download_manager=self.mock_download_manager,
            security_scanner=self.mock_security_scanner,
            config=self.mock_config
        )
    
    def test_initialization(self):
        """Test BulkDownloadManager initialization."""
        assert self.bulk_manager.batch_config.batch_size == 3
        assert self.bulk_manager.batch_config.concurrent_batches == 2
        assert self.bulk_manager.batch_config.strategy == BatchStrategy.ADAPTIVE
        assert len(self.bulk_manager.jobs) == 0
        assert len(self.bulk_manager.active_jobs) == 0
        assert self.bulk_manager.stats['total_jobs'] == 0
    
    @pytest.mark.asyncio
    async def test_create_bulk_job(self):
        """Test creating a bulk download job."""
        # Create mock search results
        mock_results = self._create_mock_search_results(2, 3)  # 2 models, 3 files each
        
        # Create job
        job_id = await self.bulk_manager.create_bulk_job(
            search_results=mock_results,
            name="Test Bulk Job",
            options={'test': True}
        )
        
        # Verify job creation
        assert isinstance(job_id, str)
        assert job_id in self.bulk_manager.jobs
        
        job = self.bulk_manager.jobs[job_id]
        assert job.name == "Test Bulk Job"
        assert job.status == BulkStatus.PENDING
        assert job.total_files == 6  # 2 models * 3 files
        assert job.options == {'test': True}
        assert self.bulk_manager.stats['total_jobs'] == 1
    
    @pytest.mark.asyncio
    async def test_process_job_success(self):
        """Test successful job processing."""
        # Create mock search results
        mock_results = self._create_mock_search_results(1, 2)  # 1 model, 2 files
        
        # Create job
        job_id = await self.bulk_manager.create_bulk_job(mock_results, "Test Job")
        
        # Mock successful downloads
        mock_task = Mock()
        mock_task.status = DownloadStatus.COMPLETED
        mock_task.final_path = Path("/tmp/test.safetensors")
        mock_task.file_info.id = 1
        mock_task.file_info.size = 1024
        self.mock_download_manager.get_task_status.return_value = mock_task
        
        # Mock successful security scan
        mock_scan_report = Mock()
        mock_scan_report.scan_result = Mock(value="safe")
        mock_scan_report.scan_result.name = "SAFE"
        from core.security.scanner import ScanResult
        mock_scan_report.scan_result = ScanResult.SAFE
        self.mock_security_scanner.scan_file.return_value = mock_scan_report
        
        # Process job
        await self.bulk_manager._process_job(job_id)
        
        # Verify job completion
        job = self.bulk_manager.jobs[job_id]
        assert job.status == BulkStatus.COMPLETED
        assert job.downloaded_files == 2
        assert job.failed_files == 0
        assert job.started_at is not None
        assert job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_process_job_with_failures(self):
        """Test job processing with failures."""
        # Create mock search results
        mock_results = self._create_mock_search_results(1, 3)
        
        # Create job
        job_id = await self.bulk_manager.create_bulk_job(mock_results, "Test Job")
        
        # Mock mixed results
        self.mock_download_manager.start_download = AsyncMock(
            side_effect=[True, False, True]  # Second download fails
        )
        
        # Mock successful task
        mock_task = Mock()
        mock_task.status = DownloadStatus.COMPLETED
        mock_task.final_path = Path("/tmp/test.safetensors")
        mock_task.file_info.id = 1
        mock_task.file_info.size = 1024
        
        # Mock failed task
        mock_failed_task = Mock()
        mock_failed_task.status = DownloadStatus.FAILED
        
        self.mock_download_manager.get_task_status.side_effect = [
            mock_task, mock_failed_task, mock_task
        ]
        
        # Mock security scan
        mock_scan_report = Mock()
        mock_scan_report.scan_result = Mock(value="safe")
        from core.security.scanner import ScanResult
        mock_scan_report.scan_result = ScanResult.SAFE
        self.mock_security_scanner.scan_file.return_value = mock_scan_report
        
        # Process job
        await self.bulk_manager._process_job(job_id)
        
        # Verify job completion with failures
        job = self.bulk_manager.jobs[job_id]
        assert job.status == BulkStatus.FAILED
        assert job.downloaded_files == 2
        assert job.failed_files == 1
    
    @pytest.mark.asyncio
    async def test_process_job_with_exceptions(self):
        """Test job processing with exception handling."""
        # Use standard exceptions instead of custom ones
        class NetworkError(Exception):
            pass
        
        class DiskFullError(Exception):
            pass
        
        # Create mock search results
        mock_results = self._create_mock_search_results(1, 3)
        
        # Create job
        job_id = await self.bulk_manager.create_bulk_job(mock_results, "Exception Test Job")
        
        # Mock start_download to raise exceptions
        self.mock_download_manager.start_download = AsyncMock(
            side_effect=[
                True,  # First succeeds
                NetworkError("Connection timeout"),  # Second throws NetworkError
                DiskFullError("No space left on device")  # Third throws DiskFullError
            ]
        )
        
        # Mock successful task for first download
        mock_task = Mock()
        mock_task.status = DownloadStatus.COMPLETED
        mock_task.final_path = Path("/tmp/test.safetensors")
        mock_task.file_info.id = 1
        mock_task.file_info.size = 1024
        
        self.mock_download_manager.get_task_status.return_value = mock_task
        
        # Mock security scan
        mock_scan_report = Mock()
        from core.security.scanner import ScanResult
        mock_scan_report.scan_result = ScanResult.SAFE
        self.mock_security_scanner.scan_file.return_value = mock_scan_report
        
        # Process job - should not crash despite exceptions
        await self.bulk_manager._process_job(job_id)
        
        # Verify job handling exceptions gracefully
        job = self.bulk_manager.jobs[job_id]
        assert job.status == BulkStatus.FAILED, "Job should be marked as failed due to exceptions"
        assert job.downloaded_files == 1, "Only first download should succeed"
        assert job.failed_files == 2, "Two downloads should fail due to exceptions"
        
        # Verify error information is captured
        assert len(job.errors) >= 2, "Error details should be captured for exceptions"
        error_messages = ' '.join(str(error) for error in job.errors)
        assert "NetworkError" in error_messages or "Connection timeout" in error_messages
        assert "DiskFullError" in error_messages or "No space left" in error_messages
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self):
        """Test pausing and resuming a job."""
        # Create and start a job
        mock_results = self._create_mock_search_results(1, 2)
        job_id = await self.bulk_manager.create_bulk_job(mock_results)
        
        # Set job as processing
        job = self.bulk_manager.jobs[job_id]
        job.status = BulkStatus.PROCESSING
        job.download_tasks = {'file1': 'task1', 'file2': 'task2'}
        
        # Test pause
        result = await self.bulk_manager.pause_job(job_id)
        assert result is True
        assert job.status == BulkStatus.PAUSED
        assert self.mock_download_manager.pause_download.call_count == 2
        
        # Test resume
        result = await self.bulk_manager.resume_job(job_id)
        assert result is True
        assert job.status == BulkStatus.PROCESSING
        assert self.mock_download_manager.resume_download.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Test cancelling a job."""
        # Create job
        mock_results = self._create_mock_search_results(1, 2)
        job_id = await self.bulk_manager.create_bulk_job(mock_results)
        
        # Set job as processing
        job = self.bulk_manager.jobs[job_id]
        job.status = BulkStatus.PROCESSING
        job.download_tasks = {'file1': 'task1', 'file2': 'task2'}
        self.bulk_manager.active_jobs.add(job_id)
        
        # Test cancel
        result = self.bulk_manager.cancel_job(job_id)
        assert result is True
        assert job.status == BulkStatus.CANCELLED
        assert job.completed_at is not None
        assert job_id not in self.bulk_manager.active_jobs
        assert self.mock_download_manager.cancel_download.call_count == 2
    
    def test_extract_file_infos(self):
        """Test extracting file information from search results."""
        # Create mock search result with files
        mock_result = Mock()
        mock_result.id = 123
        mock_result.name = "Test Model"
        
        mock_version = Mock()
        mock_version.id = 456
        mock_version.name = "v1.0"
        mock_version.files = [
            {
                'id': 1,
                'name': 'model.safetensors',
                'downloadUrl': 'https://example.com/download/1',
                'sizeKB': 1024,
                'hashes': {'SHA256': 'abc123'}
            },
            {
                'id': 2,
                'name': 'model.ckpt',
                'downloadUrl': 'https://example.com/download/2',
                'sizeKB': 2048,
                'hashes': {'SHA256': 'def456'}
            }
        ]
        
        mock_result.model_versions = [mock_version]
        
        # Extract file infos
        file_infos = self.bulk_manager._extract_file_infos(mock_result)
        
        assert len(file_infos) == 2
        assert file_infos[0].id == 1
        assert file_infos[0].name == 'model.safetensors'
        assert file_infos[0].url == 'https://example.com/download/1'
        assert file_infos[0].size == 1024 * 1024  # KB to bytes
        assert file_infos[0].hash_sha256 == 'abc123'
        assert file_infos[0].metadata['model_id'] == 123
        assert file_infos[0].metadata['model_name'] == "Test Model"
    
    @pytest.mark.asyncio
    async def test_progress_callbacks(self):
        """Test progress callback functionality."""
        callback_data = []
        
        def progress_callback(job_id, data):
            callback_data.append((job_id, data))
        
        # Add callback
        self.bulk_manager.add_progress_callback(progress_callback)
        
        # Trigger progress notification
        self.bulk_manager._notify_progress("test-job", {'progress': 50})
        
        assert len(callback_data) == 1
        assert callback_data[0] == ("test-job", {'progress': 50})
        
        # Remove callback
        self.bulk_manager.remove_progress_callback(progress_callback)
        self.bulk_manager._notify_progress("test-job", {'progress': 100})
        
        assert len(callback_data) == 1  # No new data
    
    @pytest.mark.asyncio
    async def test_completion_callbacks(self):
        """Test completion callback functionality."""
        completed_jobs = []
        
        def completion_callback(job):
            completed_jobs.append(job)
        
        # Add callback
        self.bulk_manager.add_completion_callback(completion_callback)
        
        # Create and complete a job
        mock_results = self._create_mock_search_results(1, 1)
        job_id = await self.bulk_manager.create_bulk_job(mock_results)
        job = self.bulk_manager.jobs[job_id]
        
        # Trigger completion callbacks
        for callback in self.bulk_manager.completion_callbacks:
            callback(job)
        
        assert len(completed_jobs) == 1
        assert completed_jobs[0] == job
    
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting bulk download statistics."""
        # Create some jobs
        mock_results = self._create_mock_search_results(1, 1)
        
        job1_id = await self.bulk_manager.create_bulk_job(mock_results, "Job 1")
        job2_id = await self.bulk_manager.create_bulk_job(mock_results, "Job 2")
        
        # Set different statuses
        self.bulk_manager.jobs[job1_id].status = BulkStatus.PROCESSING
        self.bulk_manager.active_jobs.add(job1_id)
        
        self.bulk_manager.jobs[job2_id].status = BulkStatus.COMPLETED
        self.bulk_manager.stats['completed_jobs'] = 1
        
        # Get statistics
        stats = self.bulk_manager.get_statistics()
        
        assert stats['total_jobs'] == 2
        assert stats['completed_jobs'] == 1
        assert stats['active_jobs'] == 1
        assert stats['queued_jobs'] == 0
    
    @pytest.mark.asyncio
    async def test_export_job_report(self):
        """Test exporting job report."""
        # Create job with some progress
        mock_results = self._create_mock_search_results(1, 2)
        job_id = await self.bulk_manager.create_bulk_job(mock_results, "Test Job")
        
        job = self.bulk_manager.jobs[job_id]
        job.status = BulkStatus.COMPLETED
        job.downloaded_files = 2
        job.started_at = time.time() - 10
        job.completed_at = time.time()
        job.download_tasks = {'file1': 'task1', 'file2': 'task2'}
        
        # Mock task details
        mock_task = Mock()
        mock_task.status = DownloadStatus.COMPLETED
        mock_task.progress_percent = 100
        mock_task.downloaded_bytes = 1024
        mock_task.total_bytes = 1024
        self.mock_download_manager.get_task_status.return_value = mock_task
        
        # Export report
        report = self.bulk_manager.export_job_report(job_id)
        
        assert report['job_id'] == job_id
        assert report['name'] == "Test Job"
        assert report['status'] == "completed"
        assert report['downloaded_files'] == 2
        assert 'task_details' in report
        assert len(report['task_details']) == 2
        assert report['duration'] is not None
        assert report['duration'] >= 10
    
    def _create_mock_search_results(self, num_models: int, files_per_model: int):
        """Create mock search results for testing."""
        results = []
        
        for i in range(num_models):
            mock_result = Mock()
            mock_result.id = i + 1
            mock_result.name = f"Model {i + 1}"
            
            mock_version = Mock()
            mock_version.id = (i + 1) * 100
            mock_version.name = "v1.0"
            mock_version.files = []
            
            for j in range(files_per_model):
                file_data = {
                    'id': (i * files_per_model) + j + 1,
                    'name': f'file_{j + 1}.safetensors',
                    'downloadUrl': f'https://example.com/download/{(i * files_per_model) + j + 1}',
                    'sizeKB': 1024 * (j + 1),
                    'hashes': {'SHA256': f'hash_{(i * files_per_model) + j + 1}'}
                }
                mock_version.files.append(file_data)
            
            mock_result.model_versions = [mock_version]
            results.append(mock_result)
        
        return results


class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('core.bulk.download_manager.BulkDownloadManager')
    @pytest.mark.asyncio
    async def test_create_bulk_download_from_search(self, MockBulkManager):
        """Test creating bulk download from search results."""
        # Mock bulk manager
        mock_instance = Mock()
        mock_instance.create_bulk_job.return_value = "job-123"
        MockBulkManager.return_value = mock_instance
        
        # Create mock search results
        mock_results = [Mock()]
        
        # Call utility function
        job_id = create_bulk_download_from_search(
            search_results=mock_results,
            name="Test Download",
            batch_size=10
        )
        
        assert job_id == "job-123"
        mock_instance.create_bulk_job.assert_called_once()
        call_args = mock_instance.create_bulk_job.call_args
        assert call_args[0][0] == mock_results
        assert call_args[0][1] == "Test Download"
        assert call_args[0][2]['batch_size'] == 10
    
    def test_create_bulk_download_from_ids_not_implemented(self):
        """Test that bulk download from IDs is not implemented."""
        with pytest.raises(NotImplementedError):
            from core.bulk.download_manager import create_bulk_download_from_ids
            create_bulk_download_from_ids([1, 2, 3])


class TestEnums:
    """Test bulk download enums."""
    
    def test_bulk_status_enum(self):
        """Test BulkStatus enum values."""
        assert BulkStatus.PENDING.value == "pending"
        assert BulkStatus.PROCESSING.value == "processing"
        assert BulkStatus.COMPLETED.value == "completed"
        assert BulkStatus.FAILED.value == "failed"
        assert BulkStatus.CANCELLED.value == "cancelled"
        assert BulkStatus.PAUSED.value == "paused"
    
    def test_batch_strategy_enum(self):
        """Test BatchStrategy enum values."""
        assert BatchStrategy.SEQUENTIAL.value == "sequential"
        assert BatchStrategy.PARALLEL.value == "parallel"
        assert BatchStrategy.ADAPTIVE.value == "adaptive"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])