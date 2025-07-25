#!/usr/bin/env python3
"""
Import latest model data from JSON files into database
"""
import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.html_cleaner import HTMLCleaner

def process_model_data(model: Dict[str, Any]) -> Dict[str, Any]:
    """Process model data for database insertion"""
    # Clean HTML from description
    description = model.get('description', '')
    if description:
        description = HTMLCleaner.clean_html(description)
    
    # Extract trainedWords from modelVersions
    trained_words = []
    if 'modelVersions' in model and isinstance(model['modelVersions'], list):
        for version in model['modelVersions']:
            if isinstance(version, dict) and 'trainedWords' in version:
                version_words = version.get('trainedWords', [])
                if isinstance(version_words, list):
                    trained_words.extend(version_words)
    
    # Also check root level trainedWords
    if 'trainedWords' in model and isinstance(model['trainedWords'], list):
        trained_words.extend(model['trainedWords'])
    
    # Remove duplicates while preserving order
    unique_words = list(dict.fromkeys(trained_words))
    
    # Extract creator info
    creator = model.get('creator', {})
    creator_username = creator.get('username', '') if isinstance(creator, dict) else ''
    
    # Prepare data for insertion
    return {
        'id': model.get('id'),
        'name': model.get('name', ''),
        'type': model.get('type', ''),
        'description': description,
        'creator_username': creator_username,
        'nsfw': model.get('nsfw', False),
        'allowCommercialUse': json.dumps(model.get('allowCommercialUse', [])),
        'trainedWords': json.dumps(unique_words) if unique_words else None,
        'raw_data': json.dumps(model),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

def import_json_file(file_path: Path, conn: sqlite3.Connection, category: str) -> int:
    """Import models from a JSON file"""
    print(f"\nImporting {category} models from {file_path.name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            models = json.load(f)
        
        if not isinstance(models, list):
            print(f"  ⚠️  Invalid JSON format in {file_path.name}")
            return 0
        
        cursor = conn.cursor()
        imported = 0
        updated = 0
        
        for model in models:
            if not isinstance(model, dict) or 'id' not in model:
                continue
            
            processed_data = process_model_data(model)
            processed_data['priority_category'] = category.lower()
            
            # Check if model already exists
            cursor.execute("SELECT id FROM models WHERE id = ?", (processed_data['id'],))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing model
                cursor.execute("""
                    UPDATE models SET
                        name = ?,
                        type = ?,
                        description = ?,
                        creator_username = ?,
                        nsfw = ?,
                        allowCommercialUse = ?,
                        trainedWords = ?,
                        raw_data = ?,
                        updated_at = ?,
                        priority_category = ?
                    WHERE id = ?
                """, (
                    processed_data['name'],
                    processed_data['type'],
                    processed_data['description'],
                    processed_data['creator_username'],
                    processed_data['nsfw'],
                    processed_data['allowCommercialUse'],
                    processed_data['trainedWords'],
                    processed_data['raw_data'],
                    processed_data['updated_at'],
                    processed_data['priority_category'],
                    processed_data['id']
                ))
                updated += 1
            else:
                # Insert new model
                cursor.execute("""
                    INSERT INTO models (
                        id, name, type, description, creator_username, 
                        nsfw, allowCommercialUse, trainedWords, raw_data,
                        created_at, updated_at, priority_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    processed_data['id'],
                    processed_data['name'],
                    processed_data['type'],
                    processed_data['description'],
                    processed_data['creator_username'],
                    processed_data['nsfw'],
                    processed_data['allowCommercialUse'],
                    processed_data['trainedWords'],
                    processed_data['raw_data'],
                    processed_data['created_at'],
                    processed_data['updated_at'],
                    processed_data['priority_category']
                ))
                imported += 1
            
            if (imported + updated) % 1000 == 0:
                print(f"  Progress: {imported} new, {updated} updated...")
                conn.commit()
        
        conn.commit()
        print(f"  ✅ Completed: {imported} new models, {updated} updated")
        return imported + updated
        
    except Exception as e:
        print(f"  ❌ Error importing {file_path.name}: {e}")
        conn.rollback()
        return 0

def main():
    """Main execution function"""
    db_path = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/data/civitai_downloader.db")
    json_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    if not json_dir.exists():
        print(f"❌ JSON directory not found: {json_dir}")
        return
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    try:
        # Import each category
        categories = {
            'CHARACTER': 'character_models_category.json',
            'STYLE': 'style_models_category.json',
            'CONCEPT': 'concept_models_category.json',
            'POSES': 'poses_models_category.json'
        }
        
        total_imported = 0
        for category, filename in categories.items():
            file_path = json_dir / filename
            if file_path.exists():
                count = import_json_file(file_path, conn, category)
                total_imported += count
            else:
                print(f"⚠️  File not found: {filename}")
        
        # Show final statistics
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM models")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT priority_category, COUNT(*) 
            FROM models 
            GROUP BY priority_category 
            ORDER BY COUNT(*) DESC
        """)
        
        print("\n📊 Database Statistics:")
        print(f"Total models: {total_count:,}")
        print("\nBy category:")
        for category, count in cursor.fetchall():
            print(f"  {category or 'uncategorized'}: {count:,}")
        
        # Show sample of models with trainedWords
        cursor.execute("""
            SELECT id, name, type, trainedWords
            FROM models
            WHERE trainedWords IS NOT NULL AND trainedWords != '[]'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        print("\n🎯 Sample models with trainedWords:")
        for row in cursor.fetchall():
            model_id, name, model_type, trained_words_json = row
            trained_words = json.loads(trained_words_json) if trained_words_json else []
            if trained_words:
                print(f"  {name} ({model_type})")
                print(f"    Trigger words: {', '.join(trained_words[:3])}{'...' if len(trained_words) > 3 else ''}")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\n✅ Import completed!")

if __name__ == "__main__":
    main()