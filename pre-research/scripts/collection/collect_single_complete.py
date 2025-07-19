#!/usr/bin/env python3
"""1つのベースモデルの完全チェックポイントを取得（効率版）"""

import os
import sys
from pathlib import Path
from typing import List, Dict

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def main():
    print("=== 単一ベースモデル完全取得（効率版）===")
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    # 対象ベースモデルを選択（最も影響が大きいponyから開始）
    base_model = "pony"
    
    try:
        # APIクライアントの初期化
        print(f"\n1. Civitai APIクライアントを初期化中...")
        client = CivitaiClient(api_key)
        collector = URLCollector()
        
        all_models = []
        seen_ids = set()
        
        print(f"\n{'='*50}")
        print(f"🔍 {base_model.upper()} チェックポイント完全取得")
        print(f"{'='*50}")
        
        # 方法1: 直接タグ検索
        print(f"\n2. {base_model}タグで直接検索中...")
        try:
            direct_models = client.search_models_with_cursor(
                types=["Checkpoint"],
                tag=base_model,
                sort="Most Downloaded", 
                limit=100,
                max_pages=3  # 効率化のため3ページに制限
            )
            
            print(f"   直接タグ検索結果: {len(direct_models)}個")
            
            # 追加
            for model in direct_models:
                model_id = model.get('id')
                if model_id and model_id not in seen_ids:
                    all_models.append(model)
                    seen_ids.add(model_id)
            
            print(f"   追加済み: {len(all_models)}個")
            
        except Exception as e:
            print(f"   直接タグ検索エラー: {e}")
        
        # 方法2: base modelタグから検索（効率版）
        print(f"\n3. base modelタグから{base_model}検索中（効率版）...")
        try:
            base_model_checkpoints = client.search_models_with_cursor(
                types=["Checkpoint"],
                tag="base model",
                sort="Most Downloaded",
                limit=100,
                max_pages=15  # 効率化のため15ページに制限
            )
            
            print(f"   base model取得数: {len(base_model_checkpoints)}個")
            
            # ponyでフィルタリング
            filtered_models = []
            base_model_lower = base_model.lower()
            
            for model in base_model_checkpoints:
                name = model.get('name', '') or ''
                name = name.lower()
                tags = [tag.lower() for tag in model.get('tags', []) if tag]
                description = model.get('description', '') or ''
                description = description.lower()
                
                if (base_model_lower in name or 
                    base_model_lower in tags or 
                    base_model_lower in description):
                    filtered_models.append(model)
            
            print(f"   {base_model}関連フィルタ結果: {len(filtered_models)}個")
            
            # 重複除去しながら追加
            added_count = 0
            for model in filtered_models:
                model_id = model.get('id')
                if model_id and model_id not in seen_ids:
                    all_models.append(model)
                    seen_ids.add(model_id)
                    added_count += 1
            
            print(f"   新規追加: {added_count}個")
            
        except Exception as e:
            print(f"   base model検索エラー: {e}")
        
        print(f"\n✅ {base_model.upper()}完全取得結果: {len(all_models)}個")
        
        if all_models:
            # URL収集
            print(f"\n4. URL収集中...")
            urls = collector.collect_model_urls(all_models)
            print(f"   ダウンロードURL: {len(urls)}個")
            
            # ファイル出力
            print(f"\n5. ファイル出力中...")
            filename_base = f"{base_model}_checkpoints_complete_efficient"
            
            csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
            json_file = collector.export_to_json(urls, f"{filename_base}.json")
            text_file = collector.export_to_text(urls, f"{filename_base}.txt")
            
            print(f"   📁 出力ファイル:")
            print(f"     CSV:  {csv_file}")
            print(f"     JSON: {json_file}")
            print(f"     TXT:  {text_file}")
            
            # 結果サマリー
            print(f"\n{'='*50}")
            print(f"🎯 {base_model.upper()}取得結果サマリー")
            print(f"{'='*50}")
            
            print(f"以前（直接タグのみ）: 97個")
            print(f"現在（統合方式）: {len(all_models)}個")
            increase = len(all_models) - 97
            if increase > 0:
                increase_rate = (increase / 97 * 100)
                print(f"改善: +{increase}個 ({increase_rate:.1f}%向上)")
            
            # サンプル表示
            print(f"\n📊 サンプルチェックポイント（上位10個）:")
            for i, model in enumerate(all_models[:10], 1):
                name = model.get('name', 'Unknown')
                tags = ', '.join(model.get('tags', [])[:3])
                creator = model.get('creator', {})
                if isinstance(creator, dict):
                    creator_name = creator.get('username', 'Unknown')
                else:
                    creator_name = str(creator)
                
                print(f"{i:2d}. {name}")
                print(f"     タグ: {tags}")
                print(f"     作成者: {creator_name}")
                print()
            
            print(f"✅ {base_model.upper()}チェックポイントの完全取得が完了しました！")
            print(f"出力ディレクトリ: {collector.output_dir}")
            
            # 他のベースモデルへの案内
            print(f"\n💡 次のステップ:")
            print(f"  1. illustriousとnoobaiも同様に実行")
            print(f"  2. 3つのベースモデル結果を統合")
            print(f"  3. 最終的な重複除去とファイル生成")
        
        else:
            print(f"   ❌ {base_model}チェックポイントが見つかりませんでした")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()