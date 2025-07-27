#!/usr/bin/env python3
"""Convert processed JSONL to CSV format."""

import json
import csv
import sys
import re
from pathlib import Path
from html import unescape

# Import extraction logic
from extract_description_logic import extract_useful_description

def convert_jsonl_to_csv(jsonl_path: str, csv_path: str):
    """Convert JSONL file to CSV format."""
    
    models = []
    
    # Read JSONL file
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                model = json.loads(line)
                models.append(model)
    
    if not models:
        print("No models found in JSONL file")
        return
    
    print(f"Found {len(models)} models")
    
    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        headers = [
            'ID', 'Name', 'Type', 'Creator', 'Downloads', 'Likes', 'Rating', 'Commercial_Use',
            'Primary_Category', 'All_Categories', 'Tags', 'Base_Model', 'Description', 'Created_At', 'Updated_At'
        ]
        writer.writerow(headers)
        
        # Data rows
        for model in models:
            processing = model.get('_processing', {})
            primary_category = processing.get('primary_category', 'unknown')
            all_categories = ', '.join(processing.get('all_categories', []))
            
            # Commercial Use (1=allowed, 0=not allowed)
            allow_commercial = model.get('allowCommercialUse', [])
            if isinstance(allow_commercial, list):
                commercial_use = '1' if allow_commercial and len(allow_commercial) > 0 else '0'
            elif isinstance(allow_commercial, bool):
                commercial_use = '1' if allow_commercial else '0'
            else:
                commercial_use = '0'
            
            # Tags
            tags = model.get('tags', [])
            if tags and isinstance(tags[0], dict):
                tags_list = [tag.get('name', '') for tag in tags]
            else:
                tags_list = [str(tag) for tag in tags if tag]
            tags_str = ', '.join(tags_list[:10])  # First 10 tags
            
            # Base Model from versions
            base_models = set()
            for version in model.get('modelVersions', []):
                if version.get('baseModel'):
                    base_models.add(version['baseModel'])
            base_model_str = ', '.join(sorted(base_models))
            
            # Description (extract useful info using new logic)
            description = extract_useful_description(model.get('description', ''))
            
            # Stats
            stats = model.get('stats', {})
            
            row = [
                model.get('id', ''),
                model.get('name', ''),
                model.get('type', ''),
                model.get('creator', {}).get('username', ''),
                stats.get('downloadCount', 0),
                stats.get('thumbsUpCount', 0),
                stats.get('rating', 0),
                commercial_use,
                primary_category,
                all_categories,
                tags_str,
                base_model_str,
                description,
                model.get('createdAt', ''),
                model.get('updatedAt', '')
            ]
            writer.writerow(row)
    
    print(f"CSV saved to: {csv_path}")

if __name__ == "__main__":
    # Latest NoobAI Checkpoint test results
    jsonl_file = "data/intermediate/search_20250727_033223_00c0f24f_processed.jsonl"
    csv_file = "reports/noobai_checkpoint_models.csv"
    
    convert_jsonl_to_csv(jsonl_file, csv_file)