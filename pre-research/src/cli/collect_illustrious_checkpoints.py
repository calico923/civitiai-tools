#!/usr/bin/env python3
"""illustrious checkpointのmost downloadedモデルのURL収集スクリプト"""

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
    print("=== Illustrious Checkpoint URL収集 ===\n")
    
    # 環境変数の読み込み
    load_dotenv()
    
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        print(".envファイルでAPIキーを設定してください")
        return
    
    print(f"APIキー: {api_key[:8]}...")
    
    try:
        # APIクライアントの初期化
        print("\n1. Civitai APIクライアントを初期化中...")
        client = CivitaiClient(api_key)
        
        # illustrious checkpointを検索
        print("\n2. illustrious checkpointを検索中...")
        print("   - タイプ: Checkpoint")
        print("   - クエリ: illustrious")
        print("   - ソート: Highest Rated")
        
        models = client.search_illustrious_checkpoints(max_requests=3)
        
        if not models:
            print("\nillustrious checkpointが見つかりませんでした")
            return
        
        # URL収集器の初期化
        print("\n3. URL収集器を初期化中...")
        collector = URLCollector()
        
        # URLを収集
        print("\n4. ダウンロードURLを収集中...")
        urls = collector.collect_model_urls(models)
        print(f"   {len(urls)}個のダウンロードURLを収集")
        
        if not urls:
            print("ダウンロード可能なURLが見つかりませんでした")
            return
        
        # 結果を出力
        print("\n5. 結果をエクスポート中...")
        
        # CSV形式で出力
        csv_file = collector.export_to_csv(urls, "illustrious_checkpoints_highest_rated.csv")
        print(f"   CSV: {csv_file}")
        
        # JSON形式でも出力
        json_file = collector.export_to_json(urls, "illustrious_checkpoints_highest_rated.json")
        print(f"   JSON: {json_file}")
        
        # テキスト形式でも出力
        text_file = collector.export_to_text(urls, "illustrious_checkpoints_highest_rated.txt")
        print(f"   Text: {text_file}")
        
        # 詳細を表示
        print(f"\n=== 収集結果詳細 ===")
        print(f"総モデル数: {len(urls)}")
        
        total_size_mb = sum(url.file_size for url in urls) / (1024 * 1024)
        print(f"総ファイルサイズ: {total_size_mb:.1f} MB")
        
        print(f"\n=== トップ10モデル ===")
        for i, url in enumerate(urls[:10], 1):
            print(f"{i:2d}. {url.model_name}")
            print(f"     タイプ: {url.model_type}")
            print(f"     サイズ: {url.file_size / (1024*1024):.1f} MB")
            print(f"     作成者: {url.creator}")
            print(f"     タグ: {', '.join(url.tags[:5])}")
            print(f"     URL: {url.download_url}")
            print()
        
        if len(urls) > 10:
            print(f"（他 {len(urls) - 10} 個のモデル）")
        
        print(f"\n=== 完了 ===")
        print(f"全ファイルは {collector.output_dir} に保存されました")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()