#!/usr/bin/env python3
"""URL収集機能のデモンストレーション"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.url_collector import URLCollector
from tests.fixtures.sample_models import VALID_MODEL_DATA

def main():
    print("=== Civitai URL Collector Demo ===\n")
    
    # URLCollectorの初期化
    collector = URLCollector()
    print(f"Output directory: {collector.output_dir}")
    
    # モデルデータからURL収集
    print(f"\nProcessing {len(VALID_MODEL_DATA)} sample models...")
    urls = collector.collect_model_urls(VALID_MODEL_DATA)
    print(f"Collected {len(urls)} URLs")
    
    # 各形式での出力
    print("\nExporting URLs in multiple formats:")
    
    # テキスト形式
    text_file = collector.export_to_text(urls, "demo_urls.txt")
    print(f"✓ Text format: {text_file}")
    
    # CSV形式
    csv_file = collector.export_to_csv(urls, "demo_urls.csv")
    print(f"✓ CSV format: {csv_file}")
    
    # JSON形式
    json_file = collector.export_to_json(urls, "demo_urls.json")
    print(f"✓ JSON format: {json_file}")
    
    # URLの詳細表示
    print("\n=== Collected URLs ===")
    for i, url in enumerate(urls, 1):
        print(f"\n{i}. {url.model_name}")
        print(f"   Type: {url.model_type}")
        print(f"   Download URL: {url.download_url}")
        print(f"   File Size: {url.file_size / (1024*1024):.2f} MB")
        print(f"   Tags: {', '.join(url.tags)}")
        print(f"   Creator: {url.creator}")
    
    print(f"\n=== Demo Complete ===")
    print(f"Check the outputs directory: {collector.output_dir}")

if __name__ == "__main__":
    main()