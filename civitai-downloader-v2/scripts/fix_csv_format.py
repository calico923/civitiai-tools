#!/usr/bin/env python3
"""
CSV Format Fixer - Fix broken CSV files by removing embedded newlines
"""

import csv
import re
from pathlib import Path

def fix_csv_file(input_file: Path, output_file: Path):
    """
    Fix CSV file by removing embedded newlines and making it proper one-liner format.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output fixed CSV file
    """
    print(f"Fixing {input_file.name}...")
    
    # Read the entire file content
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix embedded newlines within quoted fields
    # This regex finds quoted strings and removes newlines within them
    def fix_quoted_field(match):
        quoted_content = match.group(1)
        # Replace newlines with spaces within quoted content
        fixed_content = re.sub(r'\r?\n', ' ', quoted_content)
        # Also compress multiple spaces into single space
        fixed_content = re.sub(r'\s+', ' ', fixed_content)
        return f'"{fixed_content}"'
    
    # Fix quoted fields that contain newlines
    fixed_content = re.sub(r'"([^"]*(?:""[^"]*)*)"', fix_quoted_field, content)
    
    # Remove any remaining standalone newlines that aren't proper row separators
    lines = fixed_content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Count commas to determine if this is a proper CSV row
        # Header has 28 fields, so 27 commas
        comma_count = line.count(',')
        
        if i == 0:  # Header row
            fixed_lines.append(line)
        elif comma_count >= 25:  # Likely a complete row (allow some tolerance)
            fixed_lines.append(line)
        else:
            # This might be a continuation of previous line
            if fixed_lines:
                # Append to previous line with space
                fixed_lines[-1] += ' ' + line
    
    # Write fixed content
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(fixed_lines))
    
    print(f"✓ Fixed {input_file.name} -> {output_file.name}")
    print(f"  Original lines: {len(lines)}")
    print(f"  Fixed lines: {len(fixed_lines)}")
    
    return len(fixed_lines) - 1  # Exclude header

def main():
    """Fix all streaming CSV files"""
    reports_dir = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports")
    
    csv_files = [
        "style_models_stream.csv",
        "concept_models_stream.csv", 
        "pose_models_stream.csv",
        "character_models_stream.csv"
    ]
    
    total_fixed = 0
    
    for csv_file in csv_files:
        input_path = reports_dir / csv_file
        output_path = reports_dir / csv_file.replace('.csv', '_fixed.csv')
        
        if input_path.exists():
            fixed_rows = fix_csv_file(input_path, output_path)
            total_fixed += fixed_rows
        else:
            print(f"⚠️  File not found: {input_path}")
    
    print(f"\n🎉 Total fixed rows: {total_fixed}")
    print("\nFixed files created with '_fixed.csv' suffix")
    print("You can replace the original files once verified:")
    for csv_file in csv_files:
        original = reports_dir / csv_file
        fixed = reports_dir / csv_file.replace('.csv', '_fixed.csv')
        if fixed.exists():
            print(f"  mv {fixed} {original}")

if __name__ == "__main__":
    main()