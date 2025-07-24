#!/usr/bin/env python3
"""
Summary script showing the results of the CSV import process.
Displays comprehensive statistics about the imported model data.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import sys

# Add parent directory to Python path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.data.database import DatabaseManager


async def generate_import_summary():
    """Generate a comprehensive summary of imported data."""
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "civitai_downloader.db"
    reports_dir = project_root / "reports"
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    
    print("=" * 70)
    print("CIVITAI MODEL IMPORT SUMMARY")
    print("=" * 70)
    print(f"Database location: {db_path}")
    print(f"Source CSV files: {reports_dir}")
    print()
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Basic statistics
        cursor.execute('SELECT COUNT(*) FROM models')
        total_models = cursor.fetchone()[0]
        print(f"Total models imported: {total_models:,}")
        
        # Category breakdown
        print("\n📁 MODELS BY CATEGORY:")
        cursor.execute('SELECT priority_category, COUNT(*) FROM models GROUP BY priority_category ORDER BY COUNT(*) DESC')
        for category, count in cursor.fetchall():
            category_name = category or "Unknown"
            percentage = (count / total_models) * 100
            print(f"  {category_name.capitalize():<12}: {count:>5,} ({percentage:5.1f}%)")
        
        # Model type breakdown
        print("\n🏷️  MODELS BY TYPE:")
        cursor.execute('SELECT type, COUNT(*) FROM models GROUP BY type ORDER BY COUNT(*) DESC LIMIT 10')
        for model_type, count in cursor.fetchall():
            percentage = (count / total_models) * 100
            print(f"  {model_type:<15}: {count:>5,} ({percentage:5.1f}%)")
        
        # NSFW breakdown
        print("\n🔞 CONTENT RATING:")
        cursor.execute('SELECT nsfw, COUNT(*) FROM models GROUP BY nsfw')
        for nsfw, count in cursor.fetchall():
            nsfw_label = "NSFW" if nsfw else "SFW"
            percentage = (count / total_models) * 100
            print(f"  {nsfw_label:<15}: {count:>5,} ({percentage:5.1f}%)")
        
        # Commercial use breakdown
        print("\n💼 COMMERCIAL USE PERMISSIONS:")
        cursor.execute('SELECT allowCommercialUse, COUNT(*) FROM models GROUP BY allowCommercialUse ORDER BY COUNT(*) DESC LIMIT 5')
        for permission, count in cursor.fetchall():
            if permission:
                percentage = (count / total_models) * 100
                print(f"  {permission:<15}: {count:>5,} ({percentage:5.1f}%)")
        
        # Top creators
        print("\n👤 TOP CREATORS:")
        cursor.execute("""
            SELECT creator_username, COUNT(*) as model_count
            FROM models 
            WHERE creator_username IS NOT NULL AND creator_username != ''
            GROUP BY creator_username
            ORDER BY model_count DESC
            LIMIT 10
        """)
        for i, (creator, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i:2d}. {creator:<20}: {count:>3,} models")
        
        # Category type breakdown
        print("\n📊 MODEL TYPES BY CATEGORY:")
        for category in ['style', 'concept', 'pose', 'character']:
            cursor.execute('SELECT type, COUNT(*) FROM models WHERE priority_category = ? GROUP BY type ORDER BY COUNT(*) DESC LIMIT 3', (category,))
            results = cursor.fetchall()
            if results:
                print(f"\n  {category.capitalize()} models:")
                for model_type, count in results:
                    print(f"    {model_type}: {count}")
        
        # Sample popular models (based on download counts from raw_data)
        print("\n🔥 SAMPLE POPULAR MODELS:")
        cursor.execute('SELECT id, name, type, priority_category, raw_data FROM models LIMIT 100')
        popular_models = []
        
        for row in cursor.fetchall():
            try:
                raw_data = json.loads(row[4]) if row[4] else {}
                stats = raw_data.get('stats', {})
                download_count = stats.get('downloadCount', 0) or 0
                
                if download_count > 0:
                    popular_models.append({
                        'id': row[0],
                        'name': row[1][:50],
                        'type': row[2],
                        'category': row[3],
                        'downloads': download_count
                    })
            except:
                continue
        
        # Sort and show top models
        popular_models.sort(key=lambda x: x['downloads'], reverse=True)
        for i, model in enumerate(popular_models[:10], 1):
            print(f"  {i:2d}. {model['name']:<50}... ({model['type']}, {model['downloads']:,} downloads)")
        
        # File information
        print("\n📁 SOURCE FILES PROCESSED:")
        csv_files = [
            ('style_models_stream.csv', 'style'),
            ('concept_models_stream.csv', 'concept'),
            ('pose_models_stream.csv', 'pose'),
            ('character_models_stream.csv', 'character')
        ]
        
        for filename, category in csv_files:
            file_path = reports_dir / filename
            if file_path.exists():
                file_size = file_path.stat().st_size / 1024 / 1024  # MB
                cursor.execute('SELECT COUNT(*) FROM models WHERE priority_category = ?', (category,))
                imported_count = cursor.fetchone()[0]
                print(f"  ✅ {filename:<30}: {file_size:>6.1f} MB → {imported_count:>4,} models")
            else:
                print(f"  ❌ {filename:<30}: File not found")
    
    print("\n" + "=" * 70)
    print("IMPORT COMPLETED SUCCESSFULLY! 🎉")
    print("=" * 70)
    print("\nNext steps:")
    print("• Use 'python scripts/query_models.py' for interactive search")
    print("• Access database directly at: data/civitai_downloader.db")
    print("• Models are ready for download processing")
    print()


if __name__ == "__main__":
    asyncio.run(generate_import_summary())