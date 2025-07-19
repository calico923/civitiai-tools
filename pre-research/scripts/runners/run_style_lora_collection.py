#!/usr/bin/env python3
"""個別ベースモデルのstyle LoRA収集実行スクリプト"""

import os
import sys
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def run_style_lora_collection(base_model: str = None):
    """指定されたベースモデルのstyle LoRAを収集"""
    
    # 環境変数の読み込み
    load_dotenv('.env.style_search')
    load_dotenv()  # デフォルトの.envも読み込み
    
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    print(f"=== style LoRA収集開始 ===")
    if base_model:
        print(f"対象ベースモデル: {base_model}")
    else:
        print(f"対象: 全styleタグLoRA")
    
    try:
        # APIクライアントの初期化
        client = CivitaiClient(api_key)
        collector = URLCollector()
        
        # 検索実行
        max_pages = int(os.getenv('MAX_PAGES', 5))
        
        if base_model:
            # 特定ベースモデルのstyle LoRA検索
            print(f"\n{base_model}ベースのstyle LoRAを検索中...")
            models = client.search_models_extended(
                tag="style",
                model_type="LORA",
                additional_tag=base_model,
                max_requests=max_pages,
                sort="Highest Rated"
            )
            filename_base = f"style_lora_{base_model}_targeted"
        else:
            # 全styleタグLoRA検索
            print(f"\n全styleタグLoRAを検索中...")
            models = client.search_models_extended(
                tag="style",
                model_type="LORA", 
                max_requests=max_pages,
                sort="Highest Rated"
            )
            filename_base = "style_lora_all_targeted"
        
        if not models:
            print("該当するモデルが見つかりませんでした")
            return
        
        print(f"発見されたモデル数: {len(models)}")
        
        # URL収集
        urls = collector.collect_model_urls(models)
        print(f"ダウンロードURL数: {len(urls)}")
        
        # ファイル出力
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        
        print(f"\n結果ファイル:")
        print(f"  CSV:  {csv_file}")
        print(f"  JSON: {json_file}")
        print(f"  TXT:  {text_file}")
        
        # サンプル表示
        print(f"\n=== サンプルモデル（上位5個） ===")
        for i, model in enumerate(models[:5], 1):
            name = model.get('name', 'Unknown')
            tags = ', '.join(model.get('tags', [])[:3])
            creator = model.get('creator', {})
            if isinstance(creator, dict):
                creator_name = creator.get('username', 'Unknown')
            else:
                creator_name = str(creator)
            
            print(f"{i}. {name}")
            print(f"   タグ: {tags}")
            print(f"   作成者: {creator_name}")
            print()
        
        print(f"✅ 収集完了！")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='style LoRA収集ツール')
    parser.add_argument('--base-model', '-b', 
                       choices=['pony', 'illustrious', 'noobai'],
                       help='対象ベースモデル (指定しない場合は全style LoRA)')
    parser.add_argument('--all-separate', '-a', action='store_true',
                       help='全ベースモデルを個別に実行')
    
    args = parser.parse_args()
    
    if args.all_separate:
        # 全ベースモデルを個別実行
        base_models = ['pony', 'illustrious', 'noobai']
        for base_model in base_models:
            print(f"\n{'='*60}")
            run_style_lora_collection(base_model)
            print(f"{'='*60}")
    else:
        # 単一実行
        run_style_lora_collection(args.base_model)


if __name__ == "__main__":
    main()