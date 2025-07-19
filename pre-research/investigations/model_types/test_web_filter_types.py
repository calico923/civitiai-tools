#!/usr/bin/env python3
"""
CivitAI WebサイトのフィルターUIに表示されるタイプをAPIでテスト
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_web_filter_types():
    """WebサイトのフィルターUI表示タイプをAPIでテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # WebサイトのFilter by Model Typeに表示されるタイプ
    web_filter_types = [
        # 画像から読み取ったタイプ
        "Aesthetic Gradient",
        "Checkpoint",
        "Controlnet",
        "Detection", 
        "DoRA",
        "Hypernetwork",
        "LoRA",
        "LyCORIS",
        "Motion",
        "Other",
        "Poses",
        "Embedding",
        "Upscaler",
        "VAE",
        "Wildcards",
        "Workflows",
        
        # 可能性のあるバリエーション
        "AestheticGradient",
        "ControlNet",
        "Embeddings",
        "TextualInversion",
        "LORA",
        "LoCon"
    ]
    
    print("🌐 CivitAI WebサイトフィルターUIのタイプをAPIでテスト")
    print("=" * 70)
    
    valid_types = []
    invalid_types = []
    
    for i, model_type in enumerate(web_filter_types, 1):
        print(f"[{i:2d}/{len(web_filter_types)}] Testing: '{model_type}'")
        
        try:
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={'types': model_type, 'limit': 3},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 0)
                    
                    # 実際のモデルタイプを確認
                    actual_types = []
                    for item in data['items'][:3]:
                        actual_type = item.get('type', 'unknown')
                        actual_types.append(actual_type)
                        
                    valid_types.append({
                        'web_filter_name': model_type,
                        'total': total,
                        'actual_types': list(set(actual_types)),
                        'examples': [item['name'] for item in data['items'][:2]]
                    })
                    
                    print(f"    ✅ Valid! Total: {total:,}")
                    print(f"    実際のtype: {list(set(actual_types))}")
                    for example in data['items'][:2]:
                        print(f"       - {example['name']}")
                        
                elif 'items' in data:
                    print(f"    ⚠️ Valid but no results")
                    valid_types.append({
                        'web_filter_name': model_type,
                        'total': 0,
                        'actual_types': [],
                        'examples': []
                    })
                else:
                    print(f"    ❌ Invalid response structure")
                    invalid_types.append(model_type)
                    
            else:
                print(f"    ❌ HTTP {response.status_code}")
                invalid_types.append(model_type)
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            invalid_types.append(model_type)
        
        time.sleep(1)
    
    return valid_types, invalid_types

def test_embedding_specifically():
    """Embeddingタイプを特別に詳しく調査"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    print("\n🎯 Embedding タイプの詳細調査")
    print("=" * 50)
    
    # Embeddingに関連する可能性のあるタイプ
    embedding_variants = [
        "Embedding",
        "Embeddings", 
        "TextualInversion",
        "Textual Inversion",
        "TI",
        "textual_inversion",
        "embedding",
        "embeddings"
    ]
    
    for variant in embedding_variants:
        print(f"\n🔍 Testing: '{variant}'")
        
        try:
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={'types': variant, 'limit': 5},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 0)
                    print(f"  ✅ {total:,}個のモデル")
                    
                    # 詳細情報を確認
                    for item in data['items'][:3]:
                        print(f"    - {item['name']}")
                        print(f"      Type: {item.get('type', 'unknown')}")
                        versions = item.get('modelVersions', [])
                        if versions:
                            print(f"      BaseModel: {versions[0].get('baseModel', 'unknown')}")
                else:
                    print(f"  ❌ 結果なし")
            else:
                print(f"  ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(1)

def main():
    print("🔍 CivitAI Webサイトフィルターで表示されるタイプの検証")
    print("=" * 70)
    
    # メイン調査
    valid_types, invalid_types = test_web_filter_types()
    
    # Embedding特別調査
    test_embedding_specifically()
    
    print("\n" + "=" * 70)
    print("📊 調査結果サマリー")
    
    print(f"\n✅ 有効なタイプ ({len(valid_types)}個):")
    for type_info in valid_types:
        if type_info['total'] > 0:
            print(f"  🟢 {type_info['web_filter_name']}: {type_info['total']:,}個")
            print(f"     実際のAPI type: {type_info['actual_types']}")
        else:
            print(f"  🟡 {type_info['web_filter_name']}: 有効だが結果なし")
    
    print(f"\n❌ 無効なタイプ ({len(invalid_types)}個):")
    for invalid_type in invalid_types[:10]:  # 最初の10個
        print(f"  🔴 {invalid_type}")
    if len(invalid_types) > 10:
        print(f"  ... and {len(invalid_types) - 10} more")
    
    # 結果保存
    import json
    
    # WebサイトのFilter by Model Typeに表示されるタイプ
    web_filter_types = [
        "Aesthetic Gradient", "Checkpoint", "Controlnet", "Detection", 
        "DoRA", "Hypernetwork", "LoRA", "LyCORIS", "Motion", "Other",
        "Poses", "Embedding", "Upscaler", "VAE", "Wildcards", "Workflows",
        "AestheticGradient", "ControlNet", "Embeddings", "TextualInversion",
        "LORA", "LoCon"
    ]
    
    results = {
        'valid_types': valid_types,
        'invalid_types': invalid_types,
        'summary': {
            'total_tested': len(web_filter_types),
            'valid_count': len(valid_types),
            'invalid_count': len(invalid_types)
        }
    }
    
    with open('web_filter_types_validation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: web_filter_types_validation.json")

if __name__ == "__main__":
    main()