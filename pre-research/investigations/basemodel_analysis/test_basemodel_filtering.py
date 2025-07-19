#!/usr/bin/env python3
"""
baseModelフィルタリングの実用的な解決策を探る
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_practical_basemodel_filtering():
    """実用的なbaseModelフィルタリング手法をテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    print("🎯 実用的なbaseModelフィルタリング手法")
    print("=" * 60)
    
    # 1. 大量取得 → クライアントサイドフィルタリング
    print("\n1. 大量取得 → クライアントサイドフィルタリング")
    
    target_basemodels = ["Illustrious", "Pony", "NoobAI", "SDXL"]
    model_types = ["Checkpoint", "LORA", "LoCon"]
    
    results = {}
    
    for model_type in model_types:
        print(f"\n📊 {model_type} の分析:")
        results[model_type] = {}
        
        try:
            # 大量のデータを取得
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={
                    'types': model_type,
                    'limit': 100,  # 大量取得
                    'sort': 'Highest Rated'
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                print(f"  取得データ: {len(items)}個")
                
                # baseModel別に分類
                basemodel_counts = {}
                basemodel_models = {}
                
                for item in items:
                    versions = item.get('modelVersions', [])
                    if versions:
                        base_model = versions[0].get('baseModel', 'Unknown')
                        
                        if base_model not in basemodel_counts:
                            basemodel_counts[base_model] = 0
                            basemodel_models[base_model] = []
                        
                        basemodel_counts[base_model] += 1
                        basemodel_models[base_model].append({
                            'name': item.get('name', 'Unknown'),
                            'id': item.get('id', 0)
                        })
                
                results[model_type] = {
                    'total_retrieved': len(items),
                    'basemodel_distribution': basemodel_counts,
                    'sample_models': basemodel_models
                }
                
                # 結果表示
                print(f"  baseModel分布:")
                for base_model, count in sorted(basemodel_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(items)) * 100
                    print(f"    - {base_model}: {count}個 ({percentage:.1f}%)")
                
                # 目標baseModelの抽出例
                for target in target_basemodels:
                    if target in basemodel_models:
                        examples = basemodel_models[target][:3]
                        print(f"  {target}の例:")
                        for example in examples:
                            print(f"    - {example['name']} (ID: {example['id']})")
                
            else:
                print(f"  ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(2)  # レート制限対策
    
    return results

def demonstrate_client_side_filtering():
    """クライアントサイドフィルタリングの実装例"""
    
    print(f"\n💡 クライアントサイドフィルタリング実装例")
    print("=" * 60)
    
    example_code = '''
def filter_models_by_basemodel(models, target_basemodel):
    """
    取得したモデルリストを特定のbaseModelでフィルタリング
    """
    filtered_models = []
    
    for model in models:
        versions = model.get('modelVersions', [])
        if versions:
            base_model = versions[0].get('baseModel', '')
            
            # 大文字小文字を無視した比較
            if target_basemodel.lower() in base_model.lower():
                filtered_models.append(model)
    
    return filtered_models

# 使用例
def get_illustrious_checkpoints(client, limit=200):
    """Illustrious Checkpointのみを取得"""
    
    # 1. 大量のCheckpointを取得
    all_checkpoints = client.search_models(
        types='Checkpoint',
        limit=limit,
        sort='Highest Rated'
    )
    
    # 2. Illustriousのみをフィルタリング
    illustrious_checkpoints = filter_models_by_basemodel(
        all_checkpoints['items'],
        'Illustrious'
    )
    
    return illustrious_checkpoints

# 効率的なページネーション付きフィルタリング
def get_basemodel_models_paginated(client, model_type, target_basemodel, target_count=100):
    """ページネーションを使った効率的なbaseModelフィルタリング"""
    
    filtered_models = []
    cursor = None
    
    while len(filtered_models) < target_count:
        # APIからデータ取得
        params = {
            'types': model_type,
            'limit': 100,
            'sort': 'Highest Rated'
        }
        
        if cursor:
            params['cursor'] = cursor
        
        response = client.search_models(**params)
        items = response.get('items', [])
        
        if not items:
            break
        
        # baseModelでフィルタリング
        batch_filtered = filter_models_by_basemodel(items, target_basemodel)
        filtered_models.extend(batch_filtered)
        
        # 次のページのカーソル取得
        cursor = response.get('metadata', {}).get('nextCursor')
        if not cursor:
            break
    
    return filtered_models[:target_count]
'''
    
    print(example_code)

def main():
    print("🚀 CivitAI API baseModel問題の実用的解決策")
    print("=" * 60)
    
    # 実際のテスト実行
    results = test_practical_basemodel_filtering()
    
    # 実装例の提示
    demonstrate_client_side_filtering()
    
    # 結果保存
    import json
    with open('basemodel_filtering_solution.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: basemodel_filtering_solution.json")
    
    # 推奨手法のまとめ
    print(f"\n🎯 推奨解決策:")
    print("1. APIでタイプ別に大量データを取得（limit=100-200）")
    print("2. クライアントサイドでbaseModelフィルタリング")
    print("3. 必要に応じてページネーションで追加取得")
    print("4. 複数バッチでの効率的な処理")

if __name__ == "__main__":
    main()