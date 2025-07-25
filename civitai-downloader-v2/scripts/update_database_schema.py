#!/usr/bin/env python3
"""
Update database schema to include trainedWords field and clean HTML from descriptions
"""
import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.html_cleaner import HTMLCleaner

def update_database_schema(db_path: Path):
    """Update database schema to include trainedWords field"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if trainedWords column already exists
        cursor.execute("PRAGMA table_info(models)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'trainedWords' not in columns:
            print("Adding trainedWords column to models table...")
            cursor.execute("ALTER TABLE models ADD COLUMN trainedWords TEXT")
            conn.commit()
            print("✅ trainedWords column added successfully")
        else:
            print("ℹ️  trainedWords column already exists")
        
        # Clean existing HTML descriptions
        print("\nCleaning HTML from existing descriptions...")
        cursor.execute("SELECT id, description, raw_data FROM models WHERE description IS NOT NULL")
        rows = cursor.fetchall()
        
        cleaned_count = 0
        for row_id, description, raw_data in rows:
            if description:
                cleaned_desc = HTMLCleaner.clean_html(description)
                if cleaned_desc != description:
                    cursor.execute("UPDATE models SET description = ? WHERE id = ?", (cleaned_desc, row_id))
                    cleaned_count += 1
            
            # Extract trainedWords from raw_data if available
            if raw_data:
                try:
                    data = json.loads(raw_data)
                    trained_words = []
                    
                    # Check modelVersions for trainedWords
                    if 'modelVersions' in data and isinstance(data['modelVersions'], list):
                        for version in data['modelVersions']:
                            if isinstance(version, dict) and 'trainedWords' in version:
                                version_words = version.get('trainedWords', [])
                                if isinstance(version_words, list):
                                    trained_words.extend(version_words)
                    
                    # Also check root level trainedWords
                    if 'trainedWords' in data and isinstance(data['trainedWords'], list):
                        trained_words.extend(data['trainedWords'])
                    
                    # Remove duplicates and store as JSON array
                    if trained_words:
                        unique_words = list(dict.fromkeys(trained_words))  # Preserve order
                        cursor.execute("UPDATE models SET trainedWords = ? WHERE id = ?", 
                                     (json.dumps(unique_words), row_id))
                
                except json.JSONDecodeError:
                    pass
        
        conn.commit()
        print(f"✅ Cleaned HTML from {cleaned_count} descriptions")
        
        # Show updated schema
        print("\nUpdated schema:")
        cursor.execute("PRAGMA table_info(models)")
        for column in cursor.fetchall():
            print(f"  {column[1]} ({column[2]})")
        
        # Show sample data
        print("\nSample data with trainedWords:")
        cursor.execute("""
            SELECT id, name, type, trainedWords 
            FROM models 
            WHERE trainedWords IS NOT NULL 
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Name: {row[1]}, Type: {row[2]}")
            if row[3]:
                words = json.loads(row[3])
                print(f"    Trained Words: {', '.join(words[:3])}...")
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main execution function"""
    db_path = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/data/civitai_downloader.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"Updating database: {db_path}")
    update_database_schema(db_path)
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    main()