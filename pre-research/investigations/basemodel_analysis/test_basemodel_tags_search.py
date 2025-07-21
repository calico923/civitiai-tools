#!/usr/bin/env python3
"""
baseModelをtagsパラメータで検索する方法をテスト
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_basemodel_tags_search():
    """baseModelをtagsで検索する方法をテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # テスト対象のbaseModel tags
    basemodel_tags = [
        "illustrious",
        "pony",
        "noobai", 
        "sdxl",
        "sd 1.5",
        "flux",
        "sd 3.0"
    ]
    
    # テスト対象のモデルタイプ
    model_types = ["Checkpoint", "LORA", "LoCon"]
    
    print("🔍 baseModel × Type 組み合わせ検索テスト")
    print("=" * 60)
    
    results = {}
    
    for model_type in model_types:
        print(f"\n📊 {model_type} の検索結果:")
        results[model_type] = {}
        
        for basemodel in basemodel_tags:
            print(f"  [{basemodel}] 検索中...")
            
            try:
                # types + tags の組み合わせで検索
                response = requests.get(
                    'https://civitai.com/api/v1/models',
                    headers=headers,
                    params={
                        'types': model_type,
                        'tag': basemodel,  # tagsではなくtag
                        'limit': 5
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data and len(data['items']) > 0:
                        total = data.get('metadata', {}).get('totalItems', 0)
                        
                        # 実際のbaseModelを確認
                        actual_basemodels = []
                        for item in data['items'][:3]:
                            versions = item.get('modelVersions', [])
                            if versions:
                                base_model = versions[0].get('baseModel', 'unknown')
                                actual_basemodels.append(base_model)
                        
                        results[model_type][basemodel] = {
                            'total': total,
                            'actual_basemodels': actual_basemodels
                        }
                        
                        print(f"    ✅ {total:,}個のモデル")
                        print(f"    実際のbaseModel: {list(set(actual_basemodels))}")
                    else:
                        print(f"    ❌ 結果なし")
                        results[model_type][basemodel] = {'total': 0, 'actual_basemodels': []}
                else:
                    print(f"    ❌ HTTP {response.status_code}")
                    results[model_type][basemodel] = {'total': -1, 'actual_basemodels': []}
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[model_type][basemodel] = {'total': -1, 'actual_basemodels': []}
            
            time.sleep(1)  # レート制限対策
    
    return results

def test_alternative_search_methods():
    """代替検索方法のテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    print("\n🔬 代替検索方法のテスト")
    print("=" * 60)
    
    # 1. tags複数形のテスト
    print("\n1. tags パラメータ (複数形)")
    try:
        response = requests.get(
            'https://civitai.com/api/v1/models',
            headers=headers,
            params={
                'types': 'Checkpoint',
                'tags': 'illustrious',
                'limit': 3
            },
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            total = data.get('metadata', {}).get('totalItems', 0)
            print(f"   結果: {total}個")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(1)
    
    # 2. baseModel フィールドでの検索テスト
    print("\n2. baseModel パラメータ (直接)")
    try:
        response = requests.get(
            'https://civitai.com/api/v1/models',
            headers=headers,
            params={
                'types': 'Checkpoint',
                'baseModel': 'Illustrious',
                'limit': 3
            },
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            total = data.get('metadata', {}).get('totalItems', 0)
            print(f"   結果: {total}個")
        
    except Exception as e:
        print(f"   Error: {e}")

def main():
    print("🎯 CivitAI API baseModel検索戦略調査")
    print("=" * 60)
    
    # メイン検索テスト
    results = test_basemodel_tags_search()
    
    # 代替方法テスト
    test_alternative_search_methods()
    
    # 結果サマリー
    print("\n📋 検索結果サマリー:")
    print("=" * 60)
    
    for model_type, basemodel_results in results.items():
        print(f"\n{model_type}:")
        for basemodel, result in basemodel_results.items():
            if result['total'] > 0:
                print(f"  ✅ {basemodel}: {result['total']:,}個")
            elif result['total'] == 0:
                print(f"  ❌ {basemodel}: 結果なし")
            else:
                print(f"  ⚠️ {basemodel}: エラー")
    
    # 結果保存
    import json
    with open('basemodel_search_strategy_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: basemodel_search_strategy_results.json")

if __name__ == "__main__":
    main()