#!/usr/bin/env python3
"""
Bulk Download Manager for CivitAI Downloader.
Manages batch downloads of multiple models with advanced queue management.
"""

import asyncio
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
import json
import threading
from datetime import datetime
import time

try:
    from ...core.download.manager import DownloadManager, DownloadTask, FileInfo, DownloadPriority, DownloadStatus
    from ...core.search.strategy import SearchResult
    from ...core.security.scanner import SecurityScanner, ScanResult
    from ...core.config.system_config import SystemConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.download.manager import DownloadManager, DownloadTask, FileInfo, DownloadPriority, DownloadStatus
    from core.search.strategy import SearchResult
    from core.security.scanner import SecurityScanner, ScanResult
    from core.config.system_config import SystemConfig


class BulkStatus(Enum):
    """Bulk download job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class BatchStrategy(Enum):
    """Batch processing strategies."""
    SEQUENTIAL = "sequential"      # Process batches one by one
    PARALLEL = "parallel"          # Process all batches in parallel
    ADAPTIVE = "adaptive"          # Adjust based on system resources


@dataclass
class BulkDownloadJob:
    """Represents a bulk download job."""
    job_id: str
    name: str
    search_results: List[SearchResult]
    status: BulkStatus = BulkStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_files: int = 0
    downloaded_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_size: int = 0
    downloaded_size: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    download_tasks: Dict[str, str] = field(default_factory=dict)  # file_id -> task_id mapping
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_id': self.job_id,
            'name': self.name,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'total_files': self.total_files,
            'downloaded_files': self.downloaded_files,
            'failed_files': self.failed_files,
            'skipped_files': self.skipped_files,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'errors': self.errors,
            'options': self.options
        }


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 5
    concurrent_batches: int = 2
    strategy: BatchStrategy = BatchStrategy.ADAPTIVE
    auto_retry: bool = True
    max_retries: int = 3
    pause_between_batches: float = 0.0
    priority_boost: bool = True  # Boost priority for bulk downloads


class BulkDownloadManager:
    """Manages bulk downloads with advanced queue management."""
    
    def __init__(self, 
                 download_manager: Optional[DownloadManager] = None,
                 security_scanner: Optional[SecurityScanner] = None,
                 config: Optional[SystemConfig] = None):
        """
        Initialize bulk download manager.
        
        Args:
            download_manager: Download manager instance
            security_scanner: Security scanner instance
            config: System configuration
        """
        self.config = config or SystemConfig()
        self.download_manager = download_manager or DownloadManager(config=self.config)
        self.security_scanner = security_scanner or SecurityScanner(config=self.config)
        
        # Bulk download configuration
        self.batch_config = BatchConfig(
            batch_size=self.config.get('bulk.batch_size', 5),
            concurrent_batches=self.config.get('bulk.concurrent_batches', 2),
            strategy=BatchStrategy(self.config.get('bulk.strategy', 'adaptive')),
            auto_retry=self.config.get('bulk.auto_retry', True),
            max_retries=self.config.get('bulk.max_retries', 3),
            pause_between_batches=self.config.get('bulk.pause_between_batches', 0.0),
            priority_boost=self.config.get('bulk.priority_boost', True)
        )
        
        # Job management
        self.jobs: Dict[str, BulkDownloadJob] = {}
        self.active_jobs: Set[str] = set()
        self.job_queue: List[str] = []
        
        # Statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_files_downloaded': 0,
            'total_bytes_downloaded': 0,
            'total_time': 0.0
        }
        
        # Callbacks
        self.progress_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.completion_callbacks: List[Callable[[BulkDownloadJob], None]] = []
        
        # Thread safety
        self._lock = threading.Lock()
        self._running = False
        self._processor_task = None
    
    def create_bulk_job(self, 
                       search_results: List[SearchResult],
                       name: Optional[str] = None,
                       options: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new bulk download job.
        
        Args:
            search_results: List of search results to download
            name: Optional job name
            options: Job-specific options
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Count total files
        total_files = 0
        total_size = 0
        for result in search_results:
            if hasattr(result, 'model_versions'):
                for version in result.model_versions:
                    if hasattr(version, 'files'):
                        total_files += len(version.files)
                        total_size += sum(f.size for f in version.files if hasattr(f, 'size'))
        
        job = BulkDownloadJob(
            job_id=job_id,
            name=name or f"Bulk Download {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            search_results=search_results,
            total_files=total_files,
            total_size=total_size,
            options=options or {}
        )
        
        with self._lock:
            self.jobs[job_id] = job
            self.job_queue.append(job_id)
            self.stats['total_jobs'] += 1
        
        # Start processor if not running
        if not self._running:
            self.start()
        
        return job_id
    
    def start(self):
        """Start the bulk download processor."""
        if self._running:
            return
        
        self._running = True
        # Only create task if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            self._processor_task = loop.create_task(self._process_jobs())
        except RuntimeError:
            # Not in an event loop, skip automatic start
            pass
    
    async def stop(self):
        """Stop the bulk download processor."""
        self._running = False
        if self._processor_task:
            await self._processor_task
    
    async def _process_jobs(self):
        """Process bulk download jobs."""
        while self._running:
            job_id = self._get_next_job()
            if not job_id:
                await asyncio.sleep(1)
                continue
            
            try:
                await self._process_job(job_id)
            except Exception as e:
                print(f"Error processing job {job_id}: {e}")
                with self._lock:
                    if job_id in self.jobs:
                        self.jobs[job_id].status = BulkStatus.FAILED
                        self.jobs[job_id].errors.append({
                            'error': str(e),
                            'timestamp': time.time()
                        })
    
    def _get_next_job(self) -> Optional[str]:
        """Get next job to process."""
        with self._lock:
            # Check concurrent job limit
            if len(self.active_jobs) >= self.batch_config.concurrent_batches:
                return None
            
            # Get next pending job
            for job_id in self.job_queue:
                if job_id not in self.active_jobs and self.jobs[job_id].status == BulkStatus.PENDING:
                    self.active_jobs.add(job_id)
                    return job_id
        
        return None
    
    async def _process_job(self, job_id: str):
        """Process a single bulk download job."""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        # Update job status
        with self._lock:
            job.status = BulkStatus.PROCESSING
            job.started_at = time.time()
        
        try:
            # Create download tasks
            all_file_infos = []
            for result in job.search_results:
                file_infos = self._extract_file_infos(result)
                all_file_infos.extend(file_infos)
            
            # Process in batches
            batches = [all_file_infos[i:i + self.batch_config.batch_size] 
                      for i in range(0, len(all_file_infos), self.batch_config.batch_size)]
            
            for batch_idx, batch in enumerate(batches):
                if job.status == BulkStatus.CANCELLED:
                    break
                
                await self._process_batch(job, batch, batch_idx, len(batches))
                
                # Pause between batches if configured
                if self.batch_config.pause_between_batches > 0 and batch_idx < len(batches) - 1:
                    await asyncio.sleep(self.batch_config.pause_between_batches)
            
            # Update final status
            with self._lock:
                if job.status != BulkStatus.CANCELLED:
                    job.status = BulkStatus.COMPLETED if job.failed_files == 0 else BulkStatus.FAILED
                job.completed_at = time.time()
                self.stats['completed_jobs'] += 1
                if job.status == BulkStatus.FAILED:
                    self.stats['failed_jobs'] += 1
            
            # Trigger completion callbacks
            for callback in self.completion_callbacks:
                try:
                    callback(job)
                except Exception as e:
                    print(f"Error in completion callback: {e}")
        
        finally:
            with self._lock:
                self.active_jobs.discard(job_id)
    
    async def _process_batch(self, job: BulkDownloadJob, batch: List[FileInfo], 
                           batch_idx: int, total_batches: int):
        """Process a batch of files."""
        batch_tasks = []
        
        for file_info in batch:
            # Create download task with priority boost if enabled
            priority = DownloadPriority.HIGH if self.batch_config.priority_boost else DownloadPriority.NORMAL
            
            task_id = self.download_manager.create_download_task(
                file_info=file_info,
                priority=priority,
                auto_start=False
            )
            
            job.download_tasks[str(file_info.id)] = task_id
            batch_tasks.append(task_id)
        
        # Start all tasks in batch
        download_futures = []
        for task_id in batch_tasks:
            future = self.download_manager.start_download(task_id)
            download_futures.append((task_id, future))
        
        # Wait for batch completion
        for task_id, future in download_futures:
            try:
                success = await future
                task = self.download_manager.get_task_status(task_id)
                
                if success and task:
                    # Perform security scan
                    if task.status == DownloadStatus.COMPLETED and task.final_path:
                        scan_report = self.security_scanner.scan_file(task.final_path)
                        if scan_report.scan_result != ScanResult.SAFE:
                            job.errors.append({
                                'file_id': task.file_info.id,
                                'error': f"Security scan failed: {scan_report.scan_result.value}",
                                'timestamp': time.time()
                            })
                            job.failed_files += 1
                        else:
                            job.downloaded_files += 1
                            job.downloaded_size += task.file_info.size
                    else:
                        job.failed_files += 1
                else:
                    job.failed_files += 1
                    
            except Exception as e:
                job.failed_files += 1
                job.errors.append({
                    'task_id': task_id,
                    'error': str(e),
                    'timestamp': time.time()
                })
        
        # Update progress
        self._notify_progress(job.job_id, {
            'batch': batch_idx + 1,
            'total_batches': total_batches,
            'downloaded_files': job.downloaded_files,
            'failed_files': job.failed_files,
            'total_files': job.total_files
        })
    
    def _extract_file_infos(self, search_result: SearchResult) -> List[FileInfo]:
        """Extract file information from search result."""
        file_infos = []
        
        if hasattr(search_result, 'model_versions'):
            for version in search_result.model_versions:
                if hasattr(version, 'files'):
                    for file_data in version.files:
                        file_info = FileInfo(
                            id=file_data.get('id', 0),
                            name=file_data.get('name', 'unknown'),
                            url=file_data.get('downloadUrl', ''),
                            size=file_data.get('sizeKB', 0) * 1024,
                            hash_sha256=file_data.get('hashes', {}).get('SHA256', '')
                        )
                        # Add metadata separately
                        file_info.metadata = {
                            'model_id': search_result.id,
                            'model_name': search_result.name,
                            'version_id': version.id if hasattr(version, 'id') else None,
                            'version_name': version.name if hasattr(version, 'name') else None
                        }
                        file_infos.append(file_info)
        
        return file_infos
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a bulk download job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job and job.status == BulkStatus.PROCESSING:
                job.status = BulkStatus.PAUSED
                # Pause all associated download tasks
                for task_id in job.download_tasks.values():
                    self.download_manager.pause_download(task_id)
                return True
        return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused bulk download job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job and job.status == BulkStatus.PAUSED:
                job.status = BulkStatus.PROCESSING
                # Resume all associated download tasks
                for task_id in job.download_tasks.values():
                    self.download_manager.resume_download(task_id)
                return True
        return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a bulk download job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job and job.status in [BulkStatus.PENDING, BulkStatus.PROCESSING, BulkStatus.PAUSED]:
                job.status = BulkStatus.CANCELLED
                job.completed_at = time.time()
                # Cancel all associated download tasks
                for task_id in job.download_tasks.values():
                    self.download_manager.cancel_download(task_id)
                self.active_jobs.discard(job_id)
                return True
        return False
    
    def get_job_status(self, job_id: str) -> Optional[BulkDownloadJob]:
        """Get status of a bulk download job."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[BulkDownloadJob]:
        """Get all bulk download jobs."""
        return list(self.jobs.values())
    
    def get_active_jobs(self) -> List[BulkDownloadJob]:
        """Get currently active jobs."""
        with self._lock:
            return [self.jobs[job_id] for job_id in self.active_jobs if job_id in self.jobs]
    
    def add_progress_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add progress callback."""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Remove progress callback."""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def add_completion_callback(self, callback: Callable[[BulkDownloadJob], None]):
        """Add completion callback."""
        self.completion_callbacks.append(callback)
    
    def remove_completion_callback(self, callback: Callable[[BulkDownloadJob], None]):
        """Remove completion callback."""
        if callback in self.completion_callbacks:
            self.completion_callbacks.remove(callback)
    
    def _notify_progress(self, job_id: str, progress_data: Dict[str, Any]):
        """Notify progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(job_id, progress_data)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bulk download statistics."""
        with self._lock:
            stats = self.stats.copy()
            stats['active_jobs'] = len(self.active_jobs)
            stats['queued_jobs'] = len([j for j in self.jobs.values() if j.status == BulkStatus.PENDING])
            return stats
    
    def save_job_state(self, job_id: str, filepath: Path):
        """Save job state to file."""
        job = self.jobs.get(job_id)
        if job:
            state = job.to_dict()
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
    
    def export_job_report(self, job_id: str) -> Dict[str, Any]:
        """Export detailed job report."""
        job = self.jobs.get(job_id)
        if not job:
            return {}
        
        report = job.to_dict()
        
        # Add download task details
        task_details = []
        for file_id, task_id in job.download_tasks.items():
            task = self.download_manager.get_task_status(task_id)
            if task:
                task_details.append({
                    'file_id': file_id,
                    'task_id': task_id,
                    'status': task.status.value,
                    'progress': task.progress_percent,
                    'downloaded_bytes': task.downloaded_bytes,
                    'total_bytes': task.total_bytes
                })
        
        report['task_details'] = task_details
        report['duration'] = job.completed_at - job.started_at if job.completed_at and job.started_at else None
        
        return report


# Utility functions
def create_bulk_download_from_search(search_results: List[SearchResult],
                                   name: Optional[str] = None,
                                   batch_size: int = 5) -> str:
    """
    Create a bulk download job from search results.
    
    Args:
        search_results: Search results to download
        name: Job name
        batch_size: Files per batch
        
    Returns:
        Job ID
    """
    bulk_manager = BulkDownloadManager()
    
    options = {
        'batch_size': batch_size,
        'source': 'search_results'
    }
    
    return bulk_manager.create_bulk_job(search_results, name, options)


def create_bulk_download_from_ids(model_ids: List[int],
                                name: Optional[str] = None) -> str:
    """
    Create a bulk download job from model IDs.
    
    Args:
        model_ids: List of model IDs to download
        name: Job name
        
    Returns:
        Job ID
    """
    # This would require fetching model details first
    # Implementation would use SearchStrategy to get model details
    raise NotImplementedError("Bulk download from IDs requires API integration")


if __name__ == "__main__":
    # Test bulk download manager
    print("Testing Bulk Download Manager...")
    
    # Create mock search results
    from core.search.strategy import SearchResult, ModelType
    
    mock_results = [
        SearchResult(
            id=1,
            name="Test Model 1",
            type=ModelType.CHECKPOINT,
            nsfw=False,
            tags=["test"],
            stats={'downloadCount': 100, 'favoriteCount': 10, 'commentCount': 5, 'rating': 4.5},
            model_versions=[],
            creator={'username': 'test_user', 'image': None}
        )
    ]
    
    # Create bulk download manager
    bulk_manager = BulkDownloadManager()
    
    # Create job
    job_id = bulk_manager.create_bulk_job(mock_results, "Test Bulk Download")
    print(f"Created job: {job_id}")
    
    # Check job status
    job = bulk_manager.get_job_status(job_id)
    print(f"Job status: {job.status.value if job else 'Not found'}")
    
    # Get statistics
    stats = bulk_manager.get_statistics()
    print(f"Statistics: {stats}")
    
    print("Bulk Download Manager test completed.")