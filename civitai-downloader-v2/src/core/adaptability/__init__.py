#!/usr/bin/env python3
"""
Adaptability module for CivitAI Downloader.
Implements requirement 15: Future API change adaptation system.
"""

from .api_detector import APIChangeDetector, APICapability
from .plugin_manager import PluginManager, Plugin, PluginRegistry
from .migration import DataMigrator, MigrationManager
from .dynamic_types import DynamicModelTypeManager

__all__ = [
    'APICapability',
    'APIChangeDetector',
    'DataMigrator',
    'DynamicModelTypeManager',
    'MigrationManager',
    'Plugin',
    'PluginManager',
    'PluginRegistry'
]