#!/usr/bin/env python3
"""Test extraction logic with real model descriptions."""

import json
from extract_description_logic import extract_useful_description

def test_real_descriptions():
    """Test with real model descriptions from intermediate file."""
    
    jsonl_file = "data/intermediate/search_20250727_033223_00c0f24f_processed.jsonl"
    
    print("🧪 Testing Extraction Logic with Real Data")
    print("=" * 60)
    
    count = 0
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
                
            model = json.loads(line)
            count += 1
            
            name = model.get('name', 'Unknown')
            description = model.get('description', '')
            
            print(f"\n📋 Model #{count}: {name}")
            print(f"📏 Original: {len(description)} chars")
            
            if description:
                # Extract useful info
                extracted = extract_useful_description(description)
                print(f"✅ Extracted: {extracted}")
                print(f"📏 Length: {len(extracted)} chars")
                
                # Show compression ratio
                if len(description) > 0:
                    ratio = len(extracted) / len(description) * 100
                    print(f"📊 Compression: {ratio:.1f}%")
            else:
                print("❌ No description")
            
            # Test first 8 models
            if count >= 8:
                break

if __name__ == "__main__":
    test_real_descriptions()