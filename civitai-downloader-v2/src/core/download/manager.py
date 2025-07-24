#!/usr/bin/env python3
"""
Download Manager for CivitAI Downloader.
Provides concurrent downloads with resume capability, progress tracking, and integrity verification.
"""

import os
import asyncio
import aiohttp
import httpx
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import tempfile

try:
    from ...api.auth import AuthManager
    from ...core.config.system_config import SystemConfig
    from ...core.search.strategy import SearchResult
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from api.auth import AuthManager
    from core.config.system_config import SystemConfig
    from core.search.strategy import SearchResult


class DownloadStatus(Enum):
    """Download status states."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadPriority(Enum):
    """Download priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class FileInfo:
    """File information for download."""
    id: int
    name: str
    url: str
    size: int
    hash_sha256: Optional[str] = None
    hash_blake3: Optional[str] = None
    type: str = "unknown"
    scan_result: str = "pending"
    primary: bool = False


@dataclass
class DownloadTask:
    """Download task configuration."""
    id: str
    file_info: FileInfo
    output_path: Path
    model_info: Optional[SearchResult] = None
    priority: DownloadPriority = DownloadPriority.NORMAL
    max_retries: int = 3
    chunk_size: int = 8192 * 1024  # 8MB chunks
    resume: bool = True
    verify_integrity: bool = True
    
    # Runtime state
    status: DownloadStatus = DownloadStatus.PENDING
    downloaded_bytes: int = 0
    total_bytes: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_speed: float = 0.0
    average_speed: float = 0.0
    retry_count: int = 0
    error_message: Optional[str] = None
    temp_path: Optional[Path] = None


@dataclass
class ProgressUpdate:
    """Progress update information."""
    task_id: str
    status: DownloadStatus
    downloaded_bytes: int
    total_bytes: int
    progress_percent: float
    current_speed: float
    eta_seconds: Optional[float]
    error_message: Optional[str] = None


class DownloadManager:
    """Advanced download manager with concurrent downloads and resume capability."""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None, config: Optional[SystemConfig] = None):
        """
        Initialize download manager.
        
        Args:
            auth_manager: Authentication manager
            config: System configuration
        """
        self.auth_manager = auth_manager or AuthManager()
        self.config = config or SystemConfig()
        
        # Configuration - enforce requirement 16.3: max 1 concurrent download
        self.max_concurrent = min(self.config.get('download.concurrent_downloads', 3), 1)
        self.max_concurrent_downloads = self.max_concurrent  # Alias for test compatibility
        self.chunk_size = self.config.get('download.chunk_size', 8192)
        self.default_output_dir = Path(self.config.get('download.paths.models', './downloads/models'))
        self.temp_dir = Path(self.config.get('download.paths.temp', './downloads/temp'))
        
        # Retry configuration for integration test compatibility
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Ensure directories exist
        self.default_output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Task management
        self.tasks: Dict[str, DownloadTask] = {}
        self.active_downloads: Dict[str, asyncio.Task] = {}
        self.download_queue: List[str] = []
        self.completed_tasks: List[str] = []
        
        # Progress tracking
        self.progress_callbacks: List[Callable[[ProgressUpdate], None]] = []
        self.progress_callback = None  # Single callback for test compatibility
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'average_speed': 0.0
        }
        
        # Thread safety
        self._lock = threading.Lock()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=None, connect=30)
            connector = aiohttp.TCPConnector(limit=self.max_concurrent * 2)
            headers = self.auth_manager.get_auth_headers()
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
        
        return self._session
    
    def create_download_task(self, file_info: FileInfo, output_path: Optional[Path] = None,
                           model_info: Optional[SearchResult] = None,
                           priority: DownloadPriority = DownloadPriority.NORMAL) -> str:
        """
        Create a download task.
        
        Args:
            file_info: File information for download
            output_path: Output file path (defaults to default directory)
            model_info: Associated model information
            priority: Download priority
            
        Returns:
            Task ID
        """
        import uuid
        task_id = f"download_{file_info.id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        if output_path is None:
            # Create safe filename
            safe_filename = self._sanitize_filename(file_info.name)
            output_path = self.default_output_dir / safe_filename
        
        # Create temp path
        temp_filename = f"{task_id}.tmp"
        temp_path = self.temp_dir / temp_filename
        
        task = DownloadTask(
            id=task_id,
            file_info=file_info,
            output_path=output_path,
            model_info=model_info,
            priority=priority,
            total_bytes=file_info.size,
            temp_path=temp_path
        )
        
        with self._lock:
            self.tasks[task_id] = task
            self.download_queue.append(task_id)
            # Sort queue by priority
            self.download_queue.sort(
                key=lambda tid: self.tasks[tid].priority.value,
                reverse=True
            )
        
        return task_id
    
    async def start_download(self, task_id: str) -> bool:
        """
        Start a download task.
        
        Args:
            task_id: Task ID to start
            
        Returns:
            True if started successfully
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Check if already downloading
        if task_id in self.active_downloads:
            return False
        
        # Check concurrent limit
        if len(self.active_downloads) >= self.max_concurrent:
            return False
        
        # Start download
        download_coroutine = self._download_file(task)
        download_task = asyncio.create_task(download_coroutine)
        
        self.active_downloads[task_id] = download_task
        task.status = DownloadStatus.DOWNLOADING
        task.start_time = time.time()
        
        # Notify progress
        self._notify_progress(task)
        
        return True
    
    async def _download_file(self, task: DownloadTask) -> None:
        """
        Download a file with resume capability.
        
        Args:
            task: Download task
        """
        try:
            session = await self._get_session()
            
            # Check if partial file exists for resume
            resume_position = 0
            if task.resume and task.temp_path.exists():
                resume_position = task.temp_path.stat().st_size
                task.downloaded_bytes = resume_position
            
            # Setup headers for resume
            headers = {}
            if resume_position > 0:
                headers['Range'] = f'bytes={resume_position}-'
            
            async with session.get(task.file_info.url, headers=headers) as response:
                if response.status not in [200, 206]:  # 206 is partial content
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                # Update total size if not resuming
                if resume_position == 0:
                    content_length = response.headers.get('content-length')
                    if content_length:
                        task.total_bytes = int(content_length)
                
                # Open file for writing
                mode = 'ab' if resume_position > 0 else 'wb'
                
                with open(task.temp_path, mode) as f:
                    start_time = time.time()
                    speed_samples = []
                    
                    async for chunk in response.content.iter_chunked(task.chunk_size):
                        if task.status == DownloadStatus.CANCELLED:
                            break
                        
                        if task.status == DownloadStatus.PAUSED:
                            await asyncio.sleep(0.1)
                            continue
                        
                        # Write chunk
                        f.write(chunk)
                        task.downloaded_bytes += len(chunk)
                        
                        # Calculate speed
                        current_time = time.time()
                        elapsed = current_time - start_time
                        
                        if elapsed > 0:
                            current_speed = len(chunk) / elapsed
                            task.current_speed = current_speed
                            
                            # Keep speed samples for average
                            speed_samples.append(current_speed)
                            if len(speed_samples) > 10:
                                speed_samples.pop(0)
                            
                            task.average_speed = sum(speed_samples) / len(speed_samples)
                        
                        start_time = current_time
                        
                        # Notify progress
                        self._notify_progress(task)
                        
                        # Small delay to prevent overwhelming
                        await asyncio.sleep(0.001)
            
            # Download completed
            if task.status != DownloadStatus.CANCELLED:
                await self._finalize_download(task)
            
        except Exception as e:
            await self._handle_download_error(task, str(e))
        
        finally:
            # Clean up
            if task.id in self.active_downloads:
                del self.active_downloads[task.id]
    
    async def _finalize_download(self, task: DownloadTask) -> None:
        """
        Finalize download (verify integrity and move to final location).
        
        Args:
            task: Download task
        """
        try:
            # Verify file integrity if hash provided
            if task.verify_integrity and task.file_info.hash_sha256:
                if not await self._verify_file_integrity(task):
                    raise Exception("File integrity verification failed")
            
            # Move from temp to final location
            if task.output_path.exists():
                # Handle duplicate files
                task.output_path = self._generate_unique_path(task.output_path)
            
            task.temp_path.rename(task.output_path)
            
            # Update task status
            task.status = DownloadStatus.COMPLETED
            task.end_time = time.time()
            
            # Update statistics
            with self._lock:
                self.stats['successful_downloads'] += 1
                self.stats['total_bytes_downloaded'] += task.downloaded_bytes
                self.completed_tasks.append(task.id)
            
            # Notify completion
            self._notify_progress(task)
            
        except Exception as e:
            await self._handle_download_error(task, f"Finalization failed: {e}")
    
    async def _verify_file_integrity(self, task: DownloadTask) -> bool:
        """
        Verify file integrity using hash.
        
        Args:
            task: Download task
            
        Returns:
            True if verification passed
        """
        try:
            hash_sha256 = hashlib.sha256()
            
            with open(task.temp_path, 'rb') as f:
                while chunk := f.read(task.chunk_size):
                    hash_sha256.update(chunk)
            
            calculated_hash = hash_sha256.hexdigest().lower()
            expected_hash = task.file_info.hash_sha256.lower()
            
            return calculated_hash == expected_hash
            
        except Exception as e:
            print(f"Hash verification error: {e}")
            return False
    
    async def _handle_download_error(self, task: DownloadTask, error: str) -> None:
        """
        Handle download errors with retry logic.
        
        Args:
            task: Download task
            error: Error message
        """
        task.retry_count += 1
        task.error_message = error
        
        if task.retry_count < task.max_retries:
            # Retry after delay
            await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
            
            # Restart download
            download_coroutine = self._download_file(task)
            download_task = asyncio.create_task(download_coroutine)
            self.active_downloads[task.id] = download_task
            
        else:
            # Max retries reached
            task.status = DownloadStatus.FAILED
            task.end_time = time.time()
            
            # Clean up temp file
            if task.temp_path and task.temp_path.exists():
                task.temp_path.unlink()
            
            # Update statistics
            with self._lock:
                self.stats['failed_downloads'] += 1
            
            # Notify failure
            self._notify_progress(task)
    
    def _notify_progress(self, task: DownloadTask) -> None:
        """Notify progress callbacks."""
        progress_percent = 0.0
        if task.total_bytes > 0:
            progress_percent = (task.downloaded_bytes / task.total_bytes) * 100
        
        eta_seconds = None
        if task.average_speed > 0 and task.total_bytes > 0:
            remaining_bytes = task.total_bytes - task.downloaded_bytes
            eta_seconds = remaining_bytes / task.average_speed
        
        update = ProgressUpdate(
            task_id=task.id,
            status=task.status,
            downloaded_bytes=task.downloaded_bytes,
            total_bytes=task.total_bytes,
            progress_percent=progress_percent,
            current_speed=task.current_speed,
            eta_seconds=eta_seconds,
            error_message=task.error_message
        )
        
        for callback in self.progress_callbacks:
            try:
                callback(update)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    def add_progress_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Add progress callback."""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Remove progress callback."""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    async def pause_download(self, task_id: str) -> bool:
        """Pause a download task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == DownloadStatus.DOWNLOADING:
                task.status = DownloadStatus.PAUSED
                self._notify_progress(task)
                return True
        return False
    
    async def resume_download(self, task_id: str) -> bool:
        """Resume a paused download task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == DownloadStatus.PAUSED:
                task.status = DownloadStatus.DOWNLOADING
                self._notify_progress(task)
                return True
        return False
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel a download task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = DownloadStatus.CANCELLED
            
            # Cancel async task
            if task_id in self.active_downloads:
                self.active_downloads[task_id].cancel()
                del self.active_downloads[task_id]
            
            # Clean up temp file
            if task.temp_path and task.temp_path.exists():
                task.temp_path.unlink()
            
            self._notify_progress(task)
            return True
        return False
    
    async def process_download_queue(self) -> None:
        """Process download queue with concurrent limit."""
        while self.download_queue:
            # Start downloads up to concurrent limit
            while (len(self.active_downloads) < self.max_concurrent and 
                   self.download_queue):
                task_id = self.download_queue.pop(0)
                if task_id in self.tasks:
                    await self.start_download(task_id)
            
            # Wait for some downloads to complete
            if self.active_downloads:
                await asyncio.sleep(0.1)
            else:
                break
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get task status."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def get_active_downloads(self) -> List[DownloadTask]:
        """Get currently active downloads."""
        return [self.tasks[tid] for tid in self.active_downloads.keys()]
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics."""
        return self.stats.copy()
    
    async def download_file(self, url: str, filename: str = None, output_dir: str = None, **kwargs) -> 'DownloadResult':
        """
        Download a file from URL - simplified interface for integration tests.
        
        Args:
            url: Download URL
            filename: Output filename (optional)
            output_dir: Output directory (optional)
            **kwargs: Additional arguments (for compatibility)
            
        Returns:
            DownloadResult object with success attribute
        """
        from dataclasses import dataclass
        from pathlib import Path
        
        @dataclass 
        class DownloadResult:
            success: bool
            file_path: Path = None
            error_message: str = ""
        
        try:
            # Simple download implementation for integration test compatibility
            base_dir = Path(output_dir) if output_dir else self.default_output_dir
            if filename:
                output_path = base_dir / filename
            else:
                # Extract filename from URL
                filename = url.split('/')[-1] or "downloaded_file"
                output_path = base_dir / filename
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Perform actual HTTP download
            try:
                # Add API key to download URL if it's a CivitAI download endpoint
                download_url = url
                if 'civitai.com/api/download' in url:
                    from ..config.env_loader import get_civitai_api_key
                    api_key = get_civitai_api_key()
                    if api_key:
                        separator = '&' if '?' in url else '?'
                        download_url = f"{url}{separator}token={api_key}"
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(download_url, follow_redirects=True)
                    response.raise_for_status()
                    
                    # Write content to file
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    return DownloadResult(success=True, file_path=output_path)
                    
            except httpx.RequestError as e:
                return DownloadResult(success=False, error_message=f"Network error: {str(e)}")
            except httpx.HTTPStatusError as e:
                return DownloadResult(success=False, error_message=f"HTTP error {e.response.status_code}: {e.response.text}")
            except OSError as e:
                return DownloadResult(success=False, error_message=f"File write error: {str(e)}")
            
        except Exception as e:
            return DownloadResult(success=False, error_message=str(e))
    
    async def download_file_with_retry(self, url: str, filename: str = None, **kwargs):
        """
        Download a file with retry logic - interface for integration tests.
        
        Args:
            url: Download URL
            filename: Output filename (optional)
            **kwargs: Additional arguments
            
        Returns:
            Result object with success attribute
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await self.download_file(url, filename, **kwargs)
                if result.success:
                    return result
                else:
                    last_exception = Exception(result.error_message)
                    
            except Exception as e:
                last_exception = e
                
            # If not the last attempt, wait before retrying
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)
        
        # All retries exhausted, return failure
        from dataclasses import dataclass
        from pathlib import Path
        
        @dataclass 
        class DownloadResult:
            success: bool
            file_path: Path = None
            error_message: str = ""
        
        return DownloadResult(
            success=False, 
            error_message=f"Download failed after {self.max_retries} retries: {last_exception}"
        )
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage."""
        # Remove/replace dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_() "
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Limit length
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:200-len(ext)] + ext
        
        return sanitized
    
    def _generate_unique_path(self, path: Path) -> Path:
        """Generate unique path if file already exists."""
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def prioritize_safetensors(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        Prioritize SafeTensors files over other formats per requirement 3.1.
        
        Args:
            files: List of available files
            
        Returns:
            Files sorted with SafeTensors first
        """
        safetensors_files = []
        other_files = []
        
        for file_info in files:
            if file_info.name.lower().endswith('.safetensors'):
                safetensors_files.append(file_info)
            else:
                other_files.append(file_info)
        
        # Return SafeTensors files first, then others
        return safetensors_files + other_files
    
    async def close(self) -> None:
        """Close download manager and cleanup resources."""
        # Cancel all active downloads
        for task_id in list(self.active_downloads.keys()):
            await self.cancel_download(task_id)
        
        # Close session
        if self._session and not self._session.closed:
            await self._session.close()


# Utility functions for easy download operations

async def download_model_file(file_info: FileInfo, output_path: Optional[Path] = None,
                            progress_callback: Optional[Callable[[ProgressUpdate], None]] = None) -> str:
    """
    Download a single model file.
    
    Args:
        file_info: File information
        output_path: Output path
        progress_callback: Progress callback function
        
    Returns:
        Task ID
    """
    manager = DownloadManager()
    
    if progress_callback:
        manager.add_progress_callback(progress_callback)
    
    task_id = manager.create_download_task(file_info, output_path)
    await manager.start_download(task_id)
    await manager.process_download_queue()
    
    return task_id


def create_file_info_from_api(file_data: Dict[str, Any]) -> FileInfo:
    """
    Create FileInfo from CivitAI API file data.
    
    Args:
        file_data: File data from API
        
    Returns:
        FileInfo object
    """
    return FileInfo(
        id=file_data['id'],
        name=file_data['name'],
        url=file_data['downloadUrl'],
        size=file_data.get('sizeKB', 0) * 1024,  # Convert KB to bytes
        hash_sha256=file_data.get('hashes', {}).get('SHA256'),
        hash_blake3=file_data.get('hashes', {}).get('BLAKE3'),
        type=file_data.get('type', 'unknown'),
        scan_result=file_data.get('virusScanResult', 'pending'),
        primary=file_data.get('primary', False)
    )


if __name__ == "__main__":
    # Test download manager
    async def test_download_manager():
        print("Testing Download Manager...")
        
        # Create manager
        manager = DownloadManager()
        
        # Add progress callback
        def progress_callback(update: ProgressUpdate):
            print(f"Task {update.task_id}: {update.status.value} - "
                  f"{update.progress_percent:.1f}% - "
                  f"{update.current_speed/1024:.1f} KB/s")
        
        manager.add_progress_callback(progress_callback)
        
        print("Download Manager initialized successfully")
        
        # Test file info creation (mock data)
        file_info = FileInfo(
            id=12345,
            name="test_model.safetensors",
            url="https://example.com/test.safetensors",
            size=1024*1024,  # 1MB
            hash_sha256="dummy_hash"
        )
        
        task_id = manager.create_download_task(file_info)
        print(f"Created download task: {task_id}")
        
        # Show task status
        task = manager.get_task_status(task_id)
        print(f"Task status: {task.status.value}")
        
        stats = manager.get_download_stats()
        print(f"Download stats: {stats}")
        
        await manager.close()
    
    # Run test
    import asyncio
    asyncio.run(test_download_manager())