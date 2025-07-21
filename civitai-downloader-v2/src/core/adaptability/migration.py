#!/usr/bin/env python3
"""
Data Migration System.
Implements requirement 20.5-20.6: Backward compatibility and data conversion.
"""

import logging
import json
import shutil
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
from abc import ABC, abstractmethod
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MigrationVersion:
    """Represents a migration version."""
    version: str
    description: str
    migration_date: datetime
    rollback_available: bool = False


class Migration(ABC):
    """Base class for data migrations."""
    
    def __init__(self, from_version: str, to_version: str, description: str):
        """
        Initialize migration.
        
        Args:
            from_version: Source version
            to_version: Target version
            description: Migration description
        """
        self.from_version = from_version
        self.to_version = to_version
        self.description = description
        self.rollback_supported = False
    
    @abstractmethod
    async def migrate(self, data_dir: Path) -> bool:
        """
        Perform the migration.
        
        Args:
            data_dir: Data directory path
            
        Returns:
            True if migration successful
        """
        pass
    
    async def rollback(self, data_dir: Path) -> bool:
        """
        Rollback the migration.
        
        Args:
            data_dir: Data directory path
            
        Returns:
            True if rollback successful
        """
        if not self.rollback_supported:
            raise NotImplementedError("Rollback not supported for this migration")
        return False
    
    def validate_data(self, data_dir: Path) -> Tuple[bool, List[str]]:
        """
        Validate data after migration.
        
        Args:
            data_dir: Data directory path
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        return True, []


class ConfigMigration(Migration):
    """Migration for configuration files."""
    
    def __init__(self):
        super().__init__(
            from_version="1.0",
            to_version="2.0", 
            description="Migrate configuration to new format"
        )
        self.rollback_supported = True
    
    async def migrate(self, data_dir: Path) -> bool:
        """Migrate configuration files."""
        try:
            old_config = data_dir / "config.json"
            new_config = data_dir / "config" / "settings.yaml"
            
            if not old_config.exists():
                logger.info("No old configuration found, skipping migration")
                return True
            
            # Create backup
            backup_path = data_dir / "config.json.backup"
            shutil.copy2(old_config, backup_path)
            
            # Load old config
            with open(old_config, 'r') as f:
                old_data = json.load(f)
            
            # Transform to new format
            new_data = self._transform_config(old_data)
            
            # Create new config directory
            new_config.parent.mkdir(exist_ok=True)
            
            # Write new config (YAML format)
            import yaml
            with open(new_config, 'w') as f:
                yaml.safe_dump(new_data, f, default_flow_style=False)
            
            logger.info("Configuration migrated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Configuration migration failed: {e}")
            return False
    
    def _transform_config(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform old config format to new format."""
        return {
            "api": {
                "base_url": old_config.get("api_url", "https://civitai.com/api/v1"),
                "timeout": old_config.get("timeout", 30),
                "retry_count": old_config.get("retries", 3)
            },
            "download": {
                "directory": old_config.get("download_dir", "./downloads"),
                "concurrent_limit": min(old_config.get("concurrent_downloads", 3), 1),
                "chunk_size": old_config.get("chunk_size", 8192)
            },
            "search": {
                "default_limit": old_config.get("page_size", 100),
                "cache_ttl": old_config.get("cache_minutes", 15) * 60
            }
        }
    
    async def rollback(self, data_dir: Path) -> bool:
        """Rollback configuration migration."""
        try:
            backup_path = data_dir / "config.json.backup"
            original_path = data_dir / "config.json"
            new_config_dir = data_dir / "config"
            
            if backup_path.exists():
                shutil.copy2(backup_path, original_path)
                backup_path.unlink()
                
                # Remove new config directory
                if new_config_dir.exists():
                    shutil.rmtree(new_config_dir)
                
                logger.info("Configuration rollback successful")
                return True
            
        except Exception as e:
            logger.error(f"Configuration rollback failed: {e}")
        
        return False


class DatabaseMigration(Migration):
    """Migration for database schema changes."""
    
    def __init__(self):
        super().__init__(
            from_version="1.0",
            to_version="2.0",
            description="Add new database tables and indexes"
        )
    
    async def migrate(self, data_dir: Path) -> bool:
        """Migrate database schema."""
        db_path = data_dir / "civitai_downloader.db"
        
        if not db_path.exists():
            logger.info("No database found, skipping migration")
            return True
        
        try:
            # Create backup
            backup_path = data_dir / "civitai_downloader.db.backup"
            shutil.copy2(db_path, backup_path)
            
            # Perform migration
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Add new columns to existing tables
                try:
                    cursor.execute("ALTER TABLE models ADD COLUMN security_scan_result TEXT")
                except sqlite3.OperationalError:
                    pass  # Column might already exist
                
                try:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN file_hash TEXT")
                except sqlite3.OperationalError:
                    pass
                
                # Create new tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_licenses (
                        model_id TEXT PRIMARY KEY,
                        allow_commercial_use BOOLEAN,
                        allow_derivatives BOOLEAN,
                        allow_different_license BOOLEAN,
                        allow_no_credit BOOLEAN,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        scan_result TEXT NOT NULL,
                        threats_detected TEXT,
                        scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_security_scans_file_path 
                    ON security_scans(file_path)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_model_licenses_commercial 
                    ON model_licenses(allow_commercial_use)
                """)
                
                conn.commit()
            
            logger.info("Database migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False


class DataMigrator:
    """Handles individual data transformations."""
    
    @staticmethod
    def migrate_model_data_v1_to_v2(model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate model data from v1 to v2 format."""
        migrated = model_data.copy()
        
        # Add new required fields
        if 'security_info' not in migrated:
            migrated['security_info'] = {
                'scan_status': 'not_scanned',
                'threats_detected': [],
                'file_integrity': 'unknown'
            }
        
        if 'license_info' not in migrated:
            migrated['license_info'] = {
                'allow_commercial_use': None,
                'allow_derivatives': None,
                'allow_different_license': None,
                'allow_no_credit': None
            }
        
        # Transform old field names
        if 'model_type' in migrated:
            migrated['type'] = migrated.pop('model_type')
        
        if 'download_count' in migrated:
            migrated['stats'] = migrated.get('stats', {})
            migrated['stats']['downloadCount'] = migrated.pop('download_count')
        
        return migrated
    
    @staticmethod
    def migrate_search_params_v1_to_v2(search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate search parameters from v1 to v2 format."""
        migrated = search_params.copy()
        
        # Transform old parameter names
        if 'page_size' in migrated:
            migrated['limit'] = migrated.pop('page_size')
        
        if 'model_types' in migrated and isinstance(migrated['model_types'], str):
            migrated['types'] = [migrated.pop('model_types')]
        
        # Add new parameters with defaults
        if 'nsfw_filter' not in migrated:
            migrated['nsfw'] = 'false'  # Default to SFW only
        
        return migrated


class MigrationManager:
    """
    Manages data migrations and version compatibility.
    Implements requirement 20.5-20.6: Backward compatibility management.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize migration manager.
        
        Args:
            data_dir: Application data directory
        """
        self.data_dir = data_dir
        self.migrations: List[Migration] = []
        self.version_file = data_dir / "version.json"
        
        # Register built-in migrations
        self._register_builtin_migrations()
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
    
    def _register_builtin_migrations(self) -> None:
        """Register built-in migrations."""
        self.migrations.extend([
            ConfigMigration(),
            DatabaseMigration()
        ])
    
    def register_migration(self, migration: Migration) -> None:
        """Register a custom migration."""
        self.migrations.append(migration)
        logger.info(f"Registered migration: {migration.from_version} -> {migration.to_version}")
    
    def get_current_version(self) -> str:
        """Get current data version."""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r') as f:
                    version_data = json.load(f)
                return version_data.get('version', '1.0')
            except Exception as e:
                logger.warning(f"Failed to read version file: {e}")
        
        return '1.0'  # Default version
    
    def set_current_version(self, version: str) -> None:
        """Set current data version."""
        version_data = {
            'version': version,
            'migration_date': datetime.now().isoformat(),
            'migrator_version': '1.0'
        }
        
        try:
            with open(self.version_file, 'w') as f:
                json.dump(version_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write version file: {e}")
    
    async def migrate_to_latest(self, target_version: str = "2.0") -> bool:
        """
        Migrate data to the latest version.
        
        Args:
            target_version: Target version to migrate to
            
        Returns:
            True if migration successful
        """
        current_version = self.get_current_version()
        
        if current_version == target_version:
            logger.info(f"Already at target version {target_version}")
            return True
        
        logger.info(f"Migrating from version {current_version} to {target_version}")
        
        # Find migration path
        migration_path = self._find_migration_path(current_version, target_version)
        
        if not migration_path:
            logger.error(f"No migration path found from {current_version} to {target_version}")
            return False
        
        # Execute migrations in sequence
        for migration in migration_path:
            logger.info(f"Executing migration: {migration.description}")
            
            try:
                success = await migration.migrate(self.data_dir)
                
                if not success:
                    logger.error(f"Migration failed: {migration.description}")
                    return False
                
                # Validate migration
                is_valid, errors = migration.validate_data(self.data_dir)
                if not is_valid:
                    logger.error(f"Migration validation failed: {errors}")
                    return False
                
                logger.info(f"Migration completed: {migration.description}")
                
            except Exception as e:
                logger.error(f"Migration exception: {e}")
                return False
        
        # Update version
        self.set_current_version(target_version)
        logger.info(f"Successfully migrated to version {target_version}")
        
        return True
    
    def _find_migration_path(self, from_version: str, to_version: str) -> List[Migration]:
        """Find sequence of migrations from source to target version."""
        # Simple linear path for now
        # In a more complex system, this could use graph traversal
        
        path = []
        current = from_version
        
        while current != to_version:
            # Find next migration
            next_migration = None
            for migration in self.migrations:
                if migration.from_version == current:
                    next_migration = migration
                    break
            
            if not next_migration:
                logger.error(f"No migration found from version {current}")
                return []
            
            path.append(next_migration)
            current = next_migration.to_version
        
        return path
    
    async def rollback_to_version(self, target_version: str) -> bool:
        """
        Rollback to a previous version.
        
        Args:
            target_version: Version to rollback to
            
        Returns:
            True if rollback successful
        """
        current_version = self.get_current_version()
        
        if current_version == target_version:
            logger.info(f"Already at version {target_version}")
            return True
        
        logger.info(f"Rolling back from {current_version} to {target_version}")
        
        # Find rollback path (reverse of migration path)
        migration_path = self._find_migration_path(target_version, current_version)
        
        if not migration_path:
            logger.error(f"No rollback path found from {current_version} to {target_version}")
            return False
        
        # Execute rollbacks in reverse order
        for migration in reversed(migration_path):
            if not migration.rollback_supported:
                logger.error(f"Rollback not supported for migration: {migration.description}")
                return False
            
            try:
                success = await migration.rollback(self.data_dir)
                if not success:
                    logger.error(f"Rollback failed: {migration.description}")
                    return False
                
                logger.info(f"Rollback completed: {migration.description}")
                
            except Exception as e:
                logger.error(f"Rollback exception: {e}")
                return False
        
        # Update version
        self.set_current_version(target_version)
        logger.info(f"Successfully rolled back to version {target_version}")
        
        return True
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get history of migrations performed."""
        history = []
        
        for migration in self.migrations:
            history.append({
                'from_version': migration.from_version,
                'to_version': migration.to_version,
                'description': migration.description,
                'rollback_supported': migration.rollback_supported
            })
        
        return history
    
    def validate_current_data(self) -> Tuple[bool, List[str]]:
        """Validate current data integrity."""
        current_version = self.get_current_version()
        errors = []
        
        # Check basic directory structure
        required_dirs = ['config', 'downloads', 'cache']
        for dir_name in required_dirs:
            dir_path = self.data_dir / dir_name
            if not dir_path.exists():
                errors.append(f"Missing required directory: {dir_name}")
        
        # Check database integrity
        db_path = self.data_dir / "civitai_downloader.db"
        if db_path.exists():
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    if result[0] != 'ok':
                        errors.append(f"Database integrity check failed: {result[0]}")
            except Exception as e:
                errors.append(f"Database validation error: {e}")
        
        # Check configuration files
        config_file = self.data_dir / "config" / "settings.yaml"
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    yaml.safe_load(f)
            except Exception as e:
                errors.append(f"Configuration file validation error: {e}")
        
        is_valid = len(errors) == 0
        return is_valid, errors