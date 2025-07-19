#!/usr/bin/env python3
"""
Test script to verify the Python virtual environment setup.
"""

import sys
import importlib
import platform

def test_python_version():
    """Test Python version."""
    print(f"🐍 Python version: {sys.version}")
    print(f"🐍 Python executable: {sys.executable}")
    
    if sys.version_info >= (3, 8):
        print("✅ Python version is compatible (3.8+)")
    else:
        print("❌ Python version is too old (need 3.8+)")

def test_dependencies():
    """Test if key dependencies are installed."""
    dependencies = [
        'aiohttp', 'requests', 'click', 'pydantic', 
        'yaml', 'pandas', 'pytest', 'rich'
    ]
    
    print("\n📦 Testing dependencies:")
    for dep in dependencies:
        try:
            if dep == 'yaml':
                module = importlib.import_module('yaml')
            else:
                module = importlib.import_module(dep)
            version = getattr(module, '__version__', 'unknown')
            print(f"  ✅ {dep}: {version}")
        except ImportError:
            print(f"  ❌ {dep}: not found")

def test_system_info():
    """Display system information."""
    print(f"\n💻 System information:")
    print(f"  Platform: {platform.platform()}")
    print(f"  Architecture: {platform.architecture()}")
    print(f"  Machine: {platform.machine()}")

def main():
    """Main test function."""
    print("🔍 CivitAI Tools - Environment Test")
    print("=" * 50)
    
    test_python_version()
    test_dependencies()
    test_system_info()
    
    print("\n🎉 Environment test completed!")

if __name__ == "__main__":
    main()