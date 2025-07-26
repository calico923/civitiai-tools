#!/usr/bin/env python3
"""Test streaming search with specific categories (style and concept)."""

import sys
import asyncio
import time
sys.path.append('.')

from src.cli.main import cli_context
from src.core.search.advanced_search import AdvancedSearchParams, NSFWFilter, ModelCategory
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def test_category_search(category_name: str, target_count: int = 200):
    """Test streaming search for specific category."""
    print(f"\n{'='*60}")
    print(f"Testing {category_name.upper()} category - Target: {target_count} models")
    print(f"{'='*60}")
    
    # Create streaming components
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(cli_context.search_engine, intermediate_manager)
    
    # Search parameters
    search_params = AdvancedSearchParams(
        query='/',
        model_types=['LORA'],
        base_model='Illustrious',
        categories=[ModelCategory(category_name.lower())],
        nsfw_filter=NSFWFilter.SFW_ONLY,
        limit=target_count
    )
    
    start_time = time.time()
    
    try:
        # Execute streaming search
        session_id, summary = await streaming_engine.streaming_search_with_recovery(
            search_params, batch_size=50
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ {category_name.upper()} search completed!")
        print(f"⏱️  Time: {elapsed_time:.1f}s")
        print(f"📊 Raw models: {summary['raw_models']}")
        print(f"🔍 Filtered models: {summary['filtered_models']}")
        print(f"⚙️  Processed models: {summary['processed_models']}")
        
        # Analyze category distribution
        print(f"\n📈 Category analysis for {category_name}:")
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
                if primary_cat == category_name.lower():
                    target_category_count += 1
                
                # Show first 10 examples
                if model_count <= 10:
                    model_name = model.get('name', 'Unknown')
                    print(f"  {model_count}. {model_name} → {primary_cat} {all_cats}")
        
        print(f"\n📊 Category distribution:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / model_count) * 100
            print(f"  {cat}: {count} ({percentage:.1f}%)")
        
        print(f"\n🎯 Target category '{category_name}' accuracy: {target_category_count}/{model_count} ({(target_category_count/model_count)*100:.1f}%)")
        
        # File size information
        files_info = summary.get('files', {})
        for file_type, info in files_info.items():
            print(f"📄 {file_type}: {info['size_mb']:.2f}MB - {info['path']}")
        
        # Optional: Keep processed file for analysis
        print(f"\n💾 Session files kept for analysis: {session_id}")
        print("🧹 Use streaming_engine.cleanup_session() to clean up later")
        
        return {
            'session_id': session_id,
            'category': category_name,
            'total_models': model_count,
            'target_category_count': target_category_count,
            'accuracy': target_category_count / model_count if model_count > 0 else 0,
            'category_distribution': category_counts,
            'elapsed_time': elapsed_time,
            'summary': summary
        }
        
    except Exception as e:
        print(f"❌ Error in {category_name} search: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Run both category tests."""
    print("🚀 Starting large-scale category streaming tests...")
    
    # Initialize CLI context
    await cli_context.initialize()
    
    # Test 1: Style category
    print(f"\n🎨 Test 1: STYLE category")
    style_result = await test_category_search('style', 200)
    
    # Short break between tests
    print(f"\n⏸️  Waiting 3 seconds before next test...")
    await asyncio.sleep(3)
    
    # Test 2: Concept category  
    print(f"\n💡 Test 2: CONCEPT category")
    concept_result = await test_category_search('concept', 200)
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("📋 FINAL COMPARISON")
    print(f"{'='*60}")
    
    if style_result and concept_result:
        print(f"Style category:")
        print(f"  ✓ Models: {style_result['total_models']}")
        print(f"  ✓ Accuracy: {style_result['accuracy']:.1%}")
        print(f"  ✓ Time: {style_result['elapsed_time']:.1f}s")
        
        print(f"\nConcept category:")
        print(f"  ✓ Models: {concept_result['total_models']}")
        print(f"  ✓ Accuracy: {concept_result['accuracy']:.1%}")
        print(f"  ✓ Time: {concept_result['elapsed_time']:.1f}s")
        
        print(f"\n🏆 Better accuracy: {'Style' if style_result['accuracy'] > concept_result['accuracy'] else 'Concept'}")
        print(f"⚡ Faster: {'Style' if style_result['elapsed_time'] < concept_result['elapsed_time'] else 'Concept'}")

if __name__ == "__main__":
    asyncio.run(main())