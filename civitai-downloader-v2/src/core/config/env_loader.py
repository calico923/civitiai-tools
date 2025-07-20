#!/usr/bin/env python3
"""
Environment Variable Loader for CivitAI Downloader.
Loads environment variables from .env files with proper precedence.
"""

import os
from pathlib import Path
from typing import Dict, Optional


def load_env_file(env_file_path: str) -> Dict[str, str]:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file_path: Path to the .env file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file_path)
    
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                    
    except (IOError, UnicodeDecodeError) as e:
        # Log error but don't fail - environment loading should be resilient
        print(f"Warning: Failed to load .env file {env_file_path}: {e}")
    
    return env_vars


def load_dotenv(project_root: Optional[str] = None) -> None:
    """
    Load environment variables from .env files with proper precedence.
    
    Precedence order (highest to lowest):
    1. Existing environment variables (os.environ)
    2. .env.local (local overrides, not in git)
    3. .env (main configuration file)
    
    Args:
        project_root: Root directory to search for .env files (defaults to current working directory)
    """
    if project_root is None:
        project_root = os.getcwd()
    
    root_path = Path(project_root)
    
    # Files to load in reverse precedence order (last loaded wins)
    env_files = [
        root_path / '.env',
        root_path / '.env.local'
    ]
    
    # Collect all env vars from files
    all_env_vars = {}
    
    for env_file in env_files:
        if env_file.exists():
            file_vars = load_env_file(str(env_file))
            all_env_vars.update(file_vars)
    
    # Set environment variables, but don't override existing ones
    for key, value in all_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value


def ensure_env_loaded() -> None:
    """
    Ensure environment variables are loaded from .env files.
    This function is safe to call multiple times.
    """
    # Only load if we haven't already loaded from a .env file
    if not hasattr(ensure_env_loaded, '_loaded'):
        # Try to find project root by looking for common project files
        current_dir = Path(__file__).parent
        project_root = None
        
        # Walk up the directory tree looking for project markers
        for parent in [current_dir] + list(current_dir.parents):
            if any((parent / marker).exists() for marker in ['.env', '.env.example', 'pyproject.toml', 'setup.py']):
                project_root = str(parent)
                break
        
        # Load environment variables
        load_dotenv(project_root)
        ensure_env_loaded._loaded = True


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable value, ensuring .env files are loaded first.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    ensure_env_loaded()
    return os.environ.get(key, default)


def get_civitai_api_key() -> Optional[str]:
    """
    Get CivitAI API key from environment variables.
    
    Returns:
        API key or None if not found
    """
    return get_env_var('CIVITAI_API_KEY')


def get_config_from_env() -> Dict[str, str]:
    """
    Get all CivitAI configuration from environment variables.
    
    Returns:
        Dictionary of configuration values
    """
    ensure_env_loaded()
    
    config_keys = [
        'CIVITAI_API_KEY',
        'CIVITAI_BASE_URL',
        'CIVITAI_TIMEOUT',
        'CIVITAI_MAX_RETRIES',
        'CIVITAI_CONCURRENT_DOWNLOADS',
        'CIVITAI_CHUNK_SIZE',
        'CIVITAI_VERIFY_SSL',
        'CIVITAI_LOG_LEVEL'
    ]
    
    config = {}
    for key in config_keys:
        value = os.environ.get(key)
        if value is not None:
            config[key] = value
    
    return config


if __name__ == "__main__":
    # Test the env loader
    ensure_env_loaded()
    
    print("Loaded CivitAI configuration:")
    config = get_config_from_env()
    
    # Mask sensitive values for display
    for key, value in config.items():
        if 'key' in key.lower() or 'token' in key.lower():
            display_value = f"***{value[-4:]}" if len(value) > 4 else "***"
        else:
            display_value = value
        print(f"  {key}={display_value}")