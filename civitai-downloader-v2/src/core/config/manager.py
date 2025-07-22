import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Configuration management with JSON and environment variable support."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to config file. If None, uses default ~/.civitai/config.json
        """
        if config_path is None:
            self.config_path = Path.home() / ".civitai" / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self._config: Dict[str, Any] = {}
        self._loaded = False
    
    async def load_config(self) -> None:
        """Load configuration from file and environment variables."""
        # Create default config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load from JSON file if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                self._config = {}
        else:
            # Create default config file
            self._config = self._get_default_config()
            self.save_config()
        
        # Override with environment variables
        self._load_env_overrides()
        self._loaded = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support.
        
        Args:
            key: Configuration key (supports dot notation like 'api.base_url')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            logger.warning("Config not loaded yet, returning default")
            return default
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Configuration section as dictionary
        """
        return self.get(section, {})
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration data.
        
        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value with dot notation support.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise
    
    async def save_config_async(self) -> None:
        """Async version of save_config."""
        self.save_config()  # Delegate to sync version
    
    @property
    def config_file(self) -> Path:
        """Get config file path."""
        return self.config_path
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'api': {
                'base_url': 'https://civitai.com/api/v1',
                'timeout': 30,
                'max_retries': 3
            },
            'database': {
                'path': 'data/civitai.db'
            },
            'download': {
                'base_directory': 'downloads',
                'max_concurrent': 3,
                'chunk_size': 8192,
                'verify_ssl': True
            },
            'cache': {
                'enabled': True,
                'max_size': 1000,
                'ttl_seconds': 3600
            }
        }
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        # Map of environment variables to config keys
        env_mappings = {
            'CIVITAI_API_KEY': 'api.api_key',
            'CIVITAI_API_URL': 'api.base_url',
            'CIVITAI_DB_PATH': 'database.path',
            'CIVITAI_MAX_CONCURRENT': 'download.max_concurrent',
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert to appropriate type
                if config_key.endswith('max_concurrent'):
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {env_value}")
                        continue
                
                self.set(config_key, env_value)