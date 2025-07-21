#!/usr/bin/env python3
"""pony, noobai, illustriousの全チェックポイント数を2つの方法で確認"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient


def count_models_by_tag(client, tag_name, model_type="Checkpoint", max_pages=5):
    """指定タグで直接検索"""
    try:
        models = client.search_models_with_cursor(
            types=[model_type],
            tag=tag_name,
            sort="Most Downloaded",
            limit=100,
            max_pages=max_pages
        )
        return len(models), models
    except Exception as e:
        print(f"  エラー: {e}")
        return 0, []


def count_models_from_base_model(client, target_name, max_pages=15):
    """base modelタグから検索して対象でフィルター"""
    try:
        print(f"    base modelタグから取得中（最大{max_pages}ページ）...")
        all_base_models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=max_pages
        )
        
        print(f"    base model総数: {len(all_base_models)}個")
        
        # 対象名でフィルタリング
        filtered = []
        target_lower = target_name.lower()
        
        for model in all_base_models:
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            description = model.get('description', '').lower()
            
            if (target_lower in name or 
                target_lower in tags or 
                target_lower in description):
                filtered.append(model)
        
        return len(filtered), filtered
        
    except Exception as e:
        print(f"  エラー: {e}")
        return 0, []


def main():
    print("=== 全ベースモデルチェックポイント数比較調査 ===")
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    try:
        # APIクライアントの初期化
        print("\n1. Civitai APIクライアントを初期化中...")
        client = CivitaiClient(api_key)
        
        # 調査対象
        base_models = ['pony', 'illustrious', 'noobai']
        results = {}
        
        for base_model in base_models:
            print(f"\n{'='*50}")
            print(f"🔍 {base_model.upper()} チェックポイント調査")
            print(f"{'='*50}")
            
            # 方法1: 直接タグ検索
            print(f"方法1: {base_model}タグで直接検索")
            direct_count, direct_models = count_models_by_tag(client, base_model, max_pages=5)
            print(f"  結果: {direct_count}個")
            
            # 方法2: base modelタグから検索
            print(f"方法2: base modelタグから{base_model}でフィルター")
            filtered_count, filtered_models = count_models_from_base_model(client, base_model, max_pages=15)
            print(f"  結果: {filtered_count}個")
            
            # 結果保存
            results[base_model] = {
                'direct_tag': direct_count,
                'from_base_model': filtered_count,
                'direct_models': direct_models,
                'filtered_models': filtered_models
            }
            
            # サンプル表示（base modelからのフィルター結果）
            if filtered_models:
                print(f"  📊 base modelからの{base_model}サンプル（上位5個）:")
                for i, model in enumerate(filtered_models[:5], 1):
                    name = model.get('name', 'Unknown')
                    tags = ', '.join(model.get('tags', [])[:3])
                    print(f"    {i}. {name}")
                    print(f"       タグ: {tags}")
        
        # 結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 全ベースモデル調査結果サマリー")
        print(f"{'='*60}")
        
        print(f"{'モデル名':<12} {'直接タグ':<10} {'base model経由':<15} {'推定合計':<10} {'増加率'}")
        print(f"{'-'*60}")
        
        for base_model in base_models:
            result = results[base_model]
            direct = result['direct_tag']
            filtered = result['from_base_model']
            estimated_total = direct + filtered  # 重複があるため実際はもう少し少ない
            
            if direct > 0:
                increase_rate = f"{(filtered / direct * 100):.1f}%"
            else:
                increase_rate = "N/A"
            
            print(f"{base_model:<12} {direct:<10} {filtered:<15} {estimated_total:<10} {increase_rate}")
        
        # 詳細分析
        print(f"\n📈 詳細分析:")
        for base_model in base_models:
            result = results[base_model]
            direct = result['direct_tag']
            filtered = result['from_base_model']
            
            print(f"\n{base_model.upper()}:")
            print(f"  直接タグ検索: {direct}個")
            print(f"  base model経由: {filtered}個")
            
            if filtered > direct:
                additional = filtered - direct
                print(f"  追加発見: {additional}個 (base model経由で{additional}個多く発見)")
            elif filtered < direct:
                print(f"  注意: base model経由の方が少ない（タグ付けの違い）")
            else:
                print(f"  両方法で同数")
        
        # 推奨事項
        print(f"\n💡 推奨事項:")
        print(f"  1. 各ベースモデルで両方の検索方法を使用")
        print(f"  2. 結果を統合して重複除去")
        print(f"  3. より多くのページを取得すればさらに増加の可能性")
        print(f"  4. illustriousと同様にpony, noobaiでも取得漏れがある可能性")
        
        print(f"\n✅ 全ベースモデルの調査が完了しました！")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()