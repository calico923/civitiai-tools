#!/usr/bin/env python3
"""
Progress Tracking System.
Implements requirement 19.1: Real-time progress tracking with visual indicators.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import sys
import shutil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProgressLevel(Enum):
    """Progress tracking levels."""
    TASK = "task"           # Individual task progress
    OPERATION = "operation" # Operation-level progress (multiple tasks)
    SYSTEM = "system"      # System-wide progress


@dataclass
class ProgressMetrics:
    """Progress measurement data."""
    current: int = 0
    total: int = 100
    rate: float = 0.0  # items per second
    eta_seconds: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    @property
    def percentage(self) -> float:
        """Get progress as percentage."""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100.0)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def remaining_time(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self.rate <= 0 or self.current >= self.total:
            return None
        remaining_items = self.total - self.current
        return remaining_items / self.rate


@dataclass
class ProgressTask:
    """Individual progress task."""
    task_id: str
    name: str
    level: ProgressLevel
    metrics: ProgressMetrics
    status: str = "running"
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, current: int, total: Optional[int] = None, 
               status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update task progress."""
        current_time = time.time()
        
        if total is not None:
            self.metrics.total = total
        
        # Calculate rate
        if current > self.metrics.current and current_time > self.metrics.last_update:
            delta_items = current - self.metrics.current
            delta_time = current_time - self.metrics.last_update
            self.metrics.rate = delta_items / delta_time
        
        self.metrics.current = current
        self.metrics.last_update = current_time
        
        if status:
            self.status = status
        
        if metadata:
            self.metadata.update(metadata)
    
    def complete(self) -> None:
        """Mark task as completed."""
        self.metrics.current = self.metrics.total
        self.status = "completed"
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = "failed"
        self.metadata['error'] = error


class ProgressTracker:
    """
    Comprehensive progress tracking system.
    Implements requirement 19.1: Multi-level progress tracking.
    """
    
    def __init__(self):
        """Initialize progress tracker."""
        self.tasks: Dict[str, ProgressTask] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()
        
        # Global metrics
        self.start_time = time.time()
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
    
    def create_task(self, task_id: str, name: str, level: ProgressLevel,
                   total: int = 100, parent_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> ProgressTask:
        """
        Create a new progress task.
        
        Args:
            task_id: Unique task identifier
            name: Human-readable task name
            level: Progress level
            total: Total items to process
            parent_id: Parent task ID for hierarchical progress
            metadata: Additional task metadata
            
        Returns:
            Created ProgressTask
        """
        with self.lock:
            if task_id in self.tasks:
                raise ValueError(f"Task already exists: {task_id}")
            
            metrics = ProgressMetrics(total=total)
            task = ProgressTask(
                task_id=task_id,
                name=name,
                level=level,
                metrics=metrics,
                parent_id=parent_id,
                metadata=metadata or {}
            )
            
            self.tasks[task_id] = task
            self.total_tasks += 1
            
            # Add to parent's children
            if parent_id and parent_id in self.tasks:
                self.tasks[parent_id].children.append(task_id)
            
            logger.debug(f"Created progress task: {task_id} - {name}")
            
            # Notify callbacks
            self._notify_callbacks(task_id, "created", task)
            
            return task
    
    def update_task(self, task_id: str, current: int, total: Optional[int] = None,
                   status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update task progress.
        
        Args:
            task_id: Task identifier
            current: Current progress value
            total: Updated total (optional)
            status: Updated status (optional)
            metadata: Additional metadata (optional)
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"Task not found: {task_id}")
                return
            
            task = self.tasks[task_id]
            old_percentage = task.metrics.percentage
            
            task.update(current, total, status, metadata)
            
            # Update parent progress if applicable
            if task.parent_id:
                self._update_parent_progress(task.parent_id)
            
            # Notify callbacks if significant change
            if abs(task.metrics.percentage - old_percentage) >= 1.0:
                self._notify_callbacks(task_id, "updated", task)
    
    def complete_task(self, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark task as completed.
        
        Args:
            task_id: Task identifier
            metadata: Final metadata
        """
        with self.lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            task.complete()
            
            if metadata:
                task.metadata.update(metadata)
            
            self.completed_tasks += 1
            
            # Update parent progress
            if task.parent_id:
                self._update_parent_progress(task.parent_id)
            
            logger.info(f"Task completed: {task_id} - {task.name}")
            
            # Notify callbacks
            self._notify_callbacks(task_id, "completed", task)
    
    def fail_task(self, task_id: str, error: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark task as failed.
        
        Args:
            task_id: Task identifier
            error: Error description
            metadata: Additional metadata
        """
        with self.lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            task.fail(error)
            
            if metadata:
                task.metadata.update(metadata)
            
            self.failed_tasks += 1
            
            logger.error(f"Task failed: {task_id} - {error}")
            
            # Notify callbacks
            self._notify_callbacks(task_id, "failed", task)
    
    def get_task(self, task_id: str) -> Optional[ProgressTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_level(self, level: ProgressLevel) -> List[ProgressTask]:
        """Get all tasks at specific level."""
        return [task for task in self.tasks.values() if task.level == level]
    
    def get_child_tasks(self, parent_id: str) -> List[ProgressTask]:
        """Get child tasks of a parent."""
        parent = self.tasks.get(parent_id)
        if not parent:
            return []
        
        return [self.tasks[child_id] for child_id in parent.children if child_id in self.tasks]
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall system progress."""
        with self.lock:
            active_tasks = [task for task in self.tasks.values() if task.status == "running"]
            
            if not active_tasks:
                overall_percentage = 100.0 if self.total_tasks > 0 else 0.0
            else:
                total_progress = sum(task.metrics.percentage for task in active_tasks)
                overall_percentage = total_progress / len(active_tasks)
            
            return {
                'overall_percentage': overall_percentage,
                'total_tasks': self.total_tasks,
                'completed_tasks': self.completed_tasks,
                'failed_tasks': self.failed_tasks,
                'active_tasks': len(active_tasks),
                'elapsed_time': time.time() - self.start_time
            }
    
    def register_callback(self, task_id: str, callback: Callable) -> None:
        """Register callback for task updates."""
        if task_id not in self.callbacks:
            self.callbacks[task_id] = []
        self.callbacks[task_id].append(callback)
    
    def _update_parent_progress(self, parent_id: str) -> None:
        """Update parent task progress based on children."""
        parent = self.tasks.get(parent_id)
        if not parent or not parent.children:
            return
        
        children = self.get_child_tasks(parent_id)
        if not children:
            return
        
        # Calculate average progress of children
        total_percentage = sum(child.metrics.percentage for child in children)
        avg_percentage = total_percentage / len(children)
        
        # Update parent progress
        new_current = int((avg_percentage / 100.0) * parent.metrics.total)
        parent.metrics.current = new_current
        parent.metrics.last_update = time.time()
    
    def _notify_callbacks(self, task_id: str, event: str, task: ProgressTask) -> None:
        """Notify registered callbacks."""
        callbacks = self.callbacks.get(task_id, [])
        for callback in callbacks:
            try:
                callback(event, task)
            except Exception as e:
                logger.error(f"Callback error for task {task_id}: {e}")
    
    def cleanup_completed_tasks(self, max_age_minutes: int = 60) -> int:
        """Clean up old completed tasks."""
        cutoff_time = time.time() - (max_age_minutes * 60)
        removed_count = 0
        
        with self.lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in ["completed", "failed"] and 
                    task.metrics.last_update < cutoff_time):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                if task_id in self.callbacks:
                    del self.callbacks[task_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.debug(f"Cleaned up {removed_count} old tasks")
        
        return removed_count


class ProgressDisplay:
    """
    Visual progress display system.
    Implements requirement 19.2: Visual progress indicators.
    """
    
    def __init__(self, tracker: ProgressTracker, update_interval: float = 0.1):
        """
        Initialize progress display.
        
        Args:
            tracker: ProgressTracker instance
            update_interval: Display update interval in seconds
        """
        self.tracker = tracker
        self.update_interval = update_interval
        self.terminal_width = shutil.get_terminal_size().columns
        self.display_thread: Optional[threading.Thread] = None
        self.stop_display = threading.Event()
        self.current_display: Dict[str, str] = {}
    
    def start_display(self, task_ids: Optional[List[str]] = None) -> None:
        """
        Start real-time progress display.
        
        Args:
            task_ids: Specific tasks to display, or None for all
        """
        if self.display_thread and self.display_thread.is_alive():
            return
        
        self.stop_display.clear()
        self.display_thread = threading.Thread(
            target=self._display_loop,
            args=(task_ids,),
            daemon=True
        )
        self.display_thread.start()
    
    def stop_display_update(self) -> None:
        """Stop progress display updates."""
        self.stop_display.set()
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
    
    def _display_loop(self, task_ids: Optional[List[str]]) -> None:
        """Main display update loop."""
        while not self.stop_display.wait(self.update_interval):
            try:
                self._update_display(task_ids)
            except Exception as e:
                logger.error(f"Display update error: {e}")
    
    def _update_display(self, task_ids: Optional[List[str]]) -> None:
        """Update progress display."""
        # Determine which tasks to display
        if task_ids:
            tasks = [self.tracker.get_task(tid) for tid in task_ids]
            tasks = [t for t in tasks if t is not None]
        else:
            tasks = [task for task in self.tracker.tasks.values() if task.status == "running"]
        
        if not tasks:
            return
        
        # Clear previous display
        if self.current_display:
            for _ in self.current_display:
                sys.stdout.write('\033[1A\033[2K')  # Move up and clear line
        
        # Generate new display
        display_lines = []
        
        for task in tasks:
            line = self._format_task_line(task)
            display_lines.append(line)
            print(line)
        
        self.current_display = {task.task_id: line for task, line in zip(tasks, display_lines)}
        sys.stdout.flush()
    
    def _format_task_line(self, task: ProgressTask) -> str:
        """Format a single task progress line."""
        # Task name (truncated if needed)
        max_name_length = min(30, self.terminal_width // 3)
        task_name = task.name[:max_name_length].ljust(max_name_length)
        
        # Progress bar
        bar_width = min(40, self.terminal_width // 3)
        filled_width = int((task.metrics.percentage / 100.0) * bar_width)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Percentage and stats
        percentage = f"{task.metrics.percentage:5.1f}%"
        
        # Rate and ETA
        rate_text = ""
        eta_text = ""
        
        if task.metrics.rate > 0:
            if task.metrics.rate >= 1:
                rate_text = f"{task.metrics.rate:.1f}/s"
            else:
                rate_text = f"{task.metrics.rate:.2f}/s"
        
        if task.metrics.remaining_time:
            eta_seconds = int(task.metrics.remaining_time)
            if eta_seconds < 60:
                eta_text = f"{eta_seconds}s"
            elif eta_seconds < 3600:
                eta_text = f"{eta_seconds//60}m{eta_seconds%60}s"
            else:
                hours = eta_seconds // 3600
                minutes = (eta_seconds % 3600) // 60
                eta_text = f"{hours}h{minutes}m"
        
        # Status indicator
        status_indicators = {
            "running": "⚡",
            "completed": "✅", 
            "failed": "❌",
            "paused": "⏸️"
        }
        status_icon = status_indicators.get(task.status, "❓")
        
        # Combine elements
        stats_text = f"{rate_text} {eta_text}".strip()
        
        line = f"{status_icon} {task_name} |{bar}| {percentage} {stats_text}"
        
        # Truncate if too long
        if len(line) > self.terminal_width:
            line = line[:self.terminal_width-3] + "..."
        
        return line
    
    def print_summary(self, task_id: str) -> None:
        """Print task summary."""
        task = self.tracker.get_task(task_id)
        if not task:
            return
        
        elapsed_time = task.metrics.elapsed_time
        
        print(f"\n📊 Task Summary: {task.name}")
        print(f"   Status: {task.status}")
        print(f"   Progress: {task.metrics.current}/{task.metrics.total} ({task.metrics.percentage:.1f}%)")
        print(f"   Elapsed: {self._format_duration(elapsed_time)}")
        
        if task.metrics.rate > 0:
            print(f"   Rate: {task.metrics.rate:.2f} items/second")
        
        if task.metadata:
            print(f"   Details: {task.metadata}")
    
    def print_overall_summary(self) -> None:
        """Print overall progress summary."""
        overall = self.tracker.get_overall_progress()
        
        print(f"\n🌟 Overall Progress Summary")
        print(f"   Progress: {overall['overall_percentage']:.1f}%")
        print(f"   Tasks: {overall['completed_tasks']}/{overall['total_tasks']} completed")
        
        if overall['failed_tasks'] > 0:
            print(f"   Failed: {overall['failed_tasks']} tasks")
        
        print(f"   Active: {overall['active_tasks']} tasks running")
        print(f"   Duration: {self._format_duration(overall['elapsed_time'])}")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def create_simple_progress_bar(current: int, total: int, width: int = 40) -> str:
        """Create a simple progress bar string."""
        if total <= 0:
            return "░" * width
        
        percentage = min(1.0, current / total)
        filled_width = int(percentage * width)
        
        bar = "█" * filled_width + "░" * (width - filled_width)
        return f"|{bar}| {percentage*100:.1f}%"
    
    def create_nested_display(self, root_task_id: str) -> List[str]:
        """Create nested progress display for hierarchical tasks."""
        root_task = self.tracker.get_task(root_task_id)
        if not root_task:
            return []
        
        lines = []
        self._add_nested_task_lines(root_task, lines, 0)
        return lines
    
    def _add_nested_task_lines(self, task: ProgressTask, lines: List[str], indent: int) -> None:
        """Add nested task lines recursively."""
        indent_str = "  " * indent
        
        # Format main task line
        bar = self.create_simple_progress_bar(task.metrics.current, task.metrics.total, 20)
        line = f"{indent_str}{task.name} {bar}"
        lines.append(line)
        
        # Add child tasks
        for child_id in task.children:
            child_task = self.tracker.get_task(child_id)
            if child_task:
                self._add_nested_task_lines(child_task, lines, indent + 1)