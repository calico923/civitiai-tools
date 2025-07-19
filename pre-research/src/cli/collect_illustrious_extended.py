#!/usr/bin/env python3
"""illustrious checkpoint拡張検索スクリプト（タグ＋名前）"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def main():
    print("=== Illustrious Checkpoint 拡張検索 ===\n")
    print("タグと名前の両方でillustriousを検索します")
    
    # 環境変数の読み込み
    load_dotenv()
    
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    print(f"APIキー: {api_key[:8]}...")
    
    try:
        # APIクライアントの初期化
        print("\n1. Civitai APIクライアントを初期化中...")
        client = CivitaiClient(api_key)
        
        # 拡張検索を実行
        print("\n2. illustrious checkpoint拡張検索を実行中...")
        models = client.search_illustrious_checkpoints_extended(max_requests=3)
        
        if not models:
            print("\nillustrious関連checkpointが見つかりませんでした")
            return
        
        # WAI-NSFW-illustrious-SDXLが含まれているか確認
        wai_model = None
        for model in models:
            if model.get('id') == 827184:
                wai_model = model
                print(f"\n✅ WAI-NSFW-illustrious-SDXL (ID: 827184) を発見しました！")
                break
        
        if not wai_model:
            print(f"\n⚠️  WAI-NSFW-illustrious-SDXL (ID: 827184) は見つかりませんでした")
        
        # URL収集器の初期化
        print("\n3. URL収集器を初期化中...")
        collector = URLCollector()
        
        # URLを収集
        print("\n4. ダウンロードURLを収集中...")
        urls = collector.collect_model_urls(models)
        print(f"   {len(urls)}個のダウンロードURLを収集")
        
        # 結果を出力
        print("\n5. 結果をエクスポート中...")
        
        # 各形式で出力
        csv_file = collector.export_to_csv(urls, "illustrious_checkpoints_extended.csv")
        print(f"   CSV: {csv_file}")
        
        json_file = collector.export_to_json(urls, "illustrious_checkpoints_extended.json")
        print(f"   JSON: {json_file}")
        
        text_file = collector.export_to_text(urls, "illustrious_checkpoints_extended.txt")
        print(f"   Text: {text_file}")
        
        # 詳細を表示
        print(f"\n=== 収集結果詳細 ===")
        print(f"総モデル数: {len(urls)}")
        
        # WAI-NSFW-illustrious-SDXLのURL情報を探す
        for url in urls:
            if "WAI-NSFW-illustrious-SDXL" in url.model_name:
                print(f"\n特定モデル情報:")
                print(f"  名前: {url.model_name}")
                print(f"  URL: {url.download_url}")
                print(f"  サイズ: {url.file_size / (1024*1024):.1f} MB")
                break
        
        print(f"\n=== 完了 ===")
        print(f"全ファイルは {collector.output_dir} に保存されました")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()