#!/usr/bin/env python3
"""Cross-session duplicate check between Style and Concept results."""

import sys
import asyncio
sys.path.append('.')

from src.cli.main import cli_context
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def check_cross_session_duplicates():
    """Check for duplicates between Style and Concept sessions."""
    
    print("🔍 CROSS-SESSION DUPLICATE CHECK")
    print("=" * 60)
    
    # Initialize components
    await cli_context.initialize()
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(None, intermediate_manager)
    
    # Session IDs
    style_session = "search_20250726_163851_2b1be2d6"  # Style 202 models
    concept_session = "search_20250726_164123_c79cf09f"  # Concept 201 models
    
    # Collect Style model IDs
    print("📋 Collecting Style model IDs...")
    style_ids = set()
    style_models = {}
    
    async for batch in streaming_engine.get_processed_models_stream(style_session):
        for model in batch:
            model_id = model.get('id')
            model_name = model.get('name', 'Unknown')
            style_ids.add(model_id)
            style_models[model_id] = {
                'name': model_name,
                'category': model.get('_processing', {}).get('primary_category', 'unknown')
            }
    
    # Collect Concept model IDs
    print("📋 Collecting Concept model IDs...")
    concept_ids = set()
    concept_models = {}
    
    async for batch in streaming_engine.get_processed_models_stream(concept_session):
        for model in batch:
            model_id = model.get('id')
            model_name = model.get('name', 'Unknown')
            concept_ids.add(model_id)
            concept_models[model_id] = {
                'name': model_name,
                'category': model.get('_processing', {}).get('primary_category', 'unknown')
            }
    
    # Find cross-session duplicates
    cross_duplicates = style_ids.intersection(concept_ids)
    
    print("\n📊 **CROSS-SESSION ANALYSIS**")
    print(f"   Style models: {len(style_ids)}")
    print(f"   Concept models: {len(concept_ids)}")
    print(f"   Cross-session duplicates: {len(cross_duplicates)}")
    
    if cross_duplicates:
        print("\n❌ **CROSS-SESSION DUPLICATES FOUND:**")
        for i, model_id in enumerate(list(cross_duplicates)[:10], 1):  # Show first 10
            style_info = style_models[model_id]
            concept_info = concept_models[model_id]
            print(f"   {i}. ID: {model_id}")
            print(f"      Name: {style_info['name']}")
            print(f"      Style classification: {style_info['category']}")
            print(f"      Concept classification: {concept_info['category']}")
            print()
        
        if len(cross_duplicates) > 10:
            print(f"   ... and {len(cross_duplicates) - 10} more")
        
        print(f"\n🔍 **ANALYSIS:**")
        print(f"   This suggests models with multiple category tags where:")
        print(f"   - Some were classified as 'style' (first tag)")
        print(f"   - Same models were also classified as 'concept' (first tag)")
        print(f"   This indicates potential issues with the API category filter")
        print(f"   or tag order inconsistency.")
        
    else:
        print("✅ No cross-session duplicates found!")
        print(f"   Each model appears in only one category, as expected.")
    
    # Additional analysis: Category tag verification
    if cross_duplicates:
        print(f"\n🔍 **DETAILED TAG ANALYSIS** (First 3 duplicates):")
        
        count = 0
        async for batch in streaming_engine.get_processed_models_stream(style_session):
            for model in batch:
                if count >= 3:
                    break
                model_id = model.get('id')
                if model_id in cross_duplicates:
                    count += 1
                    print(f"\n   Model {count}: {model.get('name')}")
                    print(f"   ID: {model_id}")
                    
                    # Check original tags
                    original_tags = model.get('tags', [])
                    tag_names = []
                    for tag in original_tags[:10]:  # First 10 tags
                        if isinstance(tag, dict):
                            tag_names.append(tag.get('name', '').lower())
                        else:
                            tag_names.append(str(tag).lower())
                    
                    style_pos = tag_names.index('style') if 'style' in tag_names else -1
                    concept_pos = tag_names.index('concept') if 'concept' in tag_names else -1
                    
                    print(f"   First 10 tags: {tag_names}")
                    print(f"   'style' position: {style_pos}")
                    print(f"   'concept' position: {concept_pos}")
                    
                    if style_pos >= 0 and concept_pos >= 0:
                        if style_pos < concept_pos:
                            print(f"   ✅ Should be classified as 'style' (appears first)")
                        else:
                            print(f"   ✅ Should be classified as 'concept' (appears first)")
                    else:
                        print(f"   ⚠️  Missing expected tags!")
    
    return len(cross_duplicates)

if __name__ == "__main__":
    duplicate_count = asyncio.run(check_cross_session_duplicates())
    
    print(f"\n{'='*60}")
    if duplicate_count == 0:
        print("✅ **CROSS-SESSION CHECK PASSED**")
        print("   No models appear in both Style and Concept results.")
        print("   Category classification is working correctly.")
    else:
        print("❌ **CROSS-SESSION ISSUES FOUND**")
        print(f"   {duplicate_count} models appear in both categories.")
        print("   This requires investigation of the classification logic.")