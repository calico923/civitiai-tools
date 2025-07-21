#!/usr/bin/env python3
"""
Data Integrity Management.
Implements requirement 17.3: Data integrity verification and recovery.
"""

import logging
import hashlib
import sqlite3
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrityStatus(Enum):
    """Data integrity status levels."""
    VALID = "valid"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    INCONSISTENT = "inconsistent"
    UNKNOWN = "unknown"


@dataclass
class FileIntegrity:
    """File integrity information."""
    file_path: Path
    expected_hash: str
    actual_hash: Optional[str] = None
    hash_algorithm: str = "sha256"
    file_size: Optional[int] = None
    last_verified: Optional[float] = None
    status: IntegrityStatus = IntegrityStatus.UNKNOWN
    
    def verify(self) -> bool:
        """Verify file integrity."""
        if not self.file_path.exists():
            self.status = IntegrityStatus.MISSING
            return False
        
        try:
            # Calculate hash
            hash_obj = hashlib.new(self.hash_algorithm)
            with open(self.file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            
            self.actual_hash = hash_obj.hexdigest()
            self.file_size = self.file_path.stat().st_size
            self.last_verified = time.time()
            
            # Compare hashes
            if self.actual_hash == self.expected_hash:
                self.status = IntegrityStatus.VALID
                return True
            else:
                self.status = IntegrityStatus.CORRUPTED
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify file {self.file_path}: {e}")
            self.status = IntegrityStatus.UNKNOWN
            return False


@dataclass
class DatabaseIntegrity:
    """Database integrity information."""
    db_path: Path
    table_counts: Dict[str, int] = field(default_factory=dict)
    integrity_check_result: Optional[str] = None
    foreign_key_check_result: List[str] = field(default_factory=list)
    last_verified: Optional[float] = None
    status: IntegrityStatus = IntegrityStatus.UNKNOWN
    
    def verify(self) -> bool:
        """Verify database integrity."""
        if not self.db_path.exists():
            self.status = IntegrityStatus.MISSING
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Integrity check
                cursor.execute("PRAGMA integrity_check")
                self.integrity_check_result = cursor.fetchone()[0]
                
                # Foreign key check
                cursor.execute("PRAGMA foreign_key_check")
                self.foreign_key_check_result = [row[0] for row in cursor.fetchall()]
                
                # Get table counts
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                self.table_counts = {}
                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    self.table_counts[table_name] = cursor.fetchone()[0]
                
                self.last_verified = time.time()
                
                # Determine status
                if (self.integrity_check_result == "ok" and 
                    len(self.foreign_key_check_result) == 0):
                    self.status = IntegrityStatus.VALID
                    return True
                else:
                    self.status = IntegrityStatus.CORRUPTED
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to verify database {self.db_path}: {e}")
            self.status = IntegrityStatus.UNKNOWN
            return False


class IntegrityManager:
    """
    Manages data integrity verification and recovery.
    Implements requirement 17.3: Comprehensive integrity management.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize integrity manager.
        
        Args:
            data_dir: Application data directory
        """
        self.data_dir = data_dir
        self.integrity_db = data_dir / "integrity.db"
        
        # File integrity tracking
        self.file_integrity: Dict[str, FileIntegrity] = {}
        
        # Database integrity tracking
        self.db_integrity: Dict[str, DatabaseIntegrity] = {}
        
        # Initialize integrity database
        self._initialize_integrity_db()
    
    def _initialize_integrity_db(self) -> None:
        """Initialize integrity tracking database."""
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                
                # File integrity table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS file_integrity (
                        file_path TEXT PRIMARY KEY,
                        expected_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
                        file_size INTEGER,
                        last_verified REAL,
                        status TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Database integrity table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS database_integrity (
                        db_path TEXT PRIMARY KEY,
                        table_counts TEXT,
                        integrity_result TEXT,
                        foreign_key_result TEXT,
                        last_verified REAL,
                        status TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Integrity log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS integrity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_path TEXT NOT NULL,
                        item_type TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        timestamp REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize integrity database: {e}")
    
    def register_file(self, file_path: Path, expected_hash: str, 
                     hash_algorithm: str = "sha256") -> None:
        """
        Register a file for integrity monitoring.
        
        Args:
            file_path: Path to the file
            expected_hash: Expected hash value
            hash_algorithm: Hash algorithm used
        """
        file_key = str(file_path)
        
        integrity_info = FileIntegrity(
            file_path=file_path,
            expected_hash=expected_hash,
            hash_algorithm=hash_algorithm
        )
        
        self.file_integrity[file_key] = integrity_info
        
        # Store in database
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO file_integrity
                    (file_path, expected_hash, hash_algorithm, status)
                    VALUES (?, ?, ?, ?)
                """, (file_key, expected_hash, hash_algorithm, IntegrityStatus.UNKNOWN.value))
                conn.commit()
                
            logger.debug(f"Registered file for integrity monitoring: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to register file integrity: {e}")
    
    def register_database(self, db_path: Path) -> None:
        """
        Register a database for integrity monitoring.
        
        Args:
            db_path: Path to the database
        """
        db_key = str(db_path)
        
        integrity_info = DatabaseIntegrity(db_path=db_path)
        self.db_integrity[db_key] = integrity_info
        
        # Store in database
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO database_integrity
                    (db_path, status)
                    VALUES (?, ?)
                """, (db_key, IntegrityStatus.UNKNOWN.value))
                conn.commit()
                
            logger.debug(f"Registered database for integrity monitoring: {db_path}")
            
        except Exception as e:
            logger.error(f"Failed to register database integrity: {e}")
    
    async def verify_file_integrity(self, file_path: Optional[Path] = None) -> Dict[str, bool]:
        """
        Verify integrity of files.
        
        Args:
            file_path: Specific file to verify, or None for all files
            
        Returns:
            Dictionary of file paths and their verification results
        """
        results = {}
        
        files_to_check = []
        if file_path:
            file_key = str(file_path)
            if file_key in self.file_integrity:
                files_to_check.append(file_key)
        else:
            files_to_check = list(self.file_integrity.keys())
        
        for file_key in files_to_check:
            integrity_info = self.file_integrity[file_key]
            result = integrity_info.verify()
            results[file_key] = result
            
            # Update database
            try:
                with sqlite3.connect(self.integrity_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE file_integrity
                        SET file_size = ?, last_verified = ?, status = ?
                        WHERE file_path = ?
                    """, (integrity_info.file_size, integrity_info.last_verified, 
                         integrity_info.status.value, file_key))
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Failed to update file integrity status: {e}")
            
            # Log event
            self._log_integrity_event(
                file_key, "file", "verification",
                integrity_info.status.value,
                f"Hash match: {result}" if result else f"Hash mismatch or error"
            )
            
            if not result:
                logger.warning(f"File integrity verification failed: {file_key}")
        
        return results
    
    async def verify_database_integrity(self, db_path: Optional[Path] = None) -> Dict[str, bool]:
        """
        Verify integrity of databases.
        
        Args:
            db_path: Specific database to verify, or None for all databases
            
        Returns:
            Dictionary of database paths and their verification results
        """
        results = {}
        
        dbs_to_check = []
        if db_path:
            db_key = str(db_path)
            if db_key in self.db_integrity:
                dbs_to_check.append(db_key)
        else:
            dbs_to_check = list(self.db_integrity.keys())
        
        for db_key in dbs_to_check:
            integrity_info = self.db_integrity[db_key]
            result = integrity_info.verify()
            results[db_key] = result
            
            # Update database
            try:
                with sqlite3.connect(self.integrity_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE database_integrity
                        SET table_counts = ?, integrity_result = ?, 
                            foreign_key_result = ?, last_verified = ?, status = ?
                        WHERE db_path = ?
                    """, (
                        json.dumps(integrity_info.table_counts),
                        integrity_info.integrity_check_result,
                        json.dumps(integrity_info.foreign_key_check_result),
                        integrity_info.last_verified,
                        integrity_info.status.value,
                        db_key
                    ))
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Failed to update database integrity status: {e}")
            
            # Log event
            self._log_integrity_event(
                db_key, "database", "verification",
                integrity_info.status.value,
                f"Integrity check: {integrity_info.integrity_check_result}"
            )
            
            if not result:
                logger.warning(f"Database integrity verification failed: {db_key}")
        
        return results
    
    def get_integrity_summary(self) -> Dict[str, Any]:
        """Get summary of integrity status."""
        file_summary = {
            "total": len(self.file_integrity),
            "valid": 0,
            "corrupted": 0,
            "missing": 0,
            "unknown": 0
        }
        
        for integrity_info in self.file_integrity.values():
            if integrity_info.status == IntegrityStatus.VALID:
                file_summary["valid"] += 1
            elif integrity_info.status == IntegrityStatus.CORRUPTED:
                file_summary["corrupted"] += 1
            elif integrity_info.status == IntegrityStatus.MISSING:
                file_summary["missing"] += 1
            else:
                file_summary["unknown"] += 1
        
        db_summary = {
            "total": len(self.db_integrity),
            "valid": 0,
            "corrupted": 0,
            "missing": 0,
            "unknown": 0
        }
        
        for integrity_info in self.db_integrity.values():
            if integrity_info.status == IntegrityStatus.VALID:
                db_summary["valid"] += 1
            elif integrity_info.status == IntegrityStatus.CORRUPTED:
                db_summary["corrupted"] += 1
            elif integrity_info.status == IntegrityStatus.MISSING:
                db_summary["missing"] += 1
            else:
                db_summary["unknown"] += 1
        
        return {
            "files": file_summary,
            "databases": db_summary,
            "overall_health": {
                "total_items": len(self.file_integrity) + len(self.db_integrity),
                "healthy_items": file_summary["valid"] + db_summary["valid"],
                "problematic_items": (file_summary["corrupted"] + file_summary["missing"] +
                                    db_summary["corrupted"] + db_summary["missing"])
            }
        }
    
    def get_corrupted_items(self) -> Dict[str, List[str]]:
        """Get list of corrupted items."""
        corrupted = {
            "files": [],
            "databases": []
        }
        
        for file_key, integrity_info in self.file_integrity.items():
            if integrity_info.status in [IntegrityStatus.CORRUPTED, IntegrityStatus.MISSING]:
                corrupted["files"].append(file_key)
        
        for db_key, integrity_info in self.db_integrity.items():
            if integrity_info.status in [IntegrityStatus.CORRUPTED, IntegrityStatus.MISSING]:
                corrupted["databases"].append(db_key)
        
        return corrupted
    
    async def attempt_recovery(self, item_path: str) -> bool:
        """
        Attempt to recover a corrupted item.
        
        Args:
            item_path: Path to the corrupted item
            
        Returns:
            True if recovery successful
        """
        # Check if it's a file
        if item_path in self.file_integrity:
            return await self._recover_file(Path(item_path))
        
        # Check if it's a database
        if item_path in self.db_integrity:
            return await self._recover_database(Path(item_path))
        
        return False
    
    async def _recover_file(self, file_path: Path) -> bool:
        """Attempt to recover a corrupted file."""
        # Look for backup files
        backup_paths = [
            file_path.with_suffix(file_path.suffix + '.backup'),
            file_path.with_suffix(file_path.suffix + '.bak'),
            file_path.parent / f"{file_path.name}.backup"
        ]
        
        for backup_path in backup_paths:
            if backup_path.exists():
                try:
                    # Copy backup to original location
                    import shutil
                    shutil.copy2(backup_path, file_path)
                    
                    # Verify recovery
                    integrity_info = self.file_integrity[str(file_path)]
                    if integrity_info.verify():
                        logger.info(f"Successfully recovered file from backup: {file_path}")
                        self._log_integrity_event(
                            str(file_path), "file", "recovery",
                            "successful", f"Recovered from {backup_path}"
                        )
                        return True
                        
                except Exception as e:
                    logger.error(f"Failed to recover file from {backup_path}: {e}")
        
        # Recovery failed
        self._log_integrity_event(
            str(file_path), "file", "recovery",
            "failed", "No valid backup found"
        )
        return False
    
    async def _recover_database(self, db_path: Path) -> bool:
        """Attempt to recover a corrupted database."""
        # Look for backup database
        backup_paths = [
            db_path.with_suffix(db_path.suffix + '.backup'),
            db_path.with_suffix(db_path.suffix + '.bak')
        ]
        
        for backup_path in backup_paths:
            if backup_path.exists():
                try:
                    import shutil
                    shutil.copy2(backup_path, db_path)
                    
                    # Verify recovery
                    integrity_info = self.db_integrity[str(db_path)]
                    if integrity_info.verify():
                        logger.info(f"Successfully recovered database from backup: {db_path}")
                        self._log_integrity_event(
                            str(db_path), "database", "recovery",
                            "successful", f"Recovered from {backup_path}"
                        )
                        return True
                        
                except Exception as e:
                    logger.error(f"Failed to recover database from {backup_path}: {e}")
        
        # Try SQLite recovery commands
        try:
            temp_db = db_path.with_suffix('.recovered')
            with sqlite3.connect(temp_db) as conn:
                conn.execute(f"ATTACH DATABASE '{db_path}' AS damaged")
                
                # Get table list from damaged database
                cursor = conn.cursor()
                cursor.execute("SELECT sql FROM damaged.sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                # Recreate tables and copy data
                for (create_sql,) in tables:
                    if create_sql:
                        conn.execute(create_sql)
                        
                        # Extract table name
                        table_name = create_sql.split()[2]
                        conn.execute(f"INSERT INTO {table_name} SELECT * FROM damaged.{table_name}")
                
                conn.execute("DETACH DATABASE damaged")
            
            # Replace original with recovered
            import shutil
            shutil.move(temp_db, db_path)
            
            # Verify recovery
            integrity_info = self.db_integrity[str(db_path)]
            if integrity_info.verify():
                logger.info(f"Successfully recovered database using SQLite recovery: {db_path}")
                self._log_integrity_event(
                    str(db_path), "database", "recovery",
                    "successful", "SQLite recovery successful"
                )
                return True
                
        except Exception as e:
            logger.error(f"SQLite recovery failed for {db_path}: {e}")
        
        # Recovery failed
        self._log_integrity_event(
            str(db_path), "database", "recovery",
            "failed", "All recovery methods failed"
        )
        return False
    
    def _log_integrity_event(self, item_path: str, item_type: str, 
                           event_type: str, status: str, message: str) -> None:
        """Log an integrity event."""
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO integrity_log
                    (item_path, item_type, event_type, status, message)
                    VALUES (?, ?, ?, ?, ?)
                """, (item_path, item_type, event_type, status, message))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log integrity event: {e}")
    
    def get_integrity_history(self, item_path: Optional[str] = None, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get integrity event history.
        
        Args:
            item_path: Filter by specific item path
            limit: Maximum number of events to return
            
        Returns:
            List of integrity events
        """
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                
                if item_path:
                    cursor.execute("""
                        SELECT item_path, item_type, event_type, status, message, timestamp
                        FROM integrity_log
                        WHERE item_path = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (item_path, limit))
                else:
                    cursor.execute("""
                        SELECT item_path, item_type, event_type, status, message, timestamp
                        FROM integrity_log
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,))
                
                events = []
                for row in cursor.fetchall():
                    events.append({
                        "item_path": row[0],
                        "item_type": row[1],
                        "event_type": row[2],
                        "status": row[3],
                        "message": row[4],
                        "timestamp": row[5]
                    })
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get integrity history: {e}")
            return []
    
    def cleanup_old_logs(self, max_age_days: int = 30) -> int:
        """
        Clean up old integrity logs.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of logs removed
        """
        cutoff_time = time.time() - (max_age_days * 86400)
        
        try:
            with sqlite3.connect(self.integrity_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM integrity_log
                    WHERE timestamp < ?
                """, (cutoff_time,))
                
                removed_count = cursor.rowcount
                conn.commit()
                
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} old integrity log entries")
                
                return removed_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup integrity logs: {e}")
            return 0