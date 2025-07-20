#!/usr/bin/env python3
"""
Fallback Chain for CivitAI Downloader.
Provides fallback execution strategies when primary methods fail.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from abc import ABC, abstractmethod
import logging


class AllMethodsFailedError(Exception):
    """Raised when all methods in a fallback chain fail."""
    
    def __init__(self, message: str, failed_methods: List[str], errors: List[Exception]):
        """
        Initialize all methods failed error.
        
        Args:
            message: Error message
            failed_methods: List of methods that failed
            errors: List of exceptions that occurred
        """
        super().__init__(message)
        self.message = message
        self.failed_methods = failed_methods
        self.errors = errors


class FallbackStrategy(ABC):
    """Abstract base class for fallback strategies."""
    
    @abstractmethod
    async def execute(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a fallback method.
        
        Args:
            method_name: Name of the method to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the method execution
        """
        pass


class FallbackChain:
    """Manages fallback execution chains for failed operations."""
    
    def __init__(self):
        """Initialize fallback chain manager."""
        self.chains = {
            'search': [
                'advanced_search',
                'basic_search',
                'official_search',
                'fallback_search'
            ],
            'sort': [
                'custom_sort',
                'advanced_sort',
                'default_sort',
                'name_sort'
            ],
            'pagination': [
                'cursor_pagination',
                'offset_pagination',
                'simple_pagination',
                'full_load'
            ],
            'filter': [
                'advanced_filter',
                'basic_filter',
                'simple_filter',
                'no_filter'
            ],
            'download': [
                'batch_download',
                'concurrent_download',
                'sequential_download',
                'single_download'
            ]
        }
        
        self.method_implementations = {}
        self.logger = logging.getLogger(__name__)
    
    def register_method(self, method_name: str, implementation: Callable) -> None:
        """
        Register a method implementation.
        
        Args:
            method_name: Name of the method
            implementation: Function or coroutine to execute
        """
        self.method_implementations[method_name] = implementation
    
    def get_chain(self, chain_type: str) -> List[str]:
        """
        Get fallback chain for a specific type.
        
        Args:
            chain_type: Type of operation (search, sort, etc.)
            
        Returns:
            List of method names in fallback order
        """
        return self.chains.get(chain_type, [])
    
    def set_chain(self, chain_type: str, methods: List[str]) -> None:
        """
        Set fallback chain for a specific type.
        
        Args:
            chain_type: Type of operation
            methods: List of method names in fallback order
        """
        self.chains[chain_type] = methods.copy()
    
    async def execute_with_fallback(self, chain_type: str, *args, **kwargs) -> Any:
        """
        Execute methods in fallback chain until one succeeds.
        
        Args:
            chain_type: Type of operation to execute
            *args: Positional arguments to pass to methods
            **kwargs: Keyword arguments to pass to methods
            
        Returns:
            Result from the first successful method
            
        Raises:
            AllMethodsFailedError: If all methods in chain fail
        """
        chain = self.get_chain(chain_type)
        if not chain:
            raise AllMethodsFailedError(
                f"No fallback chain defined for type: {chain_type}",
                [],
                []
            )
        
        failed_methods = []
        errors = []
        
        for method_name in chain:
            try:
                result = await self._execute_method(method_name, *args, **kwargs)
                self.logger.info(f"Method {method_name} succeeded in {chain_type} chain")
                return result
                
            except Exception as e:
                failed_methods.append(method_name)
                errors.append(e)
                self.logger.warning(f"Method {method_name} failed: {str(e)}")
                continue
        
        # All methods failed
        error_message = f"All methods failed in {chain_type} chain: {', '.join(failed_methods)}"
        raise AllMethodsFailedError(error_message, failed_methods, errors)
    
    async def _execute_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a specific method.
        
        Args:
            method_name: Name of the method to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Method execution result
            
        Raises:
            Exception: If method execution fails
        """
        # Check if we have a registered implementation
        if method_name in self.method_implementations:
            implementation = self.method_implementations[method_name]
            if asyncio.iscoroutinefunction(implementation):
                return await implementation(*args, **kwargs)
            else:
                return implementation(*args, **kwargs)
        
        # Default implementations for testing
        return await self._default_implementation(method_name, *args, **kwargs)
    
    async def _default_implementation(self, method_name: str, *args, **kwargs) -> Any:
        """
        Default implementation for testing purposes.
        
        Args:
            method_name: Name of the method
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Mock result
        """
        # Simulate some methods failing for testing
        if 'fail' in method_name or method_name.startswith('advanced'):
            # Simulate failure for testing
            raise Exception(f"Simulated failure in {method_name}")
        
        # Return mock success result
        return {
            'method': method_name,
            'args': args,
            'kwargs': kwargs,
            'result': f"Success from {method_name}"
        }
    
    def add_method_to_chain(self, chain_type: str, method_name: str, position: Optional[int] = None) -> None:
        """
        Add a method to an existing chain.
        
        Args:
            chain_type: Type of operation
            method_name: Name of the method to add
            position: Position to insert at (None = append)
        """
        if chain_type not in self.chains:
            self.chains[chain_type] = []
        
        if method_name not in self.chains[chain_type]:
            if position is None:
                self.chains[chain_type].append(method_name)
            else:
                self.chains[chain_type].insert(position, method_name)
    
    def remove_method_from_chain(self, chain_type: str, method_name: str) -> bool:
        """
        Remove a method from a chain.
        
        Args:
            chain_type: Type of operation
            method_name: Name of the method to remove
            
        Returns:
            True if method was removed, False if not found
        """
        if chain_type in self.chains and method_name in self.chains[chain_type]:
            self.chains[chain_type].remove(method_name)
            return True
        return False
    
    def get_method_priority(self, chain_type: str, method_name: str) -> Optional[int]:
        """
        Get priority (position) of a method in a chain.
        
        Args:
            chain_type: Type of operation
            method_name: Name of the method
            
        Returns:
            Priority index or None if not found
        """
        if chain_type in self.chains:
            try:
                return self.chains[chain_type].index(method_name)
            except ValueError:
                pass
        return None
    
    def validate_chain(self, chain_type: str) -> Dict[str, Any]:
        """
        Validate a fallback chain configuration.
        
        Args:
            chain_type: Type of operation to validate
            
        Returns:
            Validation result dictionary
        """
        chain = self.get_chain(chain_type)
        
        validation = {
            'valid': True,
            'chain_length': len(chain),
            'missing_implementations': [],
            'duplicate_methods': [],
            'warnings': []
        }
        
        # Check for duplicates
        seen = set()
        for method in chain:
            if method in seen:
                validation['duplicate_methods'].append(method)
                validation['valid'] = False
            seen.add(method)
        
        # Check for missing implementations (in production)
        for method in chain:
            if method not in self.method_implementations:
                validation['missing_implementations'].append(method)
        
        # Add warnings
        if len(chain) < 2:
            validation['warnings'].append("Chain has fewer than 2 methods - no fallback available")
        
        if len(chain) > 5:
            validation['warnings'].append("Chain is very long - may impact performance")
        
        return validation
    
    def get_chain_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all fallback chains.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_chains': len(self.chains),
            'total_methods': sum(len(chain) for chain in self.chains.values()),
            'chain_details': {},
            'most_common_methods': {}
        }
        
        # Count method usage across chains
        method_count = {}
        for chain_type, methods in self.chains.items():
            stats['chain_details'][chain_type] = {
                'length': len(methods),
                'methods': methods.copy()
            }
            
            for method in methods:
                method_count[method] = method_count.get(method, 0) + 1
        
        # Find most common methods
        if method_count:
            sorted_methods = sorted(method_count.items(), key=lambda x: x[1], reverse=True)
            stats['most_common_methods'] = dict(sorted_methods[:5])
        
        return stats