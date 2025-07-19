#!/usr/bin/env python3
"""
URL指定でCivitAIモデル情報を取得するスクリプト

Example usage:
    python url_model_collector.py https://civitai.com/models/1369545
    python url_model_collector.py https://civitai.com/models/1369545 --export-html
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


def collect_model_from_url(civitai_url: str, 
                          api_key: str, 
                          validate_urls: bool = False,
                          export_html: bool = False,
                          output_dir: str = "outputs/enhanced") -> None:
    """
    CivitAI URLからモデル情報を取得してエクスポート
    
    Args:
        civitai_url: CivitAI モデルページURL
        api_key: CivitAI APIキー
        validate_urls: ダウンロードURL検証の有無
        export_html: HTML形式エクスポートの有無
        output_dir: 出力ディレクトリ
    """
    print(f"🔍 CivitAI URLからモデル情報を取得中: {civitai_url}")
    
    # クライアント初期化
    client = CivitaiClient(api_key)
    enhanced_collector = EnhancedURLCollector(api_key=api_key)
    enhanced_collector.output_dir = Path(output_dir)
    enhanced_collector.output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # URLからモデル情報を取得
        model_data = client.get_model_from_url(civitai_url)
        print(f"✅ モデル情報取得成功: {model_data.get('name', 'Unknown')}")
        
        # モデル情報の詳細表示
        print(f"📋 モデル詳細:")
        print(f"   ID: {model_data.get('id')}")
        print(f"   名前: {model_data.get('name')}")
        print(f"   タイプ: {model_data.get('type')}")
        print(f"   作成者: {model_data.get('creator', {}).get('username', 'Unknown')}")
        print(f"   タグ: {', '.join(model_data.get('tags', [])[:5])}")
        
        # 拡張情報に変換
        print("\n🔄 拡張モデル情報を生成中...")
        model_infos = enhanced_collector.collect_enhanced_model_info([model_data])
        
        if validate_urls:
            print("🔍 ダウンロードURL検証中...")
            model_infos = enhanced_collector.validate_download_urls(model_infos)
        
        if model_infos:
            # ファイル名生成
            model_name = model_data.get('name', 'unknown').replace(' ', '_').replace('/', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"url_model_{model_name}_{timestamp}"
            
            # エクスポート
            print("\n📁 結果をエクスポート中...")
            exported_files = enhanced_collector.export_all_formats(model_infos, base_filename)
            
            print(f"📊 CSV: {exported_files['csv']}")
            print(f"📋 JSON: {exported_files['json']}")
            
            if export_html:
                print(f"🌐 HTML: {exported_files['html']}")
            
            # サマリー表示
            model_info = model_infos[0]
            print(f"\n✅ 取得完了!")
            print(f"📊 モデル名: {model_info.model_name}")
            print(f"👤 作成者: {model_info.creator}")
            print(f"💾 ファイルサイズ: {model_info.file_size_mb:.1f} MB")
            print(f"⬇️ ダウンロード数: {model_info.download_count}")
            print(f"🔗 ページURL: {model_info.civitai_page_url}")
            print(f"📥 ダウンロードURL: {model_info.download_url}")
            
        else:
            print("❌ モデル情報の処理に失敗しました")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="CivitAI URLからモデル情報を取得"
    )
    
    parser.add_argument(
        "url",
        help="CivitAI モデルページURL (例: https://civitai.com/models/1369545)"
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
    
    # モデル取得実行
    collect_model_from_url(
        civitai_url=args.url,
        api_key=api_key,
        validate_urls=args.validate_urls,
        export_html=args.export_html,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()