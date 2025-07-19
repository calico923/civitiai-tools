#!/usr/bin/env python3
"""
Project structure validation tests.
Tests the 3-layer architecture directory structure exists and is properly organized.
"""

import os
import pytest
from pathlib import Path


class TestProjectStructure:
    """Test the 3-layer architecture directory structure."""
    
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_three_layer_architecture_exists(self):
        """Test that the three-layer architecture directories exist."""
        src_dir = self.project_root / "src"
        assert src_dir.exists(), "src directory must exist"
        assert src_dir.is_dir(), "src must be a directory"
        
        # Test API layer
        api_layer = src_dir / "api"
        assert api_layer.exists(), "API layer directory must exist"
        assert api_layer.is_dir(), "API layer must be a directory"
        
        # Test Core layer
        core_layer = src_dir / "core"
        assert core_layer.exists(), "Core layer directory must exist"
        assert core_layer.is_dir(), "Core layer must be a directory"
        
        # Test Data layer
        data_layer = src_dir / "data"
        assert data_layer.exists(), "Data layer directory must exist"
        assert data_layer.is_dir(), "Data layer must be a directory"
    
    def test_api_layer_structure(self):
        """Test API layer internal structure."""
        api_dir = self.project_root / "src" / "api"
        assert api_dir.exists(), "API layer must exist"
        
        # API layer should contain these subdirectories/files
        expected_api_structure = [
            "__init__.py",
            "client.py",           # CivitaiAPIClient
            "params.py",           # SearchParams, AdvancedFilters
            "cache.py",            # ResponseCache
            "rate_limiter.py"      # RateLimiter
        ]
        
        for item in expected_api_structure:
            item_path = api_dir / item
            assert item_path.exists(), f"API layer must contain {item}"
    
    def test_core_layer_structure(self):
        """Test Core layer internal structure."""
        core_dir = self.project_root / "src" / "core"
        assert core_dir.exists(), "Core layer must exist"
        
        # Core layer should contain these subdirectories
        expected_core_structure = [
            "__init__.py",
            "interfaces/",         # Abstract interfaces
            "search/",            # Search services
            "security/",          # Security management
            "download/",          # Download engine
            "memory/",            # Memory management
            "error/"              # Error handling
        ]
        
        for item in expected_core_structure:
            item_path = core_dir / item
            assert item_path.exists(), f"Core layer must contain {item}"
            
            if item.endswith("/"):
                assert item_path.is_dir(), f"{item} must be a directory"
    
    def test_data_layer_structure(self):
        """Test Data layer internal structure."""
        data_dir = self.project_root / "src" / "data"
        assert data_dir.exists(), "Data layer must exist"
        
        # Data layer should contain these subdirectories/files
        expected_data_structure = [
            "__init__.py",
            "database.py",        # Database Manager
            "history/",           # HistoryManager
            "export/",            # MultiFormatExporter
            "models.py"           # Data Models
        ]
        
        for item in expected_data_structure:
            item_path = data_dir / item
            assert item_path.exists(), f"Data layer must contain {item}"
            
            if item.endswith("/"):
                assert item_path.is_dir(), f"{item} must be a directory"
    
    def test_test_structure_exists(self):
        """Test that test directories are properly structured."""
        tests_dir = self.project_root / "tests"
        assert tests_dir.exists(), "tests directory must exist"
        assert tests_dir.is_dir(), "tests must be a directory"
        
        # Test subdirectories
        test_subdirs = ["unit", "integration", "e2e"]
        for subdir in test_subdirs:
            subdir_path = tests_dir / subdir
            assert subdir_path.exists(), f"tests/{subdir} directory must exist"
            assert subdir_path.is_dir(), f"tests/{subdir} must be a directory"
    
    def test_config_and_docs_structure(self):
        """Test configuration and documentation structure."""
        # Test config directory
        config_dir = self.project_root / "config"
        assert config_dir.exists(), "config directory must exist"
        
        # Test docs directory
        docs_dir = self.project_root / "docs"
        assert docs_dir.exists(), "docs directory must exist"
        
    def test_init_files_exist(self):
        """Test that all necessary __init__.py files exist for proper package structure."""
        init_files = [
            "src/__init__.py",
            "src/api/__init__.py",
            "src/core/__init__.py",
            "src/core/interfaces/__init__.py",
            "src/core/search/__init__.py",
            "src/core/security/__init__.py",
            "src/core/download/__init__.py",
            "src/core/memory/__init__.py",
            "src/core/error/__init__.py",
            "src/data/__init__.py",
            "src/data/history/__init__.py",
            "src/data/export/__init__.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py",
            "tests/e2e/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = self.project_root / init_file
            assert init_path.exists(), f"{init_file} must exist for proper package structure"
            assert init_path.is_file(), f"{init_file} must be a file"
    
    def test_layer_separation_compliance(self):
        """Test that the 3-layer architecture maintains proper separation."""
        # API layer should only depend on external services, not core or data
        # Core layer should only depend on API layer, not data layer directly
        # Data layer should be independent and used by core layer
        
        # This is a structural test - actual dependency analysis would require
        # parsing import statements, but we test the directory structure compliance
        
        api_dir = self.project_root / "src" / "api"
        core_dir = self.project_root / "src" / "core"
        data_dir = self.project_root / "src" / "data"
        
        # All layers must exist and be properly separated
        assert api_dir.exists() and core_dir.exists() and data_dir.exists()
        
        # Each layer should have its own __init__.py
        assert (api_dir / "__init__.py").exists()
        assert (core_dir / "__init__.py").exists()
        assert (data_dir / "__init__.py").exists()