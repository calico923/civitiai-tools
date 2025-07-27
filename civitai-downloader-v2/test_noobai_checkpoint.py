#!/usr/bin/env python3
"""Test NoobAI Checkpoint models search with streaming."""

import sys
import asyncio
import time
sys.path.append('.')

from src.cli.main import cli_context
from src.core.stream import StreamingSearchEngine, IntermediateFileManager
from src.core.search.advanced_search import AdvancedSearchParams

async def test_noobai_checkpoint_search():
    """Test NoobAI Checkpoint search with streaming."""
    print("\n" + "="*60)
    print("🤖 Testing NoobAI + Checkpoint + BaseModel")
    print("="*60)
    
    # Initialize CLI context
    await cli_context.initialize()
    
    # Create streaming search engine
    streaming_engine = StreamingSearchEngine(
        cli_context.search_engine,
        IntermediateFileManager()
    )
    
    # Setup search parameters exactly as requested
    from src.core.search.advanced_search import NSFWFilter
    search_params = AdvancedSearchParams(
        model_types=["Checkpoint"],
        base_model="NoobAI", 
        nsfw_filter=NSFWFilter.SFW_ONLY,
        limit=200
    )
    
    print(f"🎯 Target: {search_params.limit} models")
    print(f"📋 Parameters: baseModel=NoobAI + modelType=Checkpoint")
    print("🚀 Starting streaming search...")
    
    start_time = time.time()
    
    try:
        # Execute streaming search with recovery
        session_id, summary = await streaming_engine.streaming_search_with_recovery(
            search_params, batch_size=50
        )
        
        elapsed_time = time.time() - start_time
        
        print("\n✅ Search completed!")
        print(f"⏱️  Time: {elapsed_time:.1f}s")
        print(f"📊 Raw models: {summary['raw_models']}")
        print(f"🔍 Filtered models: {summary['filtered_models']}")
        print(f"⚙️  Processed models: {summary['processed_models']}")
        
        # Check results
        target = search_params.limit
        actual = summary['processed_models']
        success = actual >= target
        
        if success:
            print(f"✅ SUCCESS: Got {actual} models (>= {target} target)")
        else:
            print(f"❌ FAILED: Got only {actual} models (< {target} target)")
        
        # Analyze category distribution
        print("\n📈 Category analysis:")
        category_counts = {}
        model_count = 0
        checkpoint_count = 0
        base_model_count = 0
        
        async for batch in streaming_engine.get_processed_models_stream(session_id):
            for model in batch:
                model_count += 1
                
                # Check type
                model_type = model.get('type', 'Unknown')
                if model_type == 'Checkpoint':
                    checkpoint_count += 1
                
                # Check base model in versions
                versions = model.get('modelVersions', [])
                for version in versions:
                    if version.get('baseModel') == 'BaseModel':
                        base_model_count += 1
                        break
                
                # Count categories
                processing = model.get('_processing', {})
                primary_cat = processing.get('primary_category', 'unknown')
                category_counts[primary_cat] = category_counts.get(primary_cat, 0) + 1
                
                # Show first 10 models
                if model_count <= 10:
                    model_name = model.get('name', 'Unknown')
                    all_cats = processing.get('all_categories', [])
                    print(f"  {model_count}. {model_name} → Type: {model_type}, Categories: {all_cats}")
        
        print("\n📊 Analysis results:")
        print(f"  Total models: {model_count}")
        if model_count > 0:
            print(f"  Checkpoint type: {checkpoint_count} ({(checkpoint_count/model_count)*100:.1f}%)")
            print(f"  BaseModel versions: {base_model_count} ({(base_model_count/model_count)*100:.1f}%)")
        else:
            print("  No models found to analyze")
        
        print("\n📊 Category distribution:")
        if model_count > 0:
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / model_count) * 100
                print(f"  {cat}: {count} ({percentage:.1f}%)")
        else:
            print("  No categories to analyze")
        
        # Show session info
        session_info = streaming_engine.intermediate_manager.get_session_summary(session_id)
        print("\n💾 Session files:")
        for file_type, info in session_info['files'].items():
            print(f"  📄 {file_type}: {info['size_mb']:.2f}MB")
        
        # Cleanup
        print("\n🧹 Cleaning up session...")
        streaming_engine.cleanup_session(session_id, keep_final=True)
        print(f"💾 Session files kept for analysis: {session_id}")
        
        return {
            'success': success,
            'total_models': model_count,
            'checkpoint_count': checkpoint_count,
            'base_model_count': base_model_count,
            'elapsed_time': elapsed_time,
            'session_id': session_id
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

# Run the test
if __name__ == "__main__":
    asyncio.run(test_noobai_checkpoint_search())