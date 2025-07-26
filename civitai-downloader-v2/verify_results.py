#!/usr/bin/env python3
"""Verify test results: check duplicates and category classification accuracy."""

import sys
import asyncio
sys.path.append('.')

from src.cli.main import cli_context
from src.core.stream import StreamingSearchEngine, IntermediateFileManager

async def analyze_session_results(session_id: str, expected_category: str):
    """Analyze session results for duplicates and classification accuracy."""
    
    # Initialize components
    intermediate_manager = IntermediateFileManager()
    streaming_engine = StreamingSearchEngine(None, intermediate_manager)
    
    print(f"\n🔍 Analyzing session: {session_id}")
    print(f"📋 Expected category: {expected_category}")
    print("=" * 60)
    
    # Collect all models
    all_models = []
    model_ids = set()
    category_counts = {}
    duplicates = []
    classification_errors = []
    
    async for batch in streaming_engine.get_processed_models_stream(session_id):
        for model in batch:
            model_id = model.get('id')
            model_name = model.get('name', 'Unknown')
            
            # Check for ID duplicates
            if model_id in model_ids:
                duplicates.append({
                    'id': model_id,
                    'name': model_name
                })
            else:
                model_ids.add(model_id)
            
            # Get category classification
            processing = model.get('_processing', {})
            primary_category = processing.get('primary_category', 'unknown')
            all_categories = processing.get('all_categories', [])
            
            # Count categories
            category_counts[primary_category] = category_counts.get(primary_category, 0) + 1
            
            # Check classification accuracy
            if primary_category != expected_category:
                # Verify if this is truly an error by checking original tags
                original_tags = model.get('tags', [])
                tag_names = []
                for tag in original_tags:
                    if isinstance(tag, dict):
                        tag_names.append(tag.get('name', '').lower())
                    else:
                        tag_names.append(str(tag).lower())
                
                classification_errors.append({
                    'id': model_id,
                    'name': model_name,
                    'classified_as': primary_category,
                    'expected': expected_category,
                    'all_categories': all_categories,
                    'original_tags': tag_names[:5],  # First 5 tags for analysis
                    'tag_order_check': {
                        'expected_position': tag_names.index(expected_category) if expected_category in tag_names else -1,
                        'classified_position': tag_names.index(primary_category) if primary_category in tag_names else -1
                    }
                })
            
            all_models.append(model)
    
    # Results
    total_models = len(all_models)
    unique_models = len(model_ids)
    duplicate_count = len(duplicates)
    correct_classifications = category_counts.get(expected_category, 0)
    classification_accuracy = (correct_classifications / total_models * 100) if total_models > 0 else 0
    
    print("📊 **DUPLICATE CHECK RESULTS**")
    print(f"   Total models: {total_models}")
    print(f"   Unique models: {unique_models}")
    print(f"   Duplicates found: {duplicate_count}")
    
    if duplicates:
        print("\n❌ **DUPLICATE MODELS FOUND:**")
        for i, dup in enumerate(duplicates[:5], 1):  # Show first 5
            print(f"   {i}. ID: {dup['id']} - {dup['name']}")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")
    else:
        print("✅ No duplicates found!")
    
    print("\n📊 **CLASSIFICATION RESULTS**")
    print(f"   Target category: {expected_category}")
    print(f"   Correct classifications: {correct_classifications}/{total_models} ({classification_accuracy:.1f}%)")
    
    print(f"\n📈 **CATEGORY DISTRIBUTION:**")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_models) * 100
        indicator = "✅" if category == expected_category else "⚠️"
        print(f"   {indicator} {category}: {count} ({percentage:.1f}%)")
    
    if classification_errors:
        print(f"\n⚠️ **CLASSIFICATION ERRORS FOUND:** {len(classification_errors)}")
        print("   First 5 misclassified models:")
        for i, error in enumerate(classification_errors[:5], 1):
            expected_pos = error['tag_order_check']['expected_position']
            classified_pos = error['tag_order_check']['classified_position']
            tag_analysis = f"Expected@{expected_pos}, Got@{classified_pos}" if expected_pos >= 0 and classified_pos >= 0 else "Tag order issue"
            
            print(f"   {i}. {error['name']}")
            print(f"      Expected: {error['expected']}, Got: {error['classified_as']}")
            print(f"      Tag analysis: {tag_analysis}")
            print(f"      Tags: {error['original_tags']}")
            print()
        
        if len(classification_errors) > 5:
            print(f"   ... and {len(classification_errors) - 5} more errors")
    else:
        print(f"✅ All models correctly classified!")
    
    return {
        'session_id': session_id,
        'expected_category': expected_category,
        'total_models': total_models,
        'unique_models': unique_models,
        'duplicates': duplicate_count,
        'correct_classifications': correct_classifications,
        'classification_accuracy': classification_accuracy,
        'category_distribution': category_counts,
        'classification_errors': len(classification_errors),
        'error_details': classification_errors[:10]  # Keep top 10 for analysis
    }

async def main():
    """Main verification function."""
    print("🔍 RESULTS VERIFICATION - Duplicate Check & Classification Analysis")
    print("=" * 80)
    
    # Initialize CLI context  
    await cli_context.initialize()
    
    # Session IDs from the tests
    style_session = "search_20250726_163851_2b1be2d6"  # Style 202 models
    concept_session = "search_20250726_164123_c79cf09f"  # Concept 200 models
    
    # Analyze both sessions
    style_results = await analyze_session_results(style_session, "style")
    concept_results = await analyze_session_results(concept_session, "concept")
    
    # Overall summary
    print(f"\n{'='*80}")
    print("📋 **OVERALL SUMMARY**")
    print(f"{'='*80}")
    
    total_models = style_results['total_models'] + concept_results['total_models']
    total_unique = style_results['unique_models'] + concept_results['unique_models']
    total_duplicates = style_results['duplicates'] + concept_results['duplicates']
    
    print(f"📊 Combined totals:")
    print(f"   Total models: {total_models}")
    print(f"   Unique models: {total_unique}")
    print(f"   Total duplicates: {total_duplicates}")
    
    style_accuracy = style_results['classification_accuracy']
    concept_accuracy = concept_results['classification_accuracy']
    overall_accuracy = (style_results['correct_classifications'] + concept_results['correct_classifications']) / total_models * 100
    
    print(f"\n🎯 Classification accuracy:")
    print(f"   Style: {style_accuracy:.1f}%")
    print(f"   Concept: {concept_accuracy:.1f}%") 
    print(f"   Overall: {overall_accuracy:.1f}%")
    
    # Final verdict
    if total_duplicates == 0 and style_accuracy >= 95 and concept_accuracy >= 95:
        print(f"\n✅ **VERIFICATION PASSED**")
        print(f"   - No duplicates found")
        print(f"   - High classification accuracy (>95%)")
    else:
        print(f"\n❌ **VERIFICATION ISSUES FOUND**")
        if total_duplicates > 0:
            print(f"   - {total_duplicates} duplicate models found")
        if style_accuracy < 95 or concept_accuracy < 95:
            print(f"   - Classification accuracy below 95%")
    
    return {
        'style': style_results,
        'concept': concept_results,
        'overall': {
            'total_models': total_models,
            'total_unique': total_unique, 
            'total_duplicates': total_duplicates,
            'overall_accuracy': overall_accuracy
        }
    }

if __name__ == "__main__":
    results = asyncio.run(main())