#!/usr/bin/env python3
"""
Clean description fields from JSON files to reduce file size and remove problematic HTML content.
"""

import json
import os
from pathlib import Path


def clean_descriptions_in_file(file_path: Path, backup: bool = True):
    """
    Remove description fields from a JSON file.
    
    Args:
        file_path: Path to JSON file
        backup: Whether to create a backup before modification
    """
    print(f"Processing: {file_path}")
    
    # Create backup if requested
    if backup:
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        print(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(file_path, backup_path)
    
    # Load JSON data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_size = os.path.getsize(file_path)
        items_processed = 0
        descriptions_removed = 0
        
        # Process each item
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    items_processed += 1
                    if 'description' in item and item['description']:
                        descriptions_removed += 1
                        # Keep the field but make it empty
                        item['description'] = ""
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        new_size = os.path.getsize(file_path)
        size_reduction = original_size - new_size
        
        print(f"  Items processed: {items_processed}")
        print(f"  Descriptions removed: {descriptions_removed}")
        print(f"  Original size: {original_size:,} bytes")
        print(f"  New size: {new_size:,} bytes")
        print(f"  Size reduction: {size_reduction:,} bytes ({size_reduction/original_size*100:.1f}%)")
        print()
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def main():
    """Clean descriptions from all category search result files."""
    
    success_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search")
    
    if not success_dir.exists():
        print(f"Directory not found: {success_dir}")
        return
    
    # Find all JSON files
    json_files = list(success_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in success_category_search directory")
        return
    
    print(f"Found {len(json_files)} JSON files to process:")
    for file_path in json_files:
        print(f"  - {file_path.name}")
    print()
    
    # Process each file
    total_reduction = 0
    for file_path in json_files:
        original_size = os.path.getsize(file_path)
        clean_descriptions_in_file(file_path, backup=True)
        new_size = os.path.getsize(file_path)
        total_reduction += (original_size - new_size)
    
    print(f"Total size reduction: {total_reduction:,} bytes ({total_reduction/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()