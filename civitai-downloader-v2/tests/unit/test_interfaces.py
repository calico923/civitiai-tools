#!/usr/bin/env python3
"""
Interface specification tests.
Tests for abstract base classes and their contract definitions.
"""

import pytest
from abc import ABC, abstractmethod
from pathlib import Path
import importlib.util
from typing import List, AsyncIterator, Dict, Any, Optional


class TestInterfaces:
    """Test abstract interface definitions and contracts."""
    
    @property
    def interfaces_dir(self) -> Path:
        """Get the interfaces directory."""
        return Path(__file__).parent.parent.parent / "src" / "core" / "interfaces"
    
    def test_search_strategy_interface(self):
        """Test SearchStrategy abstract interface exists and has correct methods."""
        # Import the SearchStrategy interface
        search_strategy_path = self.interfaces_dir / "search_strategy.py"
        assert search_strategy_path.exists(), "search_strategy.py must exist"
        
        spec = importlib.util.spec_from_file_location("search_strategy", search_strategy_path)
        search_strategy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(search_strategy_module)
        
        # Test SearchStrategy class exists
        assert hasattr(search_strategy_module, 'SearchStrategy'), "SearchStrategy class must exist"
        SearchStrategy = search_strategy_module.SearchStrategy
        
        # Test it's an abstract base class
        assert issubclass(SearchStrategy, ABC), "SearchStrategy must inherit from ABC"
        
        # Test abstract methods exist
        abstract_methods = SearchStrategy.__abstractmethods__
        expected_methods = {'search'}
        assert expected_methods.issubset(abstract_methods), f"SearchStrategy must have abstract methods: {expected_methods}"
        
        # Test method signatures (this will be tested when we create concrete implementations)
        search_method = getattr(SearchStrategy, 'search', None)
        assert search_method is not None, "SearchStrategy must have search method"
    
    def test_export_format_interface(self):
        """Test ExportFormat abstract interface exists and has correct methods."""
        export_format_path = self.interfaces_dir / "export_format.py"
        assert export_format_path.exists(), "export_format.py must exist"
        
        spec = importlib.util.spec_from_file_location("export_format", export_format_path)
        export_format_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(export_format_module)
        
        # Test ExportFormat class exists
        assert hasattr(export_format_module, 'ExportFormat'), "ExportFormat class must exist"
        ExportFormat = export_format_module.ExportFormat
        
        # Test it's an abstract base class
        assert issubclass(ExportFormat, ABC), "ExportFormat must inherit from ABC"
        
        # Test abstract methods exist
        abstract_methods = ExportFormat.__abstractmethods__
        expected_methods = {'export', 'get_extension'}
        assert expected_methods.issubset(abstract_methods), f"ExportFormat must have abstract methods: {expected_methods}"
    
    def test_security_checker_interface(self):
        """Test SecurityChecker abstract interface exists and has correct methods."""
        security_checker_path = self.interfaces_dir / "security_checker.py"
        assert security_checker_path.exists(), "security_checker.py must exist"
        
        spec = importlib.util.spec_from_file_location("security_checker", security_checker_path)
        security_checker_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(security_checker_module)
        
        # Test SecurityChecker class exists
        assert hasattr(security_checker_module, 'SecurityChecker'), "SecurityChecker class must exist"
        SecurityChecker = security_checker_module.SecurityChecker
        
        # Test it's an abstract base class
        assert issubclass(SecurityChecker, ABC), "SecurityChecker must inherit from ABC"
        
        # Test abstract methods exist
        abstract_methods = SecurityChecker.__abstractmethods__
        expected_methods = {'check_security', 'analyze_license', 'assess_privacy_risk'}
        assert expected_methods.issubset(abstract_methods), f"SecurityChecker must have abstract methods: {expected_methods}"
    
    def test_memory_manager_interface(self):
        """Test MemoryManager abstract interface exists and has correct methods."""
        memory_manager_path = self.interfaces_dir / "memory_manager.py"
        assert memory_manager_path.exists(), "memory_manager.py must exist"
        
        spec = importlib.util.spec_from_file_location("memory_manager", memory_manager_path)
        memory_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_manager_module)
        
        # Test MemoryManager class exists
        assert hasattr(memory_manager_module, 'MemoryManager'), "MemoryManager class must exist"
        MemoryManager = memory_manager_module.MemoryManager
        
        # Test it's an abstract base class
        assert issubclass(MemoryManager, ABC), "MemoryManager must inherit from ABC"
        
        # Test abstract methods exist
        abstract_methods = MemoryManager.__abstractmethods__
        expected_methods = {'should_use_streaming', 'get_memory_usage', 'optimize_memory'}
        assert expected_methods.issubset(abstract_methods), f"MemoryManager must have abstract methods: {expected_methods}"
    
    def test_error_handler_interface(self):
        """Test ErrorHandler abstract interface exists and has correct methods."""
        error_handler_path = self.interfaces_dir / "error_handler.py"
        assert error_handler_path.exists(), "error_handler.py must exist"
        
        spec = importlib.util.spec_from_file_location("error_handler", error_handler_path)
        error_handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(error_handler_module)
        
        # Test ErrorHandler class exists
        assert hasattr(error_handler_module, 'ErrorHandler'), "ErrorHandler class must exist"
        ErrorHandler = error_handler_module.ErrorHandler
        
        # Test it's an abstract base class
        assert issubclass(ErrorHandler, ABC), "ErrorHandler must inherit from ABC"
        
        # Test abstract methods exist
        abstract_methods = ErrorHandler.__abstractmethods__
        expected_methods = {'handle_error', 'should_retry', 'get_fallback'}
        assert expected_methods.issubset(abstract_methods), f"ErrorHandler must have abstract methods: {expected_methods}"
    
    def test_interface_inheritance_contracts(self):
        """Test that interfaces cannot be instantiated directly."""
        # This test will verify proper abstract class setup
        
        # Import all interfaces
        interfaces_to_test = [
            ("search_strategy", "SearchStrategy"),
            ("export_format", "ExportFormat"),
            ("security_checker", "SecurityChecker"),
            ("memory_manager", "MemoryManager"),
            ("error_handler", "ErrorHandler")
        ]
        
        for module_name, class_name in interfaces_to_test:
            interface_path = self.interfaces_dir / f"{module_name}.py"
            if interface_path.exists():
                spec = importlib.util.spec_from_file_location(module_name, interface_path)
                interface_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(interface_module)
                
                if hasattr(interface_module, class_name):
                    interface_class = getattr(interface_module, class_name)
                    
                    # Test that trying to instantiate raises TypeError
                    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
                        interface_class()
    
    def test_interface_type_hints(self):
        """Test that interfaces have proper type hints for better IDE support."""
        # This test ensures interfaces have proper type annotations
        
        interfaces_to_check = [
            ("search_strategy", "SearchStrategy"),
            ("export_format", "ExportFormat"),
            ("security_checker", "SecurityChecker"),
            ("memory_manager", "MemoryManager"),
            ("error_handler", "ErrorHandler")
        ]
        
        for module_name, class_name in interfaces_to_check:
            interface_path = self.interfaces_dir / f"{module_name}.py"
            if interface_path.exists():
                # Read the file content to check for type hints
                content = interface_path.read_text()
                
                # Check for typing imports
                assert "from typing import" in content or "import typing" in content, \
                    f"{module_name} should import typing for type hints"
                
                # Check for async support where needed
                if module_name in ["search_strategy", "memory_manager"]:
                    assert "async" in content or "AsyncIterator" in content or "Awaitable" in content, \
                        f"{module_name} should support async operations"
    
    def test_interface_documentation(self):
        """Test that all interfaces have proper docstrings."""
        interfaces_to_check = [
            ("search_strategy", "SearchStrategy"),
            ("export_format", "ExportFormat"),
            ("security_checker", "SecurityChecker"),
            ("memory_manager", "MemoryManager"),
            ("error_handler", "ErrorHandler")
        ]
        
        for module_name, class_name in interfaces_to_check:
            interface_path = self.interfaces_dir / f"{module_name}.py"
            if interface_path.exists():
                spec = importlib.util.spec_from_file_location(module_name, interface_path)
                interface_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(interface_module)
                
                if hasattr(interface_module, class_name):
                    interface_class = getattr(interface_module, class_name)
                    
                    # Test class has docstring
                    assert interface_class.__doc__ is not None, \
                        f"{class_name} must have a class docstring"
                    assert len(interface_class.__doc__.strip()) > 0, \
                        f"{class_name} docstring cannot be empty"