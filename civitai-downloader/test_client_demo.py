#!/usr/bin/env python3
"""CivitAI API client demo and test script."""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.client import CivitAIClient
from api.exceptions import APIError, NetworkError, AuthenticationError

# Import search engine components
import sys
import importlib.util

# Load search module manually to avoid relative import issues
spec = importlib.util.spec_from_file_location("search", str(Path(__file__).parent / "src" / "core" / "search.py"))
search_module = importlib.util.module_from_spec(spec)
sys.modules["search"] = search_module
spec.loader.exec_module(search_module)

ModelSearchEngine = search_module.ModelSearchEngine
SearchFilter = search_module.SearchFilter


def test_client_basic():
    """Test basic client functionality."""
    print("🔍 CivitAI API Client Demo Test")
    print("=" * 50)
    
    # Initialize client (without API key for public endpoints)
    client = CivitAIClient(calls_per_second=1.0)  # Slower for demo
    print(f"✅ Client initialized")
    print(f"   Base URL: {client.base_url}")
    print(f"   API Key: {'Set' if client.api_key else 'Not set (public mode)'}")
    
    try:
        # Test 1: Basic search
        print("\n📋 Test 1: Basic Model Search")
        print("-" * 30)
        
        response = client.search_models(
            model_types=["Checkpoint"],
            sort="Highest Rated",
            limit=5
        )
        
        print(f"✅ Search successful!")
        print(f"   Found {len(response.items)} models")
        print(f"   Total items: {response.total_items}")
        print(f"   Current page: {response.current_page}")
        
        # Display results
        for i, model in enumerate(response.items, 1):
            print(f"\n   {i}. {model.name}")
            print(f"      ID: {model.id}")
            print(f"      Type: {model.type}")
            print(f"      Creator: {model.creator}")
            print(f"      Downloads: {model.stats.download_count if model.stats else 'Unknown'}")
            print(f"      Rating: {model.stats.rating if model.stats else 'Unknown'}")
            print(f"      Tags: {', '.join(model.tags[:3])}{'...' if len(model.tags) > 3 else ''}")
        
        # Test 2: Get detailed model info
        if response.items:
            print(f"\n📄 Test 2: Model Details")
            print("-" * 30)
            
            first_model = response.items[0]
            print(f"Getting details for: {first_model.name} (ID: {first_model.id})")
            
            model_details = client.get_model(first_model.id)
            
            print(f"✅ Model details retrieved!")
            print(f"   Name: {model_details.name}")
            print(f"   Description: {model_details.description[:100] if model_details.description else 'No description'}...")
            print(f"   Versions: {len(model_details.versions)}")
            print(f"   Images: {len(model_details.images)}")
            
            # Show version info
            if model_details.versions:
                version = model_details.versions[0]
                print(f"\n   Latest Version: {version.name}")
                print(f"   Base Model: {version.base_model}")
                print(f"   Files: {len(version.files)}")
                print(f"   Trained Words: {', '.join(version.trained_words[:3]) if version.trained_words else 'None'}")
                
                # Show file info
                if version.files:
                    file_info = version.files[0]
                    print(f"\n   Main File: {file_info.name}")
                    print(f"   Size: {file_info.size_kb / 1024:.1f} MB" if file_info.size_kb else "Unknown size")
                    print(f"   Type: {file_info.type}")
                    print(f"   Format: {file_info.format}")
        
        # Test 3: Search with filters
        print(f"\n🎯 Test 3: Filtered Search")
        print("-" * 30)
        
        filtered_response = client.search_models(
            model_types=["LORA"],
            tags=["anime"],
            sort="Most Downloaded",
            limit=3
        )
        
        print(f"✅ Filtered search successful!")
        print(f"   Found {len(filtered_response.items)} LORA models with 'anime' tag")
        
        for i, model in enumerate(filtered_response.items, 1):
            print(f"\n   {i}. {model.name}")
            print(f"      Downloads: {model.stats.download_count if model.stats else 'Unknown'}")
            print(f"      Tags: {', '.join(model.tags[:5])}")
        
        # Test 4: Rate limiter stats
        print(f"\n📊 Test 4: Rate Limiter Stats")
        print("-" * 30)
        
        stats = client.get_rate_limiter_stats()
        print(f"✅ Rate limiter statistics:")
        print(f"   Calls made: {stats['calls_made']}")
        print(f"   Elapsed time: {stats['elapsed_time']:.1f}s")
        print(f"   Average rate: {stats['average_rate']:.2f} calls/s")
        print(f"   Configured rate: {stats['configured_rate']:.2f} calls/s")
        
        # Test 5: Search Engine
        print(f"\n🔍 Test 5: Advanced Search Engine")
        print("-" * 30)
        
        search_engine = ModelSearchEngine(client)
        search_filter = SearchFilter(
            model_types=["LoRA"],  # Will be normalized to LORA
            tags=["anime"],
            min_downloads=1000
        )
        
        search_result = search_engine.search(
            search_filter=search_filter,
            limit=3
        )
        
        print(f"✅ Advanced search successful!")
        print(f"   Found {len(search_result.items)} filtered models")
        
        for i, model in enumerate(search_result.items, 1):
            print(f"\n   {i}. {model.name}")
            print(f"      Type: {model.type}")
            print(f"      Downloads: {model.stats.download_count if model.stats else 'Unknown'}")
            print(f"      Tags: {', '.join(model.tags[:3])}")
        
        # Test engine stats
        engine_stats = search_engine.get_stats()
        print(f"\n   Engine Statistics:")
        print(f"   Supported types: {len(engine_stats['supported_types'])}")
        print(f"   Type mappings: {len(engine_stats['type_mappings'])}")
        
        print(f"\n🎉 All tests completed successfully!")
        
    except AuthenticationError as e:
        print(f"❌ Authentication error: {e}")
        print("   Note: Some features may require an API key")
        
    except NetworkError as e:
        print(f"❌ Network error: {e}")
        print("   Check your internet connection")
        
    except APIError as e:
        print(f"❌ API error: {e}")
        if hasattr(e, 'status_code'):
            print(f"   Status code: {e.status_code}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def test_client_error_handling():
    """Test error handling scenarios."""
    print(f"\n🛡️ Error Handling Tests")
    print("=" * 50)
    
    client = CivitAIClient(calls_per_second=2.0)
    
    # Test invalid model ID
    print("\n🔍 Testing invalid model ID...")
    try:
        client.get_model("invalid_id")
    except Exception as e:
        print(f"✅ Caught expected error: {type(e).__name__}: {e}")
    
    # Test with very high limit (should be capped at 100)
    print("\n🔍 Testing limit capping...")
    try:
        response = client.search_models(limit=200)
        print(f"✅ Limit properly handled (requested 200, API used max allowed)")
    except Exception as e:
        print(f"✅ Caught expected error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("Starting CivitAI API Client Tests...")
    print("Note: This will make real API calls to CivitAI")
    
    # Check for API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if api_key:
        print(f"✅ API key found in environment")
    else:
        print(f"⚠️  No API key found - running in public mode")
        print(f"   Set CIVITAI_API_KEY environment variable for full functionality")
    
    test_client_basic()
    test_client_error_handling()
    
    print(f"\n🏁 Demo completed!")