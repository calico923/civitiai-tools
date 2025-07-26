#!/usr/bin/env python3
"""Test the fixed limit behavior with a small test."""

import sys
import asyncio
sys.path.append('.')

from src.cli.main import cli_context
from src.core.search.advanced_search import AdvancedSearchParams, NSFWFilter, ModelCategory
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def test_limit_fix():
    """Test that limit behavior is fixed."""
    print("Testing fixed limit behavior...")
    print("=" * 60)
    
    # Initialize CLI context
    await cli_context.initialize()
    
    # Create streaming components
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(cli_context.search_engine, intermediate_manager)
    
    # Test with smaller target first (20 style models)
    search_params = AdvancedSearchParams(
        query='/',
        model_types=['LORA'],
        base_model='Illustrious',
        categories=[ModelCategory('style')],
        nsfw_filter=NSFWFilter.SFW_ONLY,
        limit=20  # Small target for testing
    )
    
    print(f"Target: {search_params.limit} models")
    print("Starting streaming search...")
    
    try:
        # Execute streaming search
        session_id, summary = await streaming_engine.streaming_search_with_recovery(
            search_params, batch_size=5  # Small batch size for testing
        )
        
        print(f"\n✅ Search completed!")
        print(f"📊 Raw models: {summary['raw_models']}")
        print(f"🔍 Filtered models: {summary['filtered_models']}")
        print(f"⚙️  Processed models: {summary['processed_models']}")
        
        # Check if we got the expected number
        expected = search_params.limit
        actual = summary['processed_models']
        
        if actual >= expected:
            print(f"✅ SUCCESS: Got {actual} models (>= {expected} target)")
        else:
            print(f"❌ FAILED: Got only {actual} models (< {expected} target)")
            
        # Show first few models
        print(f"\n📋 First few models:")
        count = 0
        async for batch in streaming_engine.get_processed_models_stream(session_id):
            for model in batch:
                count += 1
                model_name = model.get('name', 'Unknown')
                processing = model.get('_processing', {})
                primary_cat = processing.get('primary_category', 'unknown')
                
                print(f"  {count}. {model_name} → {primary_cat}")
                
                if count >= 5:  # Show first 5 only
                    break
            if count >= 5:
                break
        
        # Cleanup
        streaming_engine.cleanup_session(session_id, keep_final=False)
        
        return actual >= expected
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run test
if __name__ == "__main__":
    success = asyncio.run(test_limit_fix())
    print(f"\nResult: {'✅ PASSED' if success else '❌ FAILED'}")