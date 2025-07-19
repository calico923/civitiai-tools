#!/usr/bin/env python3
"""
CivitAI WebサイトのCheckpoint Type フィルター（Merge、Trained）をAPIでテスト
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_checkpoint_subtypes():
    """Checkpoint Type フィルター（Merge、Trained）をAPIでテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # Checkpoint Type フィルターの値
    checkpoint_subtypes = [
        # UIに表示されるもの
        "Merge",
        "Trained",
        
        # 可能性のあるバリエーション
        "merge",
        "trained",
        "Merged",
        "merged",
        "Training",
        "training",
        "Checkpoint Merge",
        "checkpoint merge",
        "Checkpoint Trained", 
        "checkpoint trained"
    ]
    
    print("🔍 Checkpoint Type フィルターのテスト")
    print("=" * 60)
    
    results = {}
    
    for i, subtype in enumerate(checkpoint_subtypes, 1):
        print(f"[{i:2d}/{len(checkpoint_subtypes)}] Testing: '{subtype}'")
        
        try:
            # 1. typesパラメータとして試す
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={
                    'types': subtype,
                    'limit': 5
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 0)
                    print(f"    ✅ types='{subtype}': {total:,}個")
                    
                    results[subtype] = {
                        'as_types': True,
                        'total': total,
                        'examples': [item['name'] for item in data['items'][:2]]
                    }
                    continue
            
            # 2. Checkpointと組み合わせて試す
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={
                    'types': 'Checkpoint',
                    'tag': subtype,  # tagとして試す
                    'limit': 5
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 0)
                    print(f"    ✅ Checkpoint+tag='{subtype}': {total:,}個")
                    
                    results[subtype] = {
                        'as_checkpoint_tag': True,
                        'total': total,
                        'examples': [item['name'] for item in data['items'][:2]]
                    }
                    continue
            
            # 3. 他のパラメータ組み合わせ
            possible_params = [
                {'checkpointType': subtype},
                {'checkpoint_type': subtype},
                {'subtype': subtype},
                {'category': subtype}
            ]
            
            found = False
            for param_dict in possible_params:
                test_params = {'types': 'Checkpoint', 'limit': 5}
                test_params.update(param_dict)
                
                response = requests.get(
                    'https://civitai.com/api/v1/models',
                    headers=headers,
                    params=test_params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data and len(data['items']) > 0:
                        total = data.get('metadata', {}).get('totalItems', 0)
                        param_name = list(param_dict.keys())[0]
                        print(f"    ✅ {param_name}='{subtype}': {total:,}個")
                        
                        results[subtype] = {
                            'as_param': param_name,
                            'total': total,
                            'examples': [item['name'] for item in data['items'][:2]]
                        }
                        found = True
                        break
            
            if not found:
                print(f"    ❌ 有効なパラメータなし")
                results[subtype] = {'valid': False}
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results[subtype] = {'error': str(e)}
        
        time.sleep(1)
    
    return results

def analyze_checkpoint_metadata():
    """Checkpointの実際のメタデータから分類情報を分析"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    print("\n🔍 Checkpoint メタデータの分析")
    print("=" * 50)
    
    try:
        # 多数のCheckpointを取得
        response = requests.get(
            'https://civitai.com/api/v1/models',
            headers=headers,
            params={
                'types': 'Checkpoint',
                'limit': 50,
                'sort': 'Highest Rated'
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            print(f"📊 {len(items)}個のCheckpointを分析中...")
            
            # メタデータの分析
            merge_indicators = []
            trained_indicators = []
            
            for item in items:
                name = item.get('name', '').lower()
                description = item.get('description', '').lower()
                
                # Merge関連キーワード
                merge_keywords = ['merge', 'merged', 'mix', 'blend', 'fusion']
                # Trained関連キーワード
                trained_keywords = ['trained', 'training', 'fine-tuned', 'finetune', 'custom']
                
                # 名前と説明から分類
                is_merge = any(keyword in name or keyword in description for keyword in merge_keywords)
                is_trained = any(keyword in name or keyword in description for keyword in trained_keywords)
                
                if is_merge:
                    merge_indicators.append(item['name'])
                if is_trained:
                    trained_indicators.append(item['name'])
            
            print(f"\n📈 分析結果:")
            print(f"  Merge系: {len(merge_indicators)}個")
            for example in merge_indicators[:5]:
                print(f"    - {example}")
            
            print(f"\n  Trained系: {len(trained_indicators)}個")
            for example in trained_indicators[:5]:
                print(f"    - {example}")
                
            return {
                'merge_examples': merge_indicators,
                'trained_examples': trained_indicators,
                'total_analyzed': len(items)
            }
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🎯 CivitAI Checkpoint Type フィルターの調査")
    print("=" * 60)
    
    # Checkpoint subtype テスト
    subtype_results = test_checkpoint_subtypes()
    
    # メタデータ分析
    metadata_analysis = analyze_checkpoint_metadata()
    
    print("\n" + "=" * 60)
    print("📊 調査結果サマリー")
    
    # 有効なsubtypes
    valid_subtypes = []
    for subtype, result in subtype_results.items():
        if result.get('valid', True) and 'error' not in result:
            valid_subtypes.append(subtype)
            
            if result.get('as_types'):
                print(f"  ✅ {subtype} (types): {result['total']:,}個")
            elif result.get('as_checkpoint_tag'):
                print(f"  ✅ {subtype} (Checkpoint+tag): {result['total']:,}個")
            elif result.get('as_param'):
                print(f"  ✅ {subtype} ({result['as_param']}): {result['total']:,}個")
    
    if not valid_subtypes:
        print("  ❌ 有効なCheckpoint Type パラメータは見つかりませんでした")
        print("  💡 解決策: クライアントサイドでキーワードフィルタリング")
    
    # 結果保存
    import json
    results = {
        'subtype_tests': subtype_results,
        'metadata_analysis': metadata_analysis,
        'valid_subtypes': valid_subtypes
    }
    
    with open('checkpoint_subtypes_investigation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: checkpoint_subtypes_investigation.json")

if __name__ == "__main__":
    main()