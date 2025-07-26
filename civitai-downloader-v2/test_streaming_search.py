#!/usr/bin/env python3
"""Test streaming search functionality."""

import sys
import asyncio
sys.path.append('.')

from src.cli.main import cli_context
from src.core.search.advanced_search import AdvancedSearchParams, NSFWFilter
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def test_streaming_search():
    # Initialize CLI context
    await cli_context.initialize()
    
    # Create streaming components
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(cli_context.search_engine, intermediate_manager)
    
    # Search parameters
    search_params = AdvancedSearchParams(
        query='/',
        model_types=['LORA'],
        base_model='Illustrious',
        nsfw_filter=NSFWFilter.SFW_ONLY,
        limit=10
    )
    
    print("Testing streaming search with intermediate files...")
    print("=" * 60)
    
    try:
        # Execute streaming search
        session_id, summary = await streaming_engine.streaming_search_with_recovery(
            search_params, batch_size=5
        )
        
        print("\n✅ Search completed successfully!")
        print(f"Session ID: {session_id}")
        print(f"Summary: {summary}")
        
        # Test stream reading
        print("\n📖 Reading processed models...")
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
        
        print("\n🧹 Cleaning up session...")
        streaming_engine.cleanup_session(session_id, keep_final=False)
        print("✅ Cleanup completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Run test
asyncio.run(test_streaming_search())