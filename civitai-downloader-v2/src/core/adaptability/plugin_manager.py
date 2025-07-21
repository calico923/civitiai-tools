#!/usr/bin/env python3
"""
Plugin Management System.
Implements requirement 15.4: Plugin-based feature extension.
"""

import logging
import importlib
import importlib.util
import inspect
import asyncio
from typing import Dict, List, Any, Optional, Type, Callable, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import json
from enum import Enum

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported."""
    MODEL_PROCESSOR = "model_processor"
    SEARCH_ENHANCER = "search_enhancer"
    EXPORT_FORMATTER = "export_formatter"
    SECURITY_SCANNER = "security_scanner"
    UI_EXTENSION = "ui_extension"


class PluginStatus(Enum):
    """Plugin status states."""
    UNKNOWN = "unknown"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Plugin metadata information."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    api_version: str = "1.0"
    min_core_version: str = "1.0.0"
    max_core_version: Optional[str] = None
    configuration: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """
    Base class for all plugins.
    Implements requirement 15.4: Plugin interface standardization.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """Initialize plugin with metadata."""
        self.metadata = metadata
        self.status = PluginStatus.UNKNOWN
        self.config = {}
        self.logger = logging.getLogger(f"plugin.{metadata.name}")
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin.
        
        Args:
            config: Plugin configuration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process data with the plugin.
        
        Args:
            data: Data to process
            context: Processing context
            
        Returns:
            Processed data
        """
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the plugin gracefully."""
        self.status = PluginStatus.DISABLED
        self.logger.info(f"Plugin {self.metadata.name} shutdown")
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "type": self.metadata.plugin_type.value,
            "status": self.status.value,
            "dependencies": self.metadata.dependencies
        }


class ModelProcessorPlugin(Plugin):
    """Base class for model processing plugins."""
    
    async def process_model(self, model_data: Dict[str, Any], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Process model data."""
        return await self.process(model_data, context)


class SearchEnhancerPlugin(Plugin):
    """Base class for search enhancement plugins."""
    
    async def enhance_search(self, search_params: Dict[str, Any],
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance search parameters."""
        return await self.process(search_params, context)


@dataclass
class PluginRegistry:
    """Registry of available plugins."""
    plugins: Dict[str, Plugin] = field(default_factory=dict)
    plugin_types: Dict[PluginType, List[str]] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    load_order: List[str] = field(default_factory=list)
    
    def register(self, plugin: Plugin) -> None:
        """Register a plugin in the registry."""
        name = plugin.metadata.name
        plugin_type = plugin.metadata.plugin_type
        
        self.plugins[name] = plugin
        
        if plugin_type not in self.plugin_types:
            self.plugin_types[plugin_type] = []
        self.plugin_types[plugin_type].append(name)
        
        # Track dependencies
        self.dependencies[name] = set(plugin.metadata.dependencies)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type."""
        plugin_names = self.plugin_types.get(plugin_type, [])
        return [self.plugins[name] for name in plugin_names]
    
    def resolve_dependencies(self) -> List[str]:
        """Resolve plugin load order based on dependencies."""
        resolved = []
        visited = set()
        temp_visited = set()
        
        def visit(plugin_name: str):
            if plugin_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {plugin_name}")
            if plugin_name in visited:
                return
            
            temp_visited.add(plugin_name)
            
            # Visit dependencies first
            for dep in self.dependencies.get(plugin_name, []):
                if dep in self.plugins:
                    visit(dep)
            
            temp_visited.remove(plugin_name)
            visited.add(plugin_name)
            resolved.append(plugin_name)
        
        # Visit all plugins
        for plugin_name in self.plugins:
            if plugin_name not in visited:
                visit(plugin_name)
        
        self.load_order = resolved
        return resolved


class PluginManager:
    """
    Manages plugin lifecycle and execution.
    Implements requirement 15.4: Plugin-based extension system.
    """
    
    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize plugin manager.
        
        Args:
            plugin_dir: Directory containing plugins
        """
        self.plugin_dir = plugin_dir or Path("./plugins")
        self.registry = PluginRegistry()
        self.active_plugins: Set[str] = set()
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Create plugin directory if it doesn't exist
        self.plugin_dir.mkdir(exist_ok=True)
        
        # Plugin hooks for different processing stages
        self.hooks: Dict[str, List[Callable]] = {
            "pre_search": [],
            "post_search": [],
            "pre_download": [],
            "post_download": [],
            "pre_export": [],
            "post_export": []
        }
    
    async def discover_plugins(self) -> List[str]:
        """
        Discover plugins in the plugin directory.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        # Look for Python files in plugin directory
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("__"):
                continue
            
            try:
                plugin_name = await self._load_plugin_from_file(plugin_file)
                if plugin_name:
                    discovered.append(plugin_name)
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")
        
        # Look for plugin packages
        for plugin_dir in self.plugin_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("__"):
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    try:
                        plugin_name = await self._load_plugin_from_package(plugin_dir)
                        if plugin_name:
                            discovered.append(plugin_name)
                    except Exception as e:
                        logger.error(f"Failed to load plugin package {plugin_dir}: {e}")
        
        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered
    
    async def _load_plugin_from_file(self, plugin_file: Path) -> Optional[str]:
        """Load plugin from a single Python file."""
        module_name = f"plugin_{plugin_file.stem}"
        
        # Load module
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin classes
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, Plugin) and 
                obj != Plugin and
                not inspect.isabstract(obj)):
                
                # Look for plugin metadata
                if hasattr(obj, 'PLUGIN_METADATA'):
                    metadata_dict = obj.PLUGIN_METADATA
                    metadata = PluginMetadata(**metadata_dict)
                    
                    # Create plugin instance
                    plugin = obj(metadata)
                    plugin.status = PluginStatus.LOADED
                    
                    # Register plugin
                    self.registry.register(plugin)
                    
                    logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
                    return metadata.name
        
        return None
    
    async def _load_plugin_from_package(self, plugin_dir: Path) -> Optional[str]:
        """Load plugin from a package directory."""
        # Read plugin.json for metadata
        metadata_file = plugin_dir / "plugin.json"
        if not metadata_file.exists():
            return None
        
        with open(metadata_file) as f:
            metadata_dict = json.load(f)
        
        metadata = PluginMetadata(**metadata_dict)
        
        # Import the plugin module
        module_name = f"plugin_{plugin_dir.name}"
        spec = importlib.util.spec_from_file_location(
            module_name, 
            plugin_dir / "__init__.py"
        )
        
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for the main plugin class
        plugin_class = getattr(module, metadata_dict.get('main_class', 'MainPlugin'), None)
        
        if plugin_class and issubclass(plugin_class, Plugin):
            # Create plugin instance
            plugin = plugin_class(metadata)
            plugin.status = PluginStatus.LOADED
            
            # Register plugin
            self.registry.register(plugin)
            
            logger.info(f"Loaded plugin package: {metadata.name} v{metadata.version}")
            return metadata.name
        
        return None
    
    async def initialize_plugins(self) -> Dict[str, bool]:
        """
        Initialize all loaded plugins.
        
        Returns:
            Dictionary of plugin initialization results
        """
        results = {}
        
        # Resolve load order
        try:
            load_order = self.registry.resolve_dependencies()
        except ValueError as e:
            logger.error(f"Failed to resolve plugin dependencies: {e}")
            return results
        
        # Initialize plugins in dependency order
        for plugin_name in load_order:
            plugin = self.registry.plugins[plugin_name]
            config = self.plugin_configs.get(plugin_name, {})
            
            try:
                success = await plugin.initialize(config)
                results[plugin_name] = success
                
                if success:
                    plugin.status = PluginStatus.INITIALIZED
                    self.active_plugins.add(plugin_name)
                    logger.info(f"Initialized plugin: {plugin_name}")
                else:
                    plugin.status = PluginStatus.ERROR
                    logger.error(f"Failed to initialize plugin: {plugin_name}")
                    
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                results[plugin_name] = False
                logger.error(f"Exception initializing plugin {plugin_name}: {e}")
        
        return results
    
    async def execute_hook(self, hook_name: str, data: Any, 
                          context: Dict[str, Any]) -> Any:
        """
        Execute a plugin hook.
        
        Args:
            hook_name: Name of the hook
            data: Data to process
            context: Processing context
            
        Returns:
            Processed data
        """
        if hook_name not in self.hooks:
            return data
        
        result = data
        
        for hook_func in self.hooks[hook_name]:
            try:
                result = await hook_func(result, context)
            except Exception as e:
                logger.error(f"Hook {hook_name} failed: {e}")
        
        return result
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a callback for a hook."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(callback)
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all plugins."""
        return {
            "total_plugins": len(self.registry.plugins),
            "active_plugins": len(self.active_plugins),
            "plugin_types": {
                ptype.value: len(plugins) 
                for ptype, plugins in self.registry.plugin_types.items()
            },
            "plugins": {
                name: plugin.get_info() 
                for name, plugin in self.registry.plugins.items()
            }
        }
    
    async def shutdown_all_plugins(self) -> None:
        """Shutdown all active plugins."""
        for plugin_name in list(self.active_plugins):
            plugin = self.registry.plugins[plugin_name]
            try:
                await plugin.shutdown()
                self.active_plugins.remove(plugin_name)
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_name}: {e}")
        
        logger.info("All plugins shut down")
    
    def configure_plugin(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """Configure a plugin."""
        self.plugin_configs[plugin_name] = config
        
        # If plugin is already active, update its configuration
        if plugin_name in self.active_plugins:
            plugin = self.registry.plugins[plugin_name]
            plugin.config.update(config)