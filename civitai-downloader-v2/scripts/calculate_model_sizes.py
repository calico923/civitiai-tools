#!/usr/bin/env python3
"""
Calculate total byte sizes of collected models by category
"""
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Tuple

def calculate_model_size(model: Dict[str, Any]) -> int:
    """Calculate total size of a model from its versions"""
    total_size = 0
    
    if 'modelVersions' in model and isinstance(model['modelVersions'], list):
        for version in model['modelVersions']:
            if isinstance(version, dict) and 'files' in version:
                for file_info in version.get('files', []):
                    if isinstance(file_info, dict) and 'sizeKB' in file_info:
                        size_kb = file_info.get('sizeKB', 0)
                        if isinstance(size_kb, (int, float)):
                            total_size += int(size_kb * 1024)  # Convert KB to bytes
    
    return total_size

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

def analyze_json_files():
    """Analyze JSON files for model sizes"""
    json_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search")
    
    categories = {
        'CHARACTER': 'character_models_category.json',
        'STYLE': 'style_models_category.json', 
        'CONCEPT': 'concept_models_category.json',
        'POSES': 'poses_models_category.json'
    }
    
    results = {}
    total_all_categories = 0
    
    print("📊 Analyzing model sizes from JSON files...\n")
    
    for category, filename in categories.items():
        file_path = json_dir / filename
        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"Processing {category}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            models = json.load(f)
        
        if not isinstance(models, list):
            print(f"  ⚠️  Invalid JSON format")
            continue
        
        total_bytes = 0
        model_count = 0
        size_distribution = {
            '< 100MB': 0,
            '100MB - 500MB': 0,
            '500MB - 1GB': 0,
            '1GB - 5GB': 0,
            '> 5GB': 0
        }
        
        largest_models = []  # (name, size, type)
        
        for model in models:
            if isinstance(model, dict):
                size = calculate_model_size(model)
                if size > 0:
                    total_bytes += size
                    model_count += 1
                    
                    # Size distribution
                    size_mb = size / (1024 * 1024)
                    if size_mb < 100:
                        size_distribution['< 100MB'] += 1
                    elif size_mb < 500:
                        size_distribution['100MB - 500MB'] += 1
                    elif size_mb < 1024:
                        size_distribution['500MB - 1GB'] += 1
                    elif size_mb < 5120:
                        size_distribution['1GB - 5GB'] += 1
                    else:
                        size_distribution['> 5GB'] += 1
                    
                    # Track largest models
                    model_info = (
                        model.get('name', 'Unknown'),
                        size,
                        model.get('type', 'Unknown')
                    )
                    largest_models.append(model_info)
        
        # Sort and get top 5 largest
        largest_models.sort(key=lambda x: x[1], reverse=True)
        top_5 = largest_models[:5]
        
        results[category] = {
            'total_bytes': total_bytes,
            'model_count': model_count,
            'average_size': total_bytes / model_count if model_count > 0 else 0,
            'size_distribution': size_distribution,
            'top_5_largest': top_5
        }
        
        total_all_categories += total_bytes
    
    # Display results
    print("\n" + "="*80)
    print("📈 MODEL SIZE ANALYSIS REPORT")
    print("="*80 + "\n")
    
    for category, data in results.items():
        print(f"🏷️  {category}")
        print(f"   Total Models: {data['model_count']:,}")
        print(f"   Total Size: {format_bytes(data['total_bytes'])}")
        print(f"   Average Size: {format_bytes(data['average_size'])}")
        
        print("\n   Size Distribution:")
        for size_range, count in data['size_distribution'].items():
            percentage = (count / data['model_count'] * 100) if data['model_count'] > 0 else 0
            print(f"     {size_range}: {count:,} ({percentage:.1f}%)")
        
        print("\n   Top 5 Largest Models:")
        for i, (name, size, model_type) in enumerate(data['top_5_largest'], 1):
            print(f"     {i}. {name[:50]}... ({model_type})")
            print(f"        Size: {format_bytes(size)}")
        print()
    
    print("="*80)
    print(f"📊 TOTAL ACROSS ALL CATEGORIES: {format_bytes(total_all_categories)}")
    print("="*80)
    
    # Summary table
    print("\n📋 SUMMARY TABLE")
    print("-"*60)
    print(f"{'Category':<15} {'Models':<10} {'Total Size':<15} {'Avg Size':<15}")
    print("-"*60)
    
    for category, data in results.items():
        print(f"{category:<15} {data['model_count']:<10,} {format_bytes(data['total_bytes']):<15} {format_bytes(data['average_size']):<15}")
    
    print("-"*60)
    total_models = sum(d['model_count'] for d in results.values())
    print(f"{'TOTAL':<15} {total_models:<10,} {format_bytes(total_all_categories):<15}")
    
    return results

def analyze_database():
    """Analyze model sizes from database"""
    db_path = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/data/civitai_downloader.db")
    
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    print("\n\n📊 Analyzing model sizes from database...\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT priority_category, COUNT(*), SUM(
            CASE 
                WHEN raw_data IS NOT NULL THEN LENGTH(raw_data)
                ELSE 0
            END
        ) as total_raw_size
        FROM models
        GROUP BY priority_category
    """)
    
    print("Raw data sizes in database:")
    for category, count, raw_size in cursor.fetchall():
        if raw_size:
            print(f"  {category or 'uncategorized'}: {count:,} models, {format_bytes(raw_size)} raw JSON data")
    
    conn.close()

def main():
    """Main execution"""
    # Analyze JSON files
    json_results = analyze_json_files()
    
    # Also analyze database
    analyze_database()

if __name__ == "__main__":
    main()