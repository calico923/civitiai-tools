"""Configuration management."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any

from .utils import get_app_dirs, ensure_app_dirs


@dataclass
class Config:
    """Application configuration."""
    # API settings
    api_key: Optional[str] = None
    api_base_url: str = "https://civitai.com/api/v1"
    api_timeout: int = 30
    api_max_retries: int = 3
    
    # Download settings
    download_path: Optional[str] = None
    concurrent_downloads: int = 1
    max_concurrent_downloads: int = 3
    chunk_size: int = 8192  # 8KB chunks
    resume_downloads: bool = True
    verify_checksums: bool = True
    
    # Search settings
    default_limit: int = 20
    default_sort: str = "Highest Rated"
    show_nsfw: bool = False
    
    # Display settings
    preview_size: int = 512
    show_metadata: bool = True
    color_output: bool = True
    
    # Storage settings
    organize_by_type: bool = True
    organize_by_base_model: bool = True
    save_metadata: bool = True
    max_cache_size_mb: int = 1024
    
    # Advanced settings
    user_agent: str = "CivitAI-Downloader/0.1.0"
    proxy: Optional[str] = None
    verify_ssl: bool = True
    
    def __post_init__(self):
        """Set default download path if not specified."""
        if not self.download_path:
            self.download_path = str(Path.home() / "CivitAI-Models")


class ConfigManager:
    """Manage application configuration."""
    
    def __init__(self):
        ensure_app_dirs()
        self.config_path = get_app_dirs()['config'] / 'config.json'
        self.config = self.load()
    
    def load(self) -> Config:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return Config(**data)
            except (json.JSONDecodeError, TypeError):
                # Invalid config, return default
                return Config()
        return Config()
    
    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)
    
    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return getattr(self.config, key, default)
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.config = Config()
        self.save()
    
    def validate(self) -> bool:
        """Validate configuration."""
        # Check download path
        download_path = Path(self.config.download_path)
        if not download_path.exists():
            try:
                download_path.mkdir(parents=True, exist_ok=True)
            except Exception:
                return False
        
        # Check numeric bounds
        if self.config.concurrent_downloads < 1:
            self.config.concurrent_downloads = 1
        elif self.config.concurrent_downloads > 5:
            self.config.concurrent_downloads = 5
        
        if self.config.chunk_size < 1024:
            self.config.chunk_size = 1024
        elif self.config.chunk_size > 1024 * 1024:  # 1MB max
            self.config.chunk_size = 1024 * 1024
        
        return True
    
    def export_env(self) -> Dict[str, str]:
        """Export configuration as environment variables."""
        env = {}
        for key, value in asdict(self.config).items():
            if value is not None:
                env_key = f"CIVITAI_{key.upper()}"
                env[env_key] = str(value)
        return env
    
    def import_env(self) -> None:
        """Import configuration from environment variables."""
        import os
        
        mapping = {
            'CIVITAI_API_KEY': 'api_key',
            'CIVITAI_DOWNLOAD_PATH': 'download_path',
            'CIVITAI_SHOW_NSFW': 'show_nsfw',
            'CIVITAI_PROXY': 'proxy',
        }
        
        for env_key, config_key in mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                # Convert boolean strings
                if config_key in ['show_nsfw', 'resume_downloads', 'verify_checksums']:
                    value = value.lower() in ['true', 'yes', '1']
                # Convert numeric strings
                elif config_key in ['concurrent_downloads', 'chunk_size', 'api_timeout']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                
                setattr(self.config, config_key, value)