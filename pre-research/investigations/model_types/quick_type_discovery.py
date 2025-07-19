#!/usr/bin/env python3
"""
CivitAI APIのモデルタイプを効率的に調査
"""

import os
import requests
import json
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

def get_sample_models():
    """サンプルモデルを取得してタイプを発見"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # 大きなサンプルを一度に取得
    try:
        response = requests.get(
            'https://civitai.com/api/v1/models',
            headers=headers,
            params={'limit': 100, 'sort': 'Most Downloaded'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if 'items' in data:
            types = [item.get('type') for item in data['items'] if item.get('type')]
            return types
        
    except Exception as e:
        print(f"Error: {e}")
    
    return []

def test_specific_types():
    """特定のタイプをテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # 可能性の高いタイプを優先的にテスト
    priority_types = [
        "Checkpoint", "LORA", "LoCon", "TextualInversion", 
        "Hypernetwork", "AestheticGradient", "ControlNet", 
        "VAE", "Embedding", "Poses", "Wildcards", "Other"
    ]
    
    valid_types = []
    
    for model_type in priority_types:
        try:
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={'types': model_type, 'limit': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 'unknown')
                    valid_types.append((model_type, total))
                    print(f"✅ {model_type}: {total} models")
                else:
                    print(f"⚠️ {model_type}: Valid but no results")
            else:
                print(f"❌ {model_type}: Invalid")
                
        except Exception as e:
            print(f"❌ {model_type}: Error - {e}")
    
    return valid_types

def main():
    print("🔍 CivitAI モデルタイプ調査（高速版）")
    print("=" * 50)
    
    # サンプルからタイプを発見
    print("📊 サンプルモデルからタイプを収集中...")
    sample_types = get_sample_models()
    
    if sample_types:
        type_counts = Counter(sample_types)
        print(f"発見したタイプ: {len(type_counts)}種類")
        
        for model_type, count in type_counts.most_common():
            print(f"  - {model_type}: {count}個のサンプル")
    
    print("\n🧪 個別タイプのテスト...")
    valid_types = test_specific_types()
    
    print(f"\n📋 有効なモデルタイプ一覧 ({len(valid_types)}個):")
    for model_type, total in valid_types:
        print(f"  - {model_type}: {total} models")
    
    # 結果を保存
    results = {
        'discovered_from_samples': dict(Counter(sample_types)) if sample_types else {},
        'valid_types': dict(valid_types),
        'all_discovered_types': list(set(sample_types)) if sample_types else []
    }
    
    with open('model_types_quick_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n結果保存: model_types_quick_results.json")

if __name__ == "__main__":
    main()