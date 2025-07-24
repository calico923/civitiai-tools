#!/usr/bin/env python3
"""
Clean description fields from large JSON files using streaming approach.
"""

import json
import os
import re
from pathlib import Path


def clean_descriptions_streaming(file_path: Path, backup: bool = True):
    """
    Remove description fields from a JSON file using streaming approach.
    
    Args:
        file_path: Path to JSON file
        backup: Whether to create a backup before modification
    """
    print(f"Processing: {file_path}")
    
    original_size = os.path.getsize(file_path)
    print(f"Original size: {original_size:,} bytes ({original_size/1024/1024:.1f} MB)")
    
    # Create backup if requested
    if backup:
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        if not backup_path.exists():
            print(f"Creating backup: {backup_path}")
            import shutil
            shutil.copy2(file_path, backup_path)
        else:
            print(f"Backup already exists: {backup_path}")
    
    temp_path = file_path.with_suffix(f"{file_path.suffix}.temp")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as infile:
            with open(temp_path, 'w', encoding='utf-8') as outfile:
                # Start processing
                line_count = 0
                descriptions_removed = 0
                in_description = False
                description_depth = 0
                
                for line in infile:
                    line_count += 1
                    if line_count % 100000 == 0:
                        print(f"  Processed {line_count:,} lines...")
                    
                    # Check if this line contains a description field
                    if '"description"' in line and ':' in line:
                        # Found description field
                        descriptions_removed += 1
                        # Replace the description content with empty string
                        # Handle various patterns
                        if line.strip().endswith(','):
                            outfile.write('    "description": "",\n')
                        else:
                            outfile.write('    "description": ""\n')
                        in_description = True
                        continue
                    
                    # Skip lines that are part of description content
                    if in_description:
                        # Check if this line ends the description field
                        # Look for closing quote followed by comma or closing brace
                        if re.search(r'"\s*[,}]', line.strip()):
                            in_description = False
                        continue
                    
                    # Write other lines as-is
                    outfile.write(line)
        
        # Replace original file with cleaned version
        temp_path.replace(file_path)
        
        new_size = os.path.getsize(file_path)
        size_reduction = original_size - new_size
        
        print(f"  Lines processed: {line_count:,}")
        print(f"  Descriptions removed: {descriptions_removed}")
        print(f"  New size: {new_size:,} bytes ({new_size/1024/1024:.1f} MB)")
        print(f"  Size reduction: {size_reduction:,} bytes ({size_reduction/original_size*100:.1f}%)")
        print()
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        if temp_path.exists():
            temp_path.unlink()


def main():
    """Clean descriptions from raw files."""
    
    success_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search")
    
    # Process raw files (they contain the descriptions)
    raw_files = list(success_dir.glob("*_raw.json"))
    
    if not raw_files:
        print("No raw JSON files found")
        return
    
    print(f"Found {len(raw_files)} raw JSON files to process:")
    for file_path in raw_files:
        print(f"  - {file_path.name} ({os.path.getsize(file_path)/1024/1024:.1f} MB)")
    print()
    
    # Process each file
    total_reduction = 0
    for file_path in sorted(raw_files, key=lambda x: os.path.getsize(x)):
        original_size = os.path.getsize(file_path)
        clean_descriptions_streaming(file_path, backup=True)
        new_size = os.path.getsize(file_path)
        total_reduction += (original_size - new_size)
    
    print(f"Total size reduction: {total_reduction:,} bytes ({total_reduction/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()