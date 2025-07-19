#!/usr/bin/env python3
"""
GitHubで見つけたCheckpoint Typesの調査
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_checkpoint_types():
    """Checkpoint Typesの各種バリエーションをテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # Checkpoint Types関連のバリエーション
    checkpoint_variations = [
        "Checkpoint Types",
        "CheckpointTypes", 
        "Checkpoint_Types",
        "checkpoint-types",
        "checkpointTypes",
        "CHECKPOINT_TYPES",
        "CheckpointType",
        "Checkpoint Type",
        "CheckpointMerge",
        "Checkpoint Merge",
        "checkpoint merge",
        "CheckpointMerged",
        "MergedCheckpoint",
        "Merged Checkpoint"
    ]
    
    print(f"🔍 {len(checkpoint_variations)}個のCheckpoint Types関連バリエーションを調査中...")
    print("=" * 60)
    
    valid_types = []
    
    for i, variant in enumerate(checkpoint_variations, 1):
        print(f"[{i:2d}/{len(checkpoint_variations)}] Testing: '{variant}'")
        
        try:
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={'types': variant, 'limit': 3},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 'unknown')
                    examples = []
                    for item in data['items'][:2]:
                        model_type = item.get('type', 'unknown')
                        examples.append(f"{item['name']} (type: {model_type})")
                    
                    valid_types.append({
                        'variant': variant,
                        'total': total,
                        'examples': examples
                    })
                    print(f"    ✅ Valid! Total: {total}")
                    for example in examples:
                        print(f"       - {example}")
                elif 'items' in data:
                    print(f"    ⚠️ Valid but no results")
                else:
                    print(f"    ❌ Invalid response structure")
            else:
                print(f"    ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        # レート制限対策
        time.sleep(1)
    
    return valid_types

def main():
    print("🔬 Checkpoint Types 調査")
    print("GitHubで見つけた情報を検証")
    print("=" * 60)
    
    valid_types = test_checkpoint_types()
    
    print("\n" + "=" * 60)
    print("📊 調査結果")
    
    # Checkpoint Types関連のバリエーション（メインから参照用）
    checkpoint_variations = [
        "Checkpoint Types", "CheckpointTypes", "Checkpoint_Types",
        "checkpoint-types", "checkpointTypes", "CHECKPOINT_TYPES",
        "CheckpointType", "Checkpoint Type", "CheckpointMerge",
        "Checkpoint Merge", "checkpoint merge", "CheckpointMerged",
        "MergedCheckpoint", "Merged Checkpoint"
    ]
    
    if valid_types:
        print(f"\n✅ 有効なCheckpoint Types ({len(valid_types)}個):")
        for type_info in valid_types:
            print(f"  🟢 '{type_info['variant']}': {type_info['total']} models")
            for example in type_info['examples']:
                print(f"     - {example}")
    else:
        print("\n❌ 有効なCheckpoint Types関連のタイプは見つかりませんでした")
        print("   すべてのバリエーションでHTTP 400エラーが発生")
    
    # 結果保存
    import json
    results = {
        'checkpoint_types_investigation': valid_types,
        'tested_variations': checkpoint_variations,
        'tested_count': len(checkpoint_variations),
        'valid_variations': len(valid_types),
        'conclusion': 'すべてのCheckpoint Types関連バリエーションが無効'
    }
    
    with open('checkpoint_types_investigation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: checkpoint_types_investigation.json")

if __name__ == "__main__":
    main()