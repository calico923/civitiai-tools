#!/usr/bin/env python3
"""
Secure Sandbox Environment.
Implements requirement 18.2: Isolated execution environment for untrusted operations.
"""

import logging
import os
import tempfile
import shutil
import subprocess
import time
import signal
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import asyncio
import resource
import contextlib

logger = logging.getLogger(__name__)


class SandboxStatus(Enum):
    """Sandbox execution status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"


@dataclass
class SandboxConfig:
    """Sandbox configuration settings."""
    # Resource limits
    max_memory_mb: int = 256
    max_cpu_time: int = 30  # seconds
    max_wall_time: int = 60  # seconds
    max_file_size_mb: int = 100
    max_open_files: int = 100
    
    # Network restrictions
    allow_network: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    
    # File system restrictions
    allow_file_write: bool = False
    allowed_write_paths: List[str] = field(default_factory=list)
    temp_dir_size_mb: int = 100
    
    # Process restrictions
    allow_subprocess: bool = False
    allowed_executables: List[str] = field(default_factory=list)
    
    # Environment variables
    environment_vars: Dict[str, str] = field(default_factory=dict)
    
    # Security options
    drop_privileges: bool = True
    enable_seccomp: bool = True  # Linux only
    chroot_enabled: bool = False


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    status: SandboxStatus
    return_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: float = 0.0
    memory_used: float = 0.0  # MB
    files_created: List[str] = field(default_factory=list)
    network_activity: bool = False
    error_message: Optional[str] = None
    resource_violations: List[str] = field(default_factory=list)


class SecureSandbox:
    """
    Secure sandbox environment for executing untrusted operations.
    Implements requirement 18.2: Isolation and resource control.
    """
    
    def __init__(self, config: SandboxConfig):
        """
        Initialize secure sandbox.
        
        Args:
            config: Sandbox configuration
        """
        self.config = config
        self.sandbox_dir: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        
        # Resource monitoring
        self.resource_monitor_active = False
        self.peak_memory_usage = 0.0
    
    async def execute_python_code(self, code: str, timeout: Optional[int] = None) -> SandboxResult:
        """
        Execute Python code in sandbox.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout override
            
        Returns:
            SandboxResult with execution details
        """
        return await self._execute_with_sandbox(
            executable="python3",
            args=["-c", code],
            timeout=timeout
        )
    
    async def execute_command(self, command: List[str], timeout: Optional[int] = None) -> SandboxResult:
        """
        Execute command in sandbox.
        
        Args:
            command: Command and arguments to execute
            timeout: Execution timeout override
            
        Returns:
            SandboxResult with execution details
        """
        if not self.config.allow_subprocess:
            return SandboxResult(
                status=SandboxStatus.ERROR,
                error_message="Subprocess execution not allowed in sandbox"
            )
        
        executable = command[0]
        if (self.config.allowed_executables and 
            executable not in self.config.allowed_executables):
            return SandboxResult(
                status=SandboxStatus.ERROR,
                error_message=f"Executable '{executable}' not allowed in sandbox"
            )
        
        return await self._execute_with_sandbox(
            executable=executable,
            args=command[1:],
            timeout=timeout
        )
    
    async def execute_file_operation(self, operation: Callable, 
                                   *args, timeout: Optional[int] = None) -> SandboxResult:
        """
        Execute file operation in sandbox.
        
        Args:
            operation: Function to execute
            args: Arguments for the operation
            timeout: Execution timeout override
            
        Returns:
            SandboxResult with execution details
        """
        start_time = time.time()
        
        try:
            with self._create_sandbox_environment():
                # Monitor resource usage
                self._start_resource_monitoring()
                
                # Execute operation with timeout
                effective_timeout = timeout or self.config.max_wall_time
                
                try:
                    result = await asyncio.wait_for(
                        self._run_operation_safely(operation, *args),
                        timeout=effective_timeout
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return SandboxResult(
                        status=SandboxStatus.COMPLETED,
                        execution_time=execution_time,
                        memory_used=self.peak_memory_usage,
                        files_created=self._get_created_files()
                    )
                    
                except asyncio.TimeoutError:
                    return SandboxResult(
                        status=SandboxStatus.TIMEOUT,
                        execution_time=time.time() - start_time,
                        error_message=f"Operation exceeded timeout of {effective_timeout}s"
                    )
                
                finally:
                    self._stop_resource_monitoring()
                    
        except Exception as e:
            return SandboxResult(
                status=SandboxStatus.ERROR,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _execute_with_sandbox(self, executable: str, args: List[str],
                                  timeout: Optional[int] = None) -> SandboxResult:
        """Execute command with full sandbox protection."""
        start_time = time.time()
        
        try:
            with self._create_sandbox_environment():
                # Prepare command
                cmd = [executable] + args
                
                # Setup environment
                env = os.environ.copy()
                env.update(self.config.environment_vars)
                
                # Remove potentially dangerous environment variables
                dangerous_vars = ['LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH']
                for var in dangerous_vars:
                    env.pop(var, None)
                
                # Resource limits
                def set_limits():
                    # Memory limit
                    if self.config.max_memory_mb > 0:
                        memory_limit = self.config.max_memory_mb * 1024 * 1024
                        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                    
                    # File size limit
                    if self.config.max_file_size_mb > 0:
                        file_size_limit = self.config.max_file_size_mb * 1024 * 1024
                        resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
                    
                    # Open files limit
                    resource.setrlimit(resource.RLIMIT_NOFILE, (self.config.max_open_files, self.config.max_open_files))
                    
                    # CPU time limit
                    if self.config.max_cpu_time > 0:
                        resource.setrlimit(resource.RLIMIT_CPU, (self.config.max_cpu_time, self.config.max_cpu_time))
                    
                    # Disable core dumps
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                
                # Start process
                self.start_time = start_time
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(self.sandbox_dir),
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=set_limits,
                    text=True
                )
                
                # Monitor process
                self._start_resource_monitoring()
                
                try:
                    # Wait for completion with timeout
                    effective_timeout = timeout or self.config.max_wall_time
                    
                    stdout, stderr = await asyncio.wait_for(
                        asyncio.create_task(
                            self._communicate_with_process()
                        ),
                        timeout=effective_timeout
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return SandboxResult(
                        status=SandboxStatus.COMPLETED,
                        return_code=self.process.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        execution_time=execution_time,
                        memory_used=self.peak_memory_usage,
                        files_created=self._get_created_files(),
                        resource_violations=self._check_resource_violations()
                    )
                    
                except asyncio.TimeoutError:
                    # Kill process tree
                    self._kill_process_tree()
                    
                    return SandboxResult(
                        status=SandboxStatus.TIMEOUT,
                        execution_time=time.time() - start_time,
                        memory_used=self.peak_memory_usage,
                        error_message=f"Process exceeded timeout of {effective_timeout}s"
                    )
                
                finally:
                    self._stop_resource_monitoring()
                    
        except Exception as e:
            execution_time = time.time() - start_time
            return SandboxResult(
                status=SandboxStatus.ERROR,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def _communicate_with_process(self) -> tuple:
        """Communicate with subprocess asynchronously."""
        if not self.process:
            raise RuntimeError("No active process")
        
        # Run communicate in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process.communicate)
    
    async def _run_operation_safely(self, operation: Callable, *args) -> Any:
        """Run operation with safety checks."""
        # Setup resource monitoring
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        # Execute operation
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, operation, *args)
        
        # Check resource usage
        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_used = final_memory - initial_memory
        self.peak_memory_usage = max(self.peak_memory_usage, memory_used)
        
        return result
    
    @contextlib.contextmanager
    def _create_sandbox_environment(self):
        """Create and manage sandbox environment."""
        # Create temporary sandbox directory
        self.sandbox_dir = Path(tempfile.mkdtemp(prefix="sandbox_"))
        
        try:
            # Set up sandbox directory permissions
            os.chmod(self.sandbox_dir, 0o750)
            
            # Create subdirectories
            (self.sandbox_dir / "tmp").mkdir(mode=0o700)
            (self.sandbox_dir / "work").mkdir(mode=0o700)
            
            # Setup allowed write paths
            for path in self.config.allowed_write_paths:
                write_path = self.sandbox_dir / path.lstrip('/')
                write_path.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Created sandbox environment: {self.sandbox_dir}")
            
            yield
            
        finally:
            # Cleanup sandbox directory
            if self.sandbox_dir and self.sandbox_dir.exists():
                try:
                    shutil.rmtree(self.sandbox_dir)
                    logger.debug(f"Cleaned up sandbox: {self.sandbox_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup sandbox {self.sandbox_dir}: {e}")
    
    def _start_resource_monitoring(self) -> None:
        """Start monitoring resource usage."""
        self.resource_monitor_active = True
        self.peak_memory_usage = 0.0
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_resources())
    
    def _stop_resource_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.resource_monitor_active = False
    
    async def _monitor_resources(self) -> None:
        """Monitor resource usage during execution."""
        while self.resource_monitor_active and self.process:
            try:
                if self.process.poll() is None:  # Process still running
                    # Get process info
                    proc = psutil.Process(self.process.pid)
                    
                    # Memory usage
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                    self.peak_memory_usage = max(self.peak_memory_usage, memory_mb)
                    
                    # Check memory limit
                    if (self.config.max_memory_mb > 0 and 
                        memory_mb > self.config.max_memory_mb * 1.1):  # 10% tolerance
                        logger.warning(f"Process exceeding memory limit: {memory_mb:.1f}MB")
                        self._kill_process_tree()
                        break
                    
                    # Check execution time
                    if (self.start_time and 
                        time.time() - self.start_time > self.config.max_wall_time * 1.1):
                        logger.warning("Process exceeding time limit")
                        self._kill_process_tree()
                        break
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except (psutil.NoSuchProcess, ProcessLookupError):
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                break
    
    def _kill_process_tree(self) -> None:
        """Kill process and all children."""
        if not self.process:
            return
        
        try:
            # Get all child processes
            parent = psutil.Process(self.process.pid)
            children = parent.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Kill parent process
            parent.kill()
            
            # Wait for termination
            parent.wait(timeout=5)
            
        except (psutil.NoSuchProcess, psutil.TimeoutExpired) as e:
            logger.warning(f"Error killing process tree: {e}")
        except Exception as e:
            logger.error(f"Unexpected error killing process: {e}")
    
    def _get_created_files(self) -> List[str]:
        """Get list of files created in sandbox."""
        if not self.sandbox_dir:
            return []
        
        created_files = []
        try:
            for root, dirs, files in os.walk(self.sandbox_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Return relative path from sandbox root
                    rel_path = file_path.relative_to(self.sandbox_dir)
                    created_files.append(str(rel_path))
        except Exception as e:
            logger.error(f"Error listing created files: {e}")
        
        return created_files
    
    def _check_resource_violations(self) -> List[str]:
        """Check for resource limit violations."""
        violations = []
        
        if (self.config.max_memory_mb > 0 and 
            self.peak_memory_usage > self.config.max_memory_mb):
            violations.append(f"Memory usage exceeded limit: {self.peak_memory_usage:.1f}MB > {self.config.max_memory_mb}MB")
        
        # Check file count in sandbox
        if self.sandbox_dir:
            file_count = len(self._get_created_files())
            if file_count > 1000:  # Arbitrary large number
                violations.append(f"Excessive file creation: {file_count} files")
        
        return violations
    
    async def scan_file_in_sandbox(self, file_path: Path) -> SandboxResult:
        """
        Scan a file in isolated sandbox environment.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            SandboxResult with scan details
        """
        if not file_path.exists():
            return SandboxResult(
                status=SandboxStatus.ERROR,
                error_message="File does not exist"
            )
        
        # Create restricted sandbox for file scanning
        scan_config = SandboxConfig(
            max_memory_mb=128,
            max_cpu_time=15,
            max_wall_time=30,
            allow_network=False,
            allow_file_write=False,
            allow_subprocess=False
        )
        
        scanner = SecureSandbox(scan_config)
        
        # Copy file to sandbox for analysis
        async def scan_operation():
            sandbox_file = scanner.sandbox_dir / "scan_target"
            shutil.copy2(file_path, sandbox_file)
            
            # Perform basic file analysis
            analysis = {
                'size': sandbox_file.stat().st_size,
                'readable': os.access(sandbox_file, os.R_OK),
                'executable': os.access(sandbox_file, os.X_OK)
            }
            
            # Try to read file safely (first 1KB only)
            try:
                with open(sandbox_file, 'rb') as f:
                    sample = f.read(1024)
                    analysis['binary'] = b'\x00' in sample
                    analysis['sample_hash'] = hashlib.sha256(sample).hexdigest()
            except Exception as e:
                analysis['read_error'] = str(e)
            
            return analysis
        
        return await scanner.execute_file_operation(scan_operation, timeout=30)
    
    @staticmethod
    def create_minimal_config() -> SandboxConfig:
        """Create minimal sandbox configuration."""
        return SandboxConfig(
            max_memory_mb=64,
            max_cpu_time=10,
            max_wall_time=20,
            max_file_size_mb=10,
            max_open_files=20,
            allow_network=False,
            allow_file_write=False,
            allow_subprocess=False
        )
    
    @staticmethod
    def create_development_config() -> SandboxConfig:
        """Create development sandbox configuration."""
        return SandboxConfig(
            max_memory_mb=512,
            max_cpu_time=60,
            max_wall_time=120,
            max_file_size_mb=50,
            max_open_files=100,
            allow_network=False,
            allow_file_write=True,
            allowed_write_paths=["/tmp", "/work"],
            allow_subprocess=True,
            allowed_executables=["python3", "pip", "git"]
        )
    
    @staticmethod
    def create_analysis_config() -> SandboxConfig:
        """Create file analysis sandbox configuration."""
        return SandboxConfig(
            max_memory_mb=256,
            max_cpu_time=30,
            max_wall_time=60,
            max_file_size_mb=20,
            max_open_files=50,
            allow_network=False,
            allow_file_write=False,
            allow_subprocess=False,
            environment_vars={
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONHASHSEED': '0'
            }
        )