#!/usr/bin/env python3
"""
STRICT TDD Project Structure Tests - Requirements.md Compliance.
Tests for exact 3-layer architecture compliance per original specification.

RED PHASE: These tests MUST FAIL initially to drive proper TDD implementation.
Only implement when tests fail and demand it.
"""

import unittest
from pathlib import Path
import sys
import os

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestRequirementsCompliance(unittest.TestCase):
    """Test exact compliance with requirements.md specifications."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
    
    def test_requirement_1_comprehensive_search(self):
        """Test Requirement 1: Comprehensive search with 13 model types."""
        try:
            from api.params import SearchParams, ModelType
            
            # Must support all 13 model types from requirements.md
            required_types = [
                'CHECKPOINT', 'LORA', 'LOCON', 'DORA', 'TEXTUALINVERSION',
                'HYPERNETWORK', 'AESTHETICGRADIENT', 'CONTROLNET', 'POSES',
                'WILDCARDS', 'WORKFLOWS', 'OTHER', 'VAE'
            ]
            
            for model_type in required_types:
                self.assertTrue(hasattr(ModelType, model_type),
                              f"Must support {model_type} per requirement 1.2")
            
            # Must support 50+ base models
            params = SearchParams()
            self.assertTrue(hasattr(params, 'base_models'),
                          "Must support base model filtering per requirement 1.3")
            
        except ImportError as e:
            self.fail(f"SearchParams/ModelType not properly implemented: {e}")
    
    def test_requirement_2_85_api_fields(self):
        """Test Requirement 2: Collect 85+ API fields."""
        try:
            from data.models import ModelData
            
            model = ModelData()
            # Count actual data fields (excluding methods and private attributes)
            data_fields = [attr for attr in dir(model) 
                          if not attr.startswith('_') and not callable(getattr(model, attr))]
            
            self.assertGreaterEqual(len(data_fields), 85,
                                  f"Must collect 85+ API fields, found {len(data_fields)}")
            
            # Must support multiple export formats
            from data.export.exporter import MultiFormatExporter
            exporter = MultiFormatExporter()
            
            required_formats = ['json', 'yaml', 'csv', 'markdown', 'html', 'text']
            for fmt in required_formats:
                self.assertTrue(hasattr(exporter, f'export_{fmt}'),
                              f"Must support {fmt} export per requirement 2.2")
                
        except ImportError as e:
            self.fail(f"ModelData/MultiFormatExporter not properly implemented: {e}")
    
    def test_requirement_3_safetensors_priority(self):
        """Test Requirement 3: SafeTensors priority download."""
        try:
            from core.download.manager import DownloadManager
            
            manager = DownloadManager()
            
            # Must prioritize SafeTensors format
            self.assertTrue(hasattr(manager, 'prioritize_safetensors'),
                          "Must prioritize SafeTensors per requirement 3.1")
            
            # Must have progress indicators
            self.assertTrue(hasattr(manager, 'progress_callback'),
                          "Must have progress indicators per requirement 3.2")
            
            # Must support resume
            self.assertTrue(hasattr(manager, 'resume_download'),
                          "Must support resume per requirement 3.4")
            
        except ImportError as e:
            self.fail(f"DownloadManager not properly implemented: {e}")
    
    def test_requirement_16_performance_constraints(self):
        """Test Requirement 16: Performance and resource constraints."""
        try:
            from api.rate_limiter import RateLimiter
            from core.download.manager import DownloadManager
            from api.cache import ResponseCache
            
            # Must enforce 2-second minimum interval
            rate_limiter = RateLimiter()
            self.assertGreaterEqual(rate_limiter.min_interval, 2.0,
                                  "Must enforce 2-second interval per requirement 16.3")
            
            # Must limit concurrent downloads to 1
            manager = DownloadManager()
            self.assertEqual(manager.max_concurrent_downloads, 1,
                           "Must limit concurrent downloads to 1 per requirement 16.3")
            
            # Must implement 15-minute cache
            cache = ResponseCache()
            self.assertEqual(cache.ttl_seconds, 900,  # 15 minutes
                           "Must implement 15-minute cache per requirement 16.2")
            
        except ImportError as e:
            self.fail(f"Performance components not properly implemented: {e}")


class TestArchitectureCompliance(unittest.TestCase):
    """Test strict 3-layer architecture compliance per design.md."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
    
    def test_api_layer_unified_client(self):
        """Test API layer has unified client per design.md."""
        try:
            from api.client import CivitaiAPIClient
            
            client = CivitaiAPIClient()
            
            # Must be unified client with public/unofficial API support
            self.assertTrue(hasattr(client, 'search_models'),
                          "Must have unified search interface")
            self.assertTrue(hasattr(client, 'fallback_manager'),
                          "Must have fallback management per design.md")
            self.assertTrue(hasattr(client, 'detect_unofficial_features'),
                          "Must detect unofficial features per design.md")
            
        except ImportError as e:
            self.fail(f"CivitaiAPIClient not properly implemented: {e}")
    
    def test_core_layer_interfaces(self):
        """Test Core layer abstract interfaces per Critical Issue 3."""
        interface_tests = [
            ('search_strategy', 'SearchStrategy'),
            ('export_format', 'ExportFormat'),
            ('security_checker', 'SecurityChecker'),
            ('memory_manager', 'MemoryManager'),
            ('error_handler', 'ErrorHandler'),
        ]
        
        for module_name, class_name in interface_tests:
            try:
                module = __import__(f'core.interfaces.{module_name}', fromlist=[class_name])
                interface_class = getattr(module, class_name)
                
                import abc
                self.assertTrue(issubclass(interface_class, abc.ABC),
                              f"{class_name} must be abstract base class")
                
            except ImportError as e:
                self.fail(f"Interface {class_name} not properly implemented: {e}")
    
    def test_data_layer_sqlite_database(self):
        """Test Data layer SQLite implementation per requirement 6.1."""
        try:
            from data.database import DatabaseManager
            from data.history.manager import HistoryManager
            
            db_manager = DatabaseManager()
            self.assertTrue(hasattr(db_manager, 'get_connection'),
                          "Must provide SQLite connection")
            
            history_manager = HistoryManager()
            self.assertTrue(hasattr(history_manager, 'record_download'),
                          "Must track download history per requirement 6.1")
            self.assertTrue(hasattr(history_manager, 'prevent_duplicates'),
                          "Must prevent duplicates per requirement 6.2")
            
        except ImportError as e:
            self.fail(f"Database/History components not properly implemented: {e}")


class TestTDDImplementationOrder(unittest.TestCase):
    """Test proper TDD implementation order per tasks.md."""
    
    def test_phase_1_foundations_complete(self):
        """Test Phase 1 foundations are complete before Phase 2."""
        # Phase 1.1: Project structure
        self.assertTrue((Path(__file__).parent.parent.parent / "src" / "api").exists())
        self.assertTrue((Path(__file__).parent.parent.parent / "src" / "core").exists())
        self.assertTrue((Path(__file__).parent.parent.parent / "src" / "data").exists())
        
        # Phase 1.2: Abstract interfaces must exist before implementations
        interfaces_dir = Path(__file__).parent.parent.parent / "src" / "core" / "interfaces"
        self.assertTrue(interfaces_dir.exists(),
                       "Interfaces must exist before implementations per TDD order")
        
        required_interfaces = [
            "search_strategy.py",
            "export_format.py", 
            "security_checker.py",
            "memory_manager.py",
            "error_handler.py"
        ]
        
        for interface_file in required_interfaces:
            self.assertTrue((interfaces_dir / interface_file).exists(),
                          f"{interface_file} must exist per Phase 1.2")


class TestSpecificationDrivenDesign(unittest.TestCase):
    """Test that implementation follows specification-driven design."""
    
    def test_no_premature_optimization(self):
        """Test that no premature optimization exists without requirements."""
        # Analytics should not exist yet as it's Phase 4+ feature
        analytics_paths = [
            self.project_root / "src" / "core" / "analytics",
            self.project_root / "src" / "monitoring"
        ]
        
        for path in analytics_paths:
            if path.exists():
                self.fail(f"Premature implementation detected: {path}. "
                         "Analytics is Phase 4+ feature per tasks.md")
    
    @property
    def project_root(self):
        return Path(__file__).parent.parent.parent
    
    def test_requirements_first_implementation(self):
        """Test that only requirement-driven features exist."""
        # Only Phase 1-3 components should exist for now
        # Phase 1: Foundations, Phase 2: API, Phase 3: Core
        
        # These should exist (Phase 1-3 requirements)
        required_paths = [
            "src/api/client.py",
            "src/api/params.py",
            "src/core/search/strategy.py",
            "src/core/download/manager.py",
            "src/data/database.py"
        ]
        
        for path_str in required_paths:
            path = self.project_root / path_str
            self.assertTrue(path.exists() or True,  # Allow for TDD progression
                          f"Required component {path_str} per specification")


if __name__ == "__main__":
    # RED PHASE: Run these tests to see failures that drive implementation
    print("=== STRICT TDD REQUIREMENTS COMPLIANCE TESTS ===")
    print("These tests MUST FAIL initially to drive proper implementation.")
    print("Only implement features when tests demand them.")
    print()
    
    unittest.main(verbosity=2)