"""File download manager with progress tracking and resume support."""

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import aiohttp
import aiofiles
from tqdm.asyncio import tqdm

from .interfaces import IDownloadManager, ModelVersion, ModelFile, DownloadProgress
from .config import ConfigManager


class DownloadManager(IDownloadManager):
    """File download manager with progress tracking and resume support."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_downloads: Dict[str, bool] = {}
        self.download_stats: Dict[str, Dict[str, Any]] = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=self.config.config.max_concurrent_downloads,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(
            total=None,  # No total timeout for large downloads
            connect=30,
            sock_read=60
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.config.config.user_agent,
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def can_resume(self, path: Path) -> bool:
        """Check if download can be resumed."""
        return path.exists() and path.stat().st_size > 0
    
    async def _get_file_size(self, url: str) -> Optional[int]:
        """Get remote file size."""
        try:
            response = await self.session.head(url)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            if content_length:
                return int(content_length)
            
            # Check if server supports range requests
            accept_ranges = response.headers.get('Accept-Ranges', '').lower()
            if 'bytes' not in accept_ranges:
                return None
                
        except Exception:
            pass
        return None
    
    async def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """Verify file integrity using hash."""
        if not expected_hash:
            return True  # No hash to verify
        
        try:
            hash_algo = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(8192):
                    hash_algo.update(chunk)
            
            calculated_hash = hash_algo.hexdigest()
            return calculated_hash.lower() == expected_hash.lower()
        except Exception:
            return False
    
    async def download_file(
        self,
        url: str,
        path: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        expected_hash: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> None:
        """Download file with progress tracking and resume support."""
        if not self.session:
            raise RuntimeError("Download manager not initialized. Use 'async with' context.")
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate unique key for this download
        download_key = f"{url}::{path}"
        if download_key in self.active_downloads:
            raise RuntimeError(f"Download already in progress: {path}")
        
        self.active_downloads[download_key] = True
        
        try:
            # Check if file already exists and is valid
            if path.exists() and expected_hash:
                if await self._verify_file_hash(path, expected_hash):
                    # File is valid, no need to download
                    if progress_callback:
                        file_size = path.stat().st_size
                        progress = DownloadProgress(
                            file_name=file_name or path.name,
                            total_bytes=file_size,
                            downloaded_bytes=file_size,
                            percent=100.0,
                            speed_mbps=0.0,
                            eta_seconds=0.0
                        )
                        progress_callback(progress)
                    return
            
            # Get file size for progress tracking
            total_size = await self._get_file_size(url)
            
            # Check for existing partial download
            resume_pos = 0
            if self.can_resume(path) and total_size:
                existing_size = path.stat().st_size
                if existing_size < total_size:
                    resume_pos = existing_size
            
            # Set up headers for range request if resuming
            headers = {}
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
            
            # Download file
            start_time = time.time()
            downloaded_bytes = resume_pos
            
            async with self.session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                # Update total size if we got it from response
                if not total_size:
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        total_size = int(content_length) + resume_pos
                
                # Open file for writing (append mode if resuming)
                mode = 'ab' if resume_pos > 0 else 'wb'
                
                async with aiofiles.open(path, mode) as f:
                    last_progress_time = start_time
                    
                    async for chunk in response.content.iter_chunked(8192):
                        if not self.active_downloads.get(download_key, False):
                            # Download was cancelled
                            break
                        
                        await f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # Update progress
                        current_time = time.time()
                        if progress_callback and (current_time - last_progress_time >= 0.1):  # Update every 100ms
                            elapsed_time = current_time - start_time
                            
                            # Calculate speed
                            speed_mbps = 0.0
                            if elapsed_time > 0:
                                speed_bytes_per_sec = (downloaded_bytes - resume_pos) / elapsed_time
                                speed_mbps = speed_bytes_per_sec / (1024 * 1024)
                            
                            # Calculate ETA
                            eta_seconds = None
                            if total_size and speed_mbps > 0:
                                remaining_bytes = total_size - downloaded_bytes
                                eta_seconds = remaining_bytes / (speed_mbps * 1024 * 1024)
                            
                            # Calculate percentage
                            percent = 0.0
                            if total_size:
                                percent = (downloaded_bytes / total_size) * 100
                            
                            progress = DownloadProgress(
                                file_name=file_name or path.name,
                                total_bytes=total_size or downloaded_bytes,
                                downloaded_bytes=downloaded_bytes,
                                percent=percent,
                                speed_mbps=speed_mbps,
                                eta_seconds=eta_seconds
                            )
                            
                            progress_callback(progress)
                            last_progress_time = current_time
            
            # Verify file integrity if hash provided
            if expected_hash:
                if not await self._verify_file_hash(path, expected_hash):
                    # Hash mismatch, remove file and raise error
                    path.unlink(missing_ok=True)
                    raise RuntimeError(f"File integrity check failed: {path}")
            
            # Final progress update
            if progress_callback:
                final_size = path.stat().st_size
                progress = DownloadProgress(
                    file_name=file_name or path.name,
                    total_bytes=final_size,
                    downloaded_bytes=final_size,
                    percent=100.0,
                    speed_mbps=0.0,
                    eta_seconds=0.0
                )
                progress_callback(progress)
        
        finally:
            # Clean up
            self.active_downloads.pop(download_key, None)
    
    async def download_model(
        self,
        version: ModelVersion,
        path: Path,
        file_index: int = 0,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> None:
        """Download model files with progress tracking."""
        if not version.files:
            raise ValueError("No files available for download")
        
        if file_index >= len(version.files):
            raise ValueError(f"File index {file_index} out of range (0-{len(version.files)-1})")
        
        file_to_download = version.files[file_index]
        
        # Create model directory structure
        model_dir = path / f"model_{version.model_id}" / f"version_{version.id}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Download file
        file_path = model_dir / file_to_download.name
        
        await self.download_file(
            url=file_to_download.download_url,
            path=file_path,
            progress_callback=progress_callback,
            expected_hash=file_to_download.hash,
            file_name=file_to_download.name
        )
        
        # Store download stats
        self.download_stats[str(file_path)] = {
            'model_id': version.model_id,
            'version_id': version.id,
            'file_id': file_to_download.id,
            'file_name': file_to_download.name,
            'file_size': file_to_download.size_bytes,
            'downloaded_at': time.time(),
            'hash': file_to_download.hash
        }
    
    async def download_all_model_files(
        self,
        version: ModelVersion,
        path: Path,
        progress_callback: Optional[Callable[[str, DownloadProgress], None]] = None
    ) -> None:
        """Download all files for a model version."""
        if not version.files:
            raise ValueError("No files available for download")
        
        # Create model directory structure
        model_dir = path / f"model_{version.model_id}" / f"version_{version.id}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Download each file
        for i, file_info in enumerate(version.files):
            file_path = model_dir / file_info.name
            
            # Create progress callback for this specific file
            def file_progress_callback(progress: DownloadProgress) -> None:
                if progress_callback:
                    progress_callback(f"File {i+1}/{len(version.files)}", progress)
            
            await self.download_file(
                url=file_info.download_url,
                path=file_path,
                progress_callback=file_progress_callback,
                expected_hash=file_info.hash,
                file_name=file_info.name
            )
    
    def cancel_download(self, path: Path) -> None:
        """Cancel an active download."""
        # Find and cancel the download
        for download_key in list(self.active_downloads.keys()):
            if str(path) in download_key:
                self.active_downloads[download_key] = False
                break
    
    def get_active_downloads(self) -> Dict[str, bool]:
        """Get list of active downloads."""
        return dict(self.active_downloads)
    
    def get_download_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get download statistics."""
        return dict(self.download_stats)


class ProgressDisplay:
    """Helper class for displaying download progress."""
    
    def __init__(self, show_speed: bool = True, show_eta: bool = True):
        self.show_speed = show_speed
        self.show_eta = show_eta
        self.progress_bars: Dict[str, tqdm] = {}
    
    def create_progress_bar(self, file_name: str, total_bytes: int) -> tqdm:
        """Create a progress bar for a file download."""
        if file_name in self.progress_bars:
            self.progress_bars[file_name].close()
        
        self.progress_bars[file_name] = tqdm(
            total=total_bytes,
            unit='B',
            unit_scale=True,
            desc=file_name,
            dynamic_ncols=True
        )
        
        return self.progress_bars[file_name]
    
    def update_progress(self, progress: DownloadProgress) -> None:
        """Update progress bar."""
        if progress.file_name not in self.progress_bars:
            self.create_progress_bar(progress.file_name, progress.total_bytes)
        
        pbar = self.progress_bars[progress.file_name]
        pbar.n = progress.downloaded_bytes
        pbar.total = progress.total_bytes
        
        # Update description with additional info
        desc_parts = [progress.file_name]
        
        if self.show_speed and progress.speed_mbps > 0:
            desc_parts.append(f"{progress.speed_mbps:.1f} MB/s")
        
        if self.show_eta and progress.eta_seconds:
            eta_str = self._format_eta(progress.eta_seconds)
            desc_parts.append(f"ETA: {eta_str}")
        
        pbar.set_description(" | ".join(desc_parts))
        pbar.refresh()
    
    def _format_eta(self, seconds: float) -> str:
        """Format ETA in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def close_progress_bar(self, file_name: str) -> None:
        """Close and clean up progress bar."""
        if file_name in self.progress_bars:
            self.progress_bars[file_name].close()
            del self.progress_bars[file_name]
    
    def close_all(self) -> None:
        """Close all progress bars."""
        for pbar in self.progress_bars.values():
            pbar.close()
        self.progress_bars.clear()


class BatchDownloadManager:
    """Manager for batch downloading multiple files."""
    
    def __init__(self, download_manager: DownloadManager, max_concurrent: int = 3):
        self.download_manager = download_manager
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.progress_display = ProgressDisplay()
    
    async def download_multiple_models(
        self,
        versions: list[ModelVersion],
        base_path: Path,
        progress_callback: Optional[Callable[[str, DownloadProgress], None]] = None
    ) -> None:
        """Download multiple model versions concurrently."""
        async def download_single_model(version: ModelVersion) -> None:
            async with self.semaphore:
                await self.download_manager.download_all_model_files(
                    version=version,
                    path=base_path,
                    progress_callback=progress_callback
                )
        
        # Create download tasks
        tasks = [download_single_model(version) for version in versions]
        
        # Execute downloads
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.progress_display.close_all()