#!/usr/bin/env python3
"""Test streaming search for Style category - 200 models (FIXED VERSION)."""

import sys
import asyncio
import time
sys.path.append('.')

from src.cli.main import cli_context
from src.core.search.advanced_search import AdvancedSearchParams, NSFWFilter, ModelCategory
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def test_style_200():
    """Test streaming search for Style category - 200 models."""
    print("🎨 STYLE CATEGORY - 200 MODELS TEST (FIXED VERSION)")
    print("=" * 60)
    
    # Initialize CLI context
    await cli_context.initialize()
    
    # Create streaming components
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(cli_context.search_engine, intermediate_manager)
    
    # Search parameters for Style category
    search_params = AdvancedSearchParams(
        query='/',
        model_types=['LORA'],
        base_model='Illustrious',
        categories=[ModelCategory('style')],
        nsfw_filter=NSFWFilter.SFW_ONLY,
        limit=200  # Target: 200 models
    )
    
    print(f"🎯 Target: {search_params.limit} Style models")
    print(f"📋 Parameters: Illustrious + LORA + Style category")
    print("🚀 Starting streaming search...")
    
    start_time = time.time()
    
    try:
        # Execute streaming search
        session_id, summary = await streaming_engine.streaming_search_with_recovery(
            search_params, batch_size=50  # Larger batch size for efficiency
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ STYLE search completed!")
        print(f"⏱️  Time: {elapsed_time:.1f}s")
        print(f"📊 Raw models: {summary['raw_models']}")
        print(f"🔍 Filtered models: {summary['filtered_models']}")
        print(f"⚙️  Processed models: {summary['processed_models']}")
        
        # Check if target was met
        target = search_params.limit
        actual = summary['processed_models']
        
        if actual >= target:
            print(f"✅ SUCCESS: Got {actual} models (>= {target} target)")
            success = True
        else:
            print(f"❌ FAILED: Got only {actual} models (< {target} target)")
            success = False
        
        # Analyze category distribution
        print(f"\n📈 Category analysis:")
        category_counts = {}
        model_count = 0
        target_category_count = 0
        
        async for batch in streaming_engine.get_processed_models_stream(session_id):
            for model in batch:
                model_count += 1
                processing = model.get('_processing', {})
                primary_cat = processing.get('primary_category', 'unknown')
                all_cats = processing.get('all_categories', [])
                
                # Count primary categories
                category_counts[primary_cat] = category_counts.get(primary_cat, 0) + 1
                
                # Count target category matches
                if primary_cat == 'style':
                    target_category_count += 1
                
                # Show first 10 examples
                if model_count <= 10:
                    model_name = model.get('name', 'Unknown')
                    print(f"  {model_count}. {model_name} → {primary_cat} {all_cats}")
        
        print(f"\n📊 Category distribution:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / model_count) * 100
            print(f"  {cat}: {count} ({percentage:.1f}%)")
        
        accuracy = (target_category_count / model_count) * 100 if model_count > 0 else 0
        print(f"\n🎯 Style category accuracy: {target_category_count}/{model_count} ({accuracy:.1f}%)")
        
        # File information
        files_info = summary.get('files', {})
        for file_type, info in files_info.items():
            print(f"📄 {file_type}: {info['size_mb']:.2f}MB - {info['path']}")
        
        # Keep session for analysis
        print(f"\n💾 Session kept for analysis: {session_id}")
        print("✅ Test completed!")
        
        return {
            'success': success,
            'session_id': session_id,
            'target': target,
            'actual': actual,
            'accuracy': accuracy,
            'elapsed_time': elapsed_time,
            'category_distribution': category_counts,
            'summary': summary
        }
        
    except Exception as e:
        print(f"❌ Error in Style test: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_style_200())
    print(f"\n🏁 Final Result: {'✅ PASSED' if result.get('success', False) else '❌ FAILED'}")