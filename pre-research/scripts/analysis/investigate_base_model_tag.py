#!/usr/bin/env python3
"""base modelタグとillustriousタグの組み合わせ検索を調査"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient


def test_different_search_combinations():
    """異なる検索条件を試してillustriousチェックポイントを調査"""
    
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== illustriousチェックポイント詳細調査 ===\n")
    
    search_combinations = [
        {
            "name": "1. illustriousタグのみ",
            "params": {"types": ["Checkpoint"], "tag": "illustrious", "sort": "Most Downloaded"}
        },
        {
            "name": "2. base modelタグのみ", 
            "params": {"types": ["Checkpoint"], "tag": "base model", "sort": "Most Downloaded"}
        },
        {
            "name": "3. illustriousクエリ検索",
            "params": {"types": ["Checkpoint"], "query": "illustrious", "sort": "Most Downloaded"}
        },
        {
            "name": "4. base modelクエリ検索",
            "params": {"types": ["Checkpoint"], "query": "base model", "sort": "Most Downloaded"}
        },
        {
            "name": "5. タグなしでCheckpointのみ（サンプル）",
            "params": {"types": ["Checkpoint"], "sort": "Most Downloaded"}
        }
    ]
    
    results = {}
    
    for combination in search_combinations:
        print(f"{combination['name']}")
        print("-" * 50)
        
        try:
            # 最初の数ページを取得
            all_models = client.search_models_with_cursor(
                **combination['params'],
                limit=100,
                max_pages=10  # 最大1000個
            )
            
            print(f"取得数: {len(all_models)}個")
            
            # illustriousに関連するモデルを数える
            illustrious_count = 0
            for model in all_models:
                name = model.get('name', '').lower()
                tags = [tag.lower() for tag in model.get('tags', [])]
                description = model.get('description', '').lower()
                
                if ('illustrious' in name or 
                    'illustrious' in tags or 
                    'illustrious' in description):
                    illustrious_count += 1
            
            print(f"illustrious関連: {illustrious_count}個")
            
            # サンプル表示（illustrious関連のみ）
            print(f"サンプル（illustrious関連のみ）:")
            count = 0
            for model in all_models:
                if count >= 5:
                    break
                    
                name = model.get('name', '').lower()
                tags = [tag.lower() for tag in model.get('tags', [])]
                description = model.get('description', '').lower()
                
                if ('illustrious' in name or 
                    'illustrious' in tags or 
                    'illustrious' in description):
                    actual_name = model.get('name', 'Unknown')
                    actual_tags = ', '.join(model.get('tags', [])[:3])
                    print(f"  {count+1}. {actual_name}")
                    print(f"     タグ: {actual_tags}")
                    count += 1
            
            results[combination['name']] = {
                'total': len(all_models),
                'illustrious_related': illustrious_count
            }
            
        except Exception as e:
            print(f"エラー: {e}")
            results[combination['name']] = {'total': 0, 'illustrious_related': 0}
        
        print("\n")
    
    # 結果サマリー
    print("=" * 60)
    print("🎯 調査結果サマリー")
    print("=" * 60)
    
    for name, result in results.items():
        print(f"{name}")
        print(f"  総数: {result['total']}個")
        print(f"  illustrious関連: {result['illustrious_related']}個")
        print()
    
    # 複数タグ検索のテスト
    print("\n" + "=" * 60)
    print("🔍 複数条件検索テスト")
    print("=" * 60)
    
    try:
        print("base model + illustrious の組み合わせ検索...")
        
        # base modelタグで検索してillustriousでフィルタ
        base_model_checkpoints = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=20  # 最大2000個
        )
        
        print(f"base modelタグでの総取得数: {len(base_model_checkpoints)}個")
        
        # illustriousを含むものをフィルタ
        illustrious_base_models = []
        for model in base_model_checkpoints:
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            description = model.get('description', '').lower()
            
            if ('illustrious' in name or 
                'illustrious' in tags or 
                'illustrious' in description):
                illustrious_base_models.append(model)
        
        print(f"base model + illustrious: {len(illustrious_base_models)}個")
        
        # サンプル表示
        print(f"\nbase model + illustriousサンプル（上位10個）:")
        for i, model in enumerate(illustrious_base_models[:10], 1):
            name = model.get('name', 'Unknown')
            tags = ', '.join(model.get('tags', [])[:3])
            print(f"  {i:2d}. {name}")
            print(f"       タグ: {tags}")
        
        print(f"\n🎯 結論:")
        print(f"Webページの500+個に最も近い結果:")
        print(f"base modelタグ検索 → illustriousフィルタ: {len(illustrious_base_models)}個")
        
    except Exception as e:
        print(f"複数条件検索エラー: {e}")


if __name__ == "__main__":
    test_different_search_combinations()