#!/usr/bin/env python3
"""
複数のCivitAI URLからモデル情報を一括取得するスクリプト

Example usage:
    python batch_url_collector.py urls.txt
    python batch_url_collector.py urls.txt --export-html
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.client import CivitaiClient
from src.core.enhanced_url_collector import EnhancedURLCollector


def collect_models_from_urls(urls_file: str, 
                           api_key: str, 
                           validate_urls: bool = False,
                           export_html: bool = False,
                           output_dir: str = "outputs/enhanced") -> None:
    """
    URLファイルからモデル情報を一括取得
    
    Args:
        urls_file: URL一覧ファイル（1行に1URL）
        api_key: CivitAI APIキー
        validate_urls: ダウンロードURL検証の有無
        export_html: HTML形式エクスポートの有無
        output_dir: 出力ディレクトリ
    """
    print(f"🔍 URLファイルからモデル情報を一括取得: {urls_file}")
    
    # URLファイル読み込み
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"❌ URLファイルが見つかりません: {urls_file}")
        sys.exit(1)
    
    if not urls:
        print("❌ 有効なURLがファイルにありません")
        sys.exit(1)
    
    print(f"📋 {len(urls)}個のURLを検出")
    
    # クライアント初期化
    client = CivitaiClient(api_key)
    enhanced_collector = EnhancedURLCollector(api_key=api_key)
    enhanced_collector.output_dir = Path(output_dir)
    enhanced_collector.output_dir.mkdir(parents=True, exist_ok=True)
    
    # モデル情報収集
    all_model_data = []
    successful_count = 0
    failed_count = 0
    
    for i, url in enumerate(urls, 1):
        print(f"\n📈 進行状況: {i}/{len(urls)} - {url}")
        
        try:
            model_data = client.get_model_from_url(url)
            all_model_data.append(model_data)
            successful_count += 1
            
            print(f"✅ 成功: {model_data.get('name', 'Unknown')} (ID: {model_data.get('id')})")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ 失敗: {e}")
            continue
    
    print(f"\n📊 取得結果: 成功 {successful_count}個, 失敗 {failed_count}個")
    
    if not all_model_data:
        print("❌ 取得できたモデルがありません")
        return
    
    # 拡張情報に変換
    print("\n🔄 拡張モデル情報を生成中...")
    model_infos = enhanced_collector.collect_enhanced_model_info(all_model_data)
    
    if validate_urls:
        print("🔍 ダウンロードURL検証中...")
        model_infos = enhanced_collector.validate_download_urls(model_infos)
    
    if model_infos:
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"batch_url_collection_{timestamp}"
        
        # エクスポート
        print("\n📁 結果をエクスポート中...")
        exported_files = enhanced_collector.export_all_formats(model_infos, base_filename)
        
        print(f"📊 CSV: {exported_files['csv']}")
        print(f"📋 JSON: {exported_files['json']}")
        
        if export_html:
            print(f"🌐 HTML: {exported_files['html']}")
        
        # サマリー表示
        print(f"\n✅ 一括取得完了!")
        print(f"📊 総モデル数: {len(model_infos)}")
        print(f"👥 作成者: {len(set(info.creator for info in model_infos))}人")
        print(f"🏷️ モデルタイプ: {', '.join(set(info.model_type for info in model_infos))}")
        
        # トップダウンロードモデル
        top_downloads = sorted(model_infos, key=lambda x: x.download_count or 0, reverse=True)[:3]
        print(f"\n🔥 トップダウンロード:")
        for i, model in enumerate(top_downloads, 1):
            print(f"   {i}. {model.model_name} - {model.download_count}ダウンロード")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="CivitAI URLファイルからモデル情報を一括取得"
    )
    
    parser.add_argument(
        "urls_file",
        help="URL一覧ファイル（1行に1URL、#で始まる行はコメント）"
    )
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help="ダウンロードURLの検証を実行"
    )
    parser.add_argument(
        "--export-html",
        action="store_true",
        help="HTML形式でエクスポート"
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/enhanced",
        help="出力ディレクトリ (default: outputs/enhanced)"
    )
    
    args = parser.parse_args()
    
    # API キー取得
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("❌ エラー: CIVITAI_API_KEY環境変数を設定してください")
        sys.exit(1)
    
    # 一括取得実行
    collect_models_from_urls(
        urls_file=args.urls_file,
        api_key=api_key,
        validate_urls=args.validate_urls,
        export_html=args.export_html,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()