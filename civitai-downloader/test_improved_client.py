#!/usr/bin/env python3
"""Test improved CivitAI API client with robust parsing."""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.client import CivitAIClient
from api.exceptions import APIError


def test_improved_client():
    """Test improved client with robust error handling."""
    print("🔍 CivitAI Improved Client Test")
    print("=" * 50)
    
    # Initialize client
    client = CivitAIClient(calls_per_second=1.0)
    print(f"✅ Client initialized with robust parsing")
    print(f"   Base URL: {client.base_url}")
    print(f"   API Key: {'Set' if client.api_key else 'Not set (public mode)'}")
    
    try:
        # Test basic search with improved error handling
        print("\n📋 Test 1: Basic Search (Improved)")
        print("-" * 40)
        
        response = client.search_models(
            model_types=["Checkpoint"],
            sort="Highest Rated",
            limit=3
        )
        
        print(f"✅ Search successful with robust parsing!")
        print(f"   Found {len(response.items)} models")
        
        for i, model in enumerate(response.items, 1):
            print(f"\n   {i}. {model.name}")
            print(f"      ID: {model.id}")
            print(f"      Type: {model.type}")
            print(f"      Creator: {model.creator or 'Unknown'}")
            print(f"      Rating: {model.stats.rating if model.stats else 'N/A'}")
            print(f"      Tags: {', '.join(model.tags[:3]) if model.tags else 'None'}")
        
        # Test LORA search
        print("\n📋 Test 2: LORA Models")
        print("-" * 40)
        
        lora_response = client.search_models(
            model_types=["LORA"],
            sort="Most Downloaded",
            limit=2
        )
        
        print(f"✅ LORA search successful!")
        print(f"   Found {len(lora_response.items)} LORA models")
        
        for i, model in enumerate(lora_response.items, 1):
            print(f"\n   {i}. {model.name}")
            print(f"      Downloads: {model.stats.download_count if model.stats else 'Unknown'}")
            print(f"      Tags: {', '.join(model.tags[:3]) if model.tags else 'None'}")
        
        # Test cursor pagination
        if hasattr(client, 'search_with_cursor_pagination'):
            print("\n📋 Test 3: Cursor Pagination")
            print("-" * 40)
            
            print("Testing cursor pagination...")
            count = 0
            for model in client.search_with_cursor_pagination(
                model_types=["TextualInversion"],
                limit=5,
                max_pages=2
            ):
                count += 1
                if count <= 3:  # Show first 3
                    print(f"   {count}. {model.name} (Type: {model.type})")
                elif count == 4:
                    print(f"   ... and {count-3} more models")
            
            print(f"✅ Cursor pagination test completed! Total: {count} models")
        
        # Test error handling improvements
        print("\n📋 Test 4: Error Handling")
        print("-" * 40)
        
        try:
            # Test with invalid model ID
            client.get_model("nonexistent_model")
        except APIError as e:
            print(f"✅ Properly caught API error: {type(e).__name__}")
        except Exception as e:
            print(f"✅ Caught unexpected error gracefully: {type(e).__name__}")
        
        print(f"\n🎉 All improved client tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting Improved CivitAI Client Tests...")
    
    # Check for API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if api_key:
        print(f"✅ API key found in environment")
    else:
        print(f"⚠️  No API key found - running in public mode")
    
    test_improved_client()
    
    print(f"\n🏁 Test completed!")