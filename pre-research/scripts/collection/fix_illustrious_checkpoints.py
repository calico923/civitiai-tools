#!/usr/bin/env python3
"""illustriousチェックポイントを正しいページネーションで取得"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def main():
    print("=== illustriousチェックポイント修正版取得 ===")
    
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
        
        # illustriousタグのcheckpointを全て取得
        print("\n2. illustriousチェックポイントを取得中（カーソルベースページネーション使用）...")
        print("   これには数分かかる可能性があります...")
        
        all_illustrious_checkpoints = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="illustrious",
            sort="Highest Rated",
            limit=100,
            max_pages=30  # 最大3000個まで取得
        )
        
        print(f"\n✅ illustriousチェックポイント取得完了: {len(all_illustrious_checkpoints)}個")
        
        # URL収集器の初期化
        collector = URLCollector()
        
        # URL情報を収集
        urls = collector.collect_model_urls(all_illustrious_checkpoints)
        print(f"ダウンロードURL: {len(urls)}個")
        
        # ファイル出力
        filename_base = "illustrious_checkpoints_fixed_cursor"
        
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        
        print(f"\n📁 出力ファイル:")
        print(f"  CSV:  {csv_file}")
        print(f"  JSON: {json_file}")
        print(f"  TXT:  {text_file}")
        
        # 結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 illustriousチェックポイント取得結果")
        print(f"{'='*60}")
        
        print(f"取得チェックポイント数: {len(all_illustrious_checkpoints):,}個")
        print(f"ダウンロードURL数: {len(urls):,}個")
        
        # 以前の結果と比較
        print(f"\n📈 以前の結果との比較:")
        print(f"  以前: 100個 → 現在: {len(all_illustrious_checkpoints):,}個")
        if len(all_illustrious_checkpoints) > 100:
            improvement = len(all_illustrious_checkpoints) - 100
            print(f"  改善: {improvement:,}個増加 ({(improvement / 100 * 100):.1f}%向上)")
        
        # サンプル表示
        print(f"\n📊 サンプルチェックポイント（上位10個）:")
        for i, model in enumerate(all_illustrious_checkpoints[:10], 1):
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
        
        # 異なるソート順でも取得してみる
        print(f"\n3. Most Downloaded順でも確認中...")
        
        most_downloaded = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="illustrious",
            sort="Most Downloaded",
            limit=100,
            max_pages=10  # 最大1000個
        )
        
        print(f"Most Downloaded順: {len(most_downloaded)}個")
        
        # Most Downloaded版も出力
        if most_downloaded:
            urls_downloaded = collector.collect_model_urls(most_downloaded)
            
            csv_file_dl = collector.export_to_csv(urls_downloaded, "illustrious_checkpoints_most_downloaded_fixed.csv")
            json_file_dl = collector.export_to_json(urls_downloaded, "illustrious_checkpoints_most_downloaded_fixed.json")
            text_file_dl = collector.export_to_text(urls_downloaded, "illustrious_checkpoints_most_downloaded_fixed.txt")
            
            print(f"  Most Downloaded版ファイル:")
            print(f"    CSV:  {csv_file_dl}")
            print(f"    JSON: {json_file_dl}")
            print(f"    TXT:  {text_file_dl}")
        
        print(f"\n✅ illustriousチェックポイントの修正取得が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()