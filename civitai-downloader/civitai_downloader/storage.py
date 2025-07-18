"""Local storage and metadata management system."""

import json
import sqlite3
import shutil
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
import asyncio
from dataclasses import asdict

from .interfaces import IStorageManager, ModelInfo, ModelVersion, ModelFile, ModelImage
from .config import ConfigManager
from .utils import sanitize_filename, get_app_data_dir, format_file_size


class StorageManager(IStorageManager):
    """Local storage and metadata management system."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.base_path = Path(config.config.download_path)
        self.metadata_db_path = self.base_path / "metadata.db"
        self.history_db_path = self.base_path / "download_history.db"
        
        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize databases
        self._init_databases()
    
    def _init_databases(self):
        """Initialize SQLite databases for metadata and history."""
        # Initialize metadata database
        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,  -- JSON array
                    creator TEXT,
                    stats TEXT,  -- JSON object
                    nsfw BOOLEAN,
                    created_at TEXT,
                    updated_at TEXT,
                    local_path TEXT,
                    downloaded_at TEXT,
                    file_size INTEGER,
                    file_hash TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY,
                    model_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    base_model TEXT,
                    trained_words TEXT,  -- JSON array
                    download_url TEXT,
                    created_at TEXT,
                    local_path TEXT,
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (model_id) REFERENCES models (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS model_files (
                    id INTEGER PRIMARY KEY,
                    version_id INTEGER,
                    name TEXT NOT NULL,
                    size_bytes INTEGER,
                    format TEXT,
                    fp TEXT,
                    hash TEXT,
                    download_url TEXT,
                    metadata TEXT,  -- JSON object
                    local_path TEXT,
                    downloaded_at TEXT,
                    verified BOOLEAN DEFAULT 0,
                    FOREIGN KEY (version_id) REFERENCES model_versions (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS model_images (
                    id INTEGER PRIMARY KEY,
                    version_id INTEGER,
                    url TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    hash TEXT,
                    nsfw BOOLEAN,
                    meta TEXT,  -- JSON object
                    local_path TEXT,
                    downloaded_at TEXT,
                    FOREIGN KEY (version_id) REFERENCES model_versions (id)
                )
            ''')
        
        # Initialize download history database
        with sqlite3.connect(self.history_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    version_id INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    version_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    download_start TEXT,
                    download_end TEXT,
                    download_duration REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS storage_stats (
                    id INTEGER PRIMARY KEY,
                    total_models INTEGER DEFAULT 0,
                    total_versions INTEGER DEFAULT 0,
                    total_files INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Initialize stats if not exists
            conn.execute('''
                INSERT OR IGNORE INTO storage_stats (id) VALUES (1)
            ''')
    
    def get_model_path(self, model: ModelInfo, version: ModelVersion) -> Path:
        """Get storage path for model."""
        # Create hierarchical directory structure
        model_dir = sanitize_filename(f"{model.name}_{model.id}")
        version_dir = sanitize_filename(f"{version.name}_{version.id}")
        
        # Organize by model type
        type_dir = model.type.value.lower()
        
        return self.base_path / type_dir / model_dir / version_dir
    
    def save_metadata(self, model: ModelInfo, version: ModelVersion, path: Path) -> None:
        """Save model metadata to database."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            # Save model info
            conn.execute('''
                INSERT OR REPLACE INTO models 
                (id, name, type, description, tags, creator, stats, nsfw, 
                 created_at, updated_at, local_path, downloaded_at, file_size, file_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model.id,
                model.name,
                model.type.value,
                model.description,
                json.dumps(model.tags),
                model.creator,
                json.dumps(model.stats),
                model.nsfw,
                model.created_at.isoformat(),
                model.updated_at.isoformat(),
                str(path),
                datetime.now().isoformat(),
                path.stat().st_size if path.exists() else 0,
                self._calculate_directory_hash(path) if path.exists() else None
            ))
            
            # Save version info
            conn.execute('''
                INSERT OR REPLACE INTO model_versions 
                (id, model_id, name, description, base_model, trained_words, 
                 download_url, created_at, local_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version.id,
                model.id,
                version.name,
                version.description,
                version.base_model,
                json.dumps(version.trained_words),
                version.download_url,
                version.created_at.isoformat(),
                str(path),
                json.dumps(self._serialize_version_metadata(version))
            ))
            
            # Save file info
            for file in version.files:
                file_path = path / file.name
                conn.execute('''
                    INSERT OR REPLACE INTO model_files 
                    (id, version_id, name, size_bytes, format, fp, hash, 
                     download_url, metadata, local_path, downloaded_at, verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file.id,
                    version.id,
                    file.name,
                    file.size_bytes,
                    file.format,
                    file.fp,
                    file.hash,
                    file.download_url,
                    json.dumps(file.metadata),
                    str(file_path),
                    datetime.now().isoformat() if file_path.exists() else None,
                    self._verify_file_hash(file_path, file.hash) if file_path.exists() and file.hash else False
                ))
            
            # Save image info
            for image in version.images:
                image_path = path / "images" / f"{image.id}.jpg"
                conn.execute('''
                    INSERT OR REPLACE INTO model_images 
                    (id, version_id, url, width, height, hash, nsfw, meta, 
                     local_path, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    image.id,
                    version.id,
                    image.url,
                    image.width,
                    image.height,
                    image.hash,
                    image.nsfw,
                    json.dumps(image.meta) if image.meta else None,
                    str(image_path),
                    datetime.now().isoformat() if image_path.exists() else None
                ))
        
        # Update storage stats
        self._update_storage_stats()
    
    def get_download_history(self) -> List[Dict[str, Any]]:
        """Get download history."""
        with sqlite3.connect(self.history_db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM download_history 
                ORDER BY created_at DESC
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def add_to_history(self, model: ModelInfo, version: ModelVersion, path: Path) -> None:
        """Add download to history."""
        with sqlite3.connect(self.history_db_path) as conn:
            conn.execute('''
                INSERT INTO download_history 
                (model_id, version_id, model_name, version_name, file_path, 
                 file_size, download_start, download_end, download_duration, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model.id,
                version.id,
                model.name,
                version.name,
                str(path),
                path.stat().st_size if path.exists() else 0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                0.0,  # Duration would be calculated by download manager
                path.exists()
            ))
    
    def check_disk_space(self, required_bytes: int) -> bool:
        """Check if enough disk space is available."""
        try:
            free_bytes = shutil.disk_usage(self.base_path).free
            return free_bytes >= required_bytes
        except Exception:
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with sqlite3.connect(self.history_db_path) as conn:
            cursor = conn.execute('SELECT * FROM storage_stats WHERE id = 1')
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                stats = dict(zip(columns, row))
                
                # Add human-readable size
                stats['total_size_human'] = format_file_size(stats['total_size_bytes'])
                
                # Add disk usage info
                try:
                    disk_usage = shutil.disk_usage(self.base_path)
                    stats['disk_free_bytes'] = disk_usage.free
                    stats['disk_total_bytes'] = disk_usage.total
                    stats['disk_used_bytes'] = disk_usage.used
                    stats['disk_free_human'] = format_file_size(disk_usage.free)
                    stats['disk_total_human'] = format_file_size(disk_usage.total)
                    stats['disk_used_human'] = format_file_size(disk_usage.used)
                except Exception:
                    stats['disk_free_bytes'] = 0
                    stats['disk_total_bytes'] = 0
                    stats['disk_used_bytes'] = 0
                
                return stats
            else:
                return {}
    
    def find_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Find model by ID in local storage."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM models WHERE id = ?
            ''', (model_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def find_models_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Find models by name (fuzzy search)."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM models
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY name
            ''', (f"%{name}%", f"%{name}%"))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_models_by_type(self, model_type: str) -> List[Dict[str, Any]]:
        """Get models by type."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM models
                WHERE type = ?
                ORDER BY downloaded_at DESC
            ''', (model_type,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recently_downloaded(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently downloaded models."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM models
                WHERE downloaded_at IS NOT NULL
                ORDER BY downloaded_at DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """Clean up orphaned files and update database."""
        orphaned_files = 0
        orphaned_dirs = 0
        freed_bytes = 0
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            # Get all file paths from database
            cursor = conn.execute('SELECT local_path FROM model_files WHERE local_path IS NOT NULL')
            db_files = {row[0] for row in cursor.fetchall()}
            
            cursor = conn.execute('SELECT local_path FROM models WHERE local_path IS NOT NULL')
            db_dirs = {row[0] for row in cursor.fetchall()}
            
            # Find orphaned files
            for file_path in db_files:
                path = Path(file_path)
                if not path.exists():
                    orphaned_files += 1
                    # Remove from database
                    conn.execute('UPDATE model_files SET local_path = NULL WHERE local_path = ?', (str(path),))
            
            # Find orphaned directories
            for dir_path in db_dirs:
                path = Path(dir_path)
                if not path.exists():
                    orphaned_dirs += 1
                    # Remove from database
                    conn.execute('UPDATE models SET local_path = NULL WHERE local_path = ?', (str(path),))
            
            # Find actual files not in database
            if self.base_path.exists():
                for file_path in self.base_path.rglob('*'):
                    if file_path.is_file() and str(file_path) not in db_files:
                        if file_path.suffix.lower() in ['.safetensors', '.ckpt', '.pt', '.pth', '.bin']:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            freed_bytes += file_size
                            orphaned_files += 1
        
        # Update storage stats
        self._update_storage_stats()
        
        return {
            'orphaned_files': orphaned_files,
            'orphaned_dirs': orphaned_dirs,
            'freed_bytes': freed_bytes,
            'freed_human': format_file_size(freed_bytes)
        }
    
    def export_metadata(self, output_path: Path) -> None:
        """Export all metadata to JSON file."""
        data = {
            'models': [],
            'export_date': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            # Get all models
            cursor = conn.execute('SELECT * FROM models ORDER BY id')
            model_columns = [desc[0] for desc in cursor.description]
            
            for model_row in cursor.fetchall():
                model_data = dict(zip(model_columns, model_row))
                
                # Parse JSON fields safely
                try:
                    model_data['tags'] = json.loads(model_data['tags']) if model_data['tags'] else []
                except (json.JSONDecodeError, TypeError):
                    model_data['tags'] = []
                
                try:
                    model_data['stats'] = json.loads(model_data['stats']) if model_data['stats'] else {}
                except (json.JSONDecodeError, TypeError):
                    model_data['stats'] = {}
                
                # Get versions for this model
                version_cursor = conn.execute('''
                    SELECT * FROM model_versions WHERE model_id = ? ORDER BY id
                ''', (model_data['id'],))
                
                version_columns = [desc[0] for desc in version_cursor.description]
                versions = []
                
                for version_row in version_cursor.fetchall():
                    version_data = dict(zip(version_columns, version_row))
                    
                    # Parse JSON fields safely
                    try:
                        version_data['trained_words'] = json.loads(version_data['trained_words']) if version_data['trained_words'] else []
                    except (json.JSONDecodeError, TypeError):
                        version_data['trained_words'] = []
                    
                    versions.append(version_data)
                
                model_data['versions'] = versions
                data['models'].append(model_data)
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_metadata(self, input_path: Path) -> Dict[str, int]:
        """Import metadata from JSON file."""
        if not input_path.exists():
            raise FileNotFoundError(f"Import file not found: {input_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_models = 0
        imported_versions = 0
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            for model_data in data.get('models', []):
                # Import model
                conn.execute('''
                    INSERT OR REPLACE INTO models 
                    (id, name, type, description, tags, creator, stats, nsfw, 
                     created_at, updated_at, local_path, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model_data['id'],
                    model_data['name'],
                    model_data['type'],
                    model_data.get('description'),
                    json.dumps(model_data.get('tags', [])),
                    model_data['creator'],
                    json.dumps(model_data.get('stats', {})),
                    model_data['nsfw'],
                    model_data['created_at'],
                    model_data['updated_at'],
                    model_data.get('local_path'),
                    model_data.get('downloaded_at')
                ))
                imported_models += 1
                
                # Import versions
                for version_data in model_data.get('versions', []):
                    conn.execute('''
                        INSERT OR REPLACE INTO model_versions 
                        (id, model_id, name, description, base_model, trained_words, 
                         download_url, created_at, local_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        version_data['id'],
                        model_data['id'],
                        version_data['name'],
                        version_data.get('description'),
                        version_data.get('base_model'),
                        json.dumps(version_data.get('trained_words', [])),
                        version_data.get('download_url'),
                        version_data['created_at'],
                        version_data.get('local_path')
                    ))
                    imported_versions += 1
        
        # Update storage stats
        self._update_storage_stats()
        
        return {
            'imported_models': imported_models,
            'imported_versions': imported_versions
        }
    
    def _calculate_directory_hash(self, path: Path) -> str:
        """Calculate hash for directory contents."""
        if not path.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        for file_path in sorted(path.rglob('*')):
            if file_path.is_file():
                hash_md5.update(str(file_path.relative_to(path)).encode())
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                except Exception:
                    pass
        
        return hash_md5.hexdigest()
    
    def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """Verify file hash."""
        if not file_path.exists() or not expected_hash:
            return False
        
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest().lower() == expected_hash.lower()
        except Exception:
            return False
    
    def _serialize_version_metadata(self, version: ModelVersion) -> Dict[str, Any]:
        """Serialize version metadata."""
        return {
            'files_count': len(version.files),
            'images_count': len(version.images),
            'total_size_bytes': sum(f.size_bytes for f in version.files),
            'file_formats': list(set(f.format for f in version.files)),
            'has_safetensors': any(f.name.endswith('.safetensors') for f in version.files),
            'has_ckpt': any(f.name.endswith('.ckpt') for f in version.files),
            'image_sizes': [(img.width, img.height) for img in version.images],
            'nsfw_images': sum(1 for img in version.images if img.nsfw)
        }
    
    def _update_storage_stats(self):
        """Update storage statistics."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            # Count totals
            cursor = conn.execute('SELECT COUNT(*) FROM models')
            total_models = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM model_versions')
            total_versions = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM model_files')
            total_files = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT SUM(size_bytes) FROM model_files')
            total_size = cursor.fetchone()[0] or 0
            
            # Update stats
            with sqlite3.connect(self.history_db_path) as history_conn:
                history_conn.execute('''
                    UPDATE storage_stats 
                    SET total_models = ?, total_versions = ?, total_files = ?, 
                        total_size_bytes = ?, last_updated = ?
                    WHERE id = 1
                ''', (total_models, total_versions, total_files, total_size, datetime.now().isoformat()))


class MetadataCache:
    """In-memory cache for frequently accessed metadata."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache."""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Set item in cache."""
        # Remove oldest items if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': 0.0,  # Would need to track hits/misses
            'memory_usage': sum(len(str(v)) for v in self.cache.values())
        }


class BackupManager:
    """Backup manager for metadata and configuration."""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.backup_dir = storage_manager.base_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, name: Optional[str] = None) -> Path:
        """Create a backup of all metadata."""
        if name is None:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{name}.json"
        self.storage_manager.export_metadata(backup_path)
        
        return backup_path
    
    def restore_backup(self, backup_path: Path) -> Dict[str, int]:
        """Restore from backup."""
        return self.storage_manager.import_metadata(backup_path)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        for backup_file in self.backup_dir.glob("*.json"):
            try:
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.stem,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'size_human': format_file_size(stat.st_size),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue
        
        return sorted(backups, key=lambda x: x['modified'], reverse=True)
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Remove old backups, keeping only the most recent ones."""
        backups = self.list_backups()
        removed = 0
        
        for backup in backups[keep_count:]:
            try:
                Path(backup['path']).unlink()
                removed += 1
            except Exception:
                continue
        
        return removed