#!/usr/bin/env python3
"""Analyze description field structure in intermediate files."""

import json
import re
from html import unescape

def analyze_descriptions():
    """Analyze description field patterns in JSONL file."""
    
    jsonl_file = "data/intermediate/search_20250727_033223_00c0f24f_processed.jsonl"
    
    print("🔍 Description Analysis")
    print("=" * 60)
    
    model_count = 0
    html_patterns = {}
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
                
            model = json.loads(line)
            model_count += 1
            
            name = model.get('name', 'Unknown')
            description = model.get('description', '')
            
            print(f"\n📋 Model #{model_count}: {name}")
            print(f"📏 Raw length: {len(description)} chars")
            
            if not description:
                print("❌ No description")
                continue
            
            # Show first 300 chars of raw HTML
            print(f"🔤 Raw HTML (first 300 chars):")
            print(f"   {description[:300]}...")
            
            # Clean HTML and show result
            cleaned = clean_html_basic(description)
            print(f"🧹 Cleaned (first 300 chars):")
            print(f"   {cleaned[:300]}...")
            print(f"📏 Cleaned length: {len(cleaned)} chars")
            
            # Look for common patterns
            find_patterns(description, name)
            
            # Stop after 5 models for analysis
            if model_count >= 5:
                break

def clean_html_basic(html_text: str) -> str:
    """Basic HTML cleaning for analysis."""
    if not html_text:
        return ""
    
    # HTMLエンティティをデコード
    text = unescape(html_text)
    
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 複数の空白を1つに
    text = re.sub(r'\s+', ' ', text)
    
    # 先頭末尾の空白を除去
    text = text.strip()
    
    return text

def find_patterns(description: str, model_name: str):
    """Find common patterns in descriptions."""
    
    # Common section markers
    patterns = [
        r'(?i)(recommend|setting|prompt|negative|cfg|step|sampler)',
        r'(?i)(使い方|設定|推奨|サンプラー|ステップ)',
        r'(?i)(how to|usage|guide|instruction)',
        r'(?i)(about|description|overview)',
        r'<[^>]+>',  # HTML tags
        r'https?://[^\s]+',  # URLs
    ]
    
    print(f"🔍 Pattern Analysis for '{model_name}':")
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, description)
        if matches:
            print(f"   Pattern {i+1}: {len(matches)} matches - {matches[:3]}")

if __name__ == "__main__":
    analyze_descriptions()