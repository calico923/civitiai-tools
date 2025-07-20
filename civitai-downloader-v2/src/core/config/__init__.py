"""
Configuration management package for CivitAI Downloader v2.

This package provides comprehensive configuration management with:
- YAML configuration file support
- Environment variable overrides
- Type conversion and validation
- Default value fallbacks
- Secure sensitive data handling
"""

from .system_config import SystemConfig

__all__ = ['SystemConfig']