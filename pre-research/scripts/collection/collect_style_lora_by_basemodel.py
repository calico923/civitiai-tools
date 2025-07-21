#!/usr/bin/env python3
"""ベースモデル別にstyleタグLoRAを収集するスクリプト"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector
from src.utils.context_manager import ContextManager


def filter_models_by_base_model(models: List[Dict], base_model: str) -> List[Dict]:
    """指定されたベースモデルに関連するモデルをフィルタリング"""
    filtered = []
    base_model_lower = base_model.lower()
    
    for model in models:
        # タグにベースモデル名が含まれているかチェック
        tags = model.get('tags', [])
        tag_match = any(base_model_lower in tag.lower() for tag in tags)
        
        # モデル名にベースモデル名が含まれているかチェック
        model_name = model.get('name', '')
        name_match = base_model_lower in model_name.lower()
        
        # 説明文にベースモデル名が含まれているかチェック
        description = model.get('description', '')
        desc_match = base_model_lower in description.lower()
        
        if tag_match or name_match or desc_match:
            filtered.append(model)
    
    return filtered


def collect_style_lora_for_base_model(client: CivitaiClient, base_model: str, max_pages: int = 5) -> List[Dict]:
    """指定ベースモデルのstyle LoRAを収集"""
    print(f"\n=== {base_model} ベースモデルのstyle LoRA収集 ===")
    
    # 1. styleタグ + ベースモデルタグで直接検索
    print(f"1. {base_model}+styleタグで直接検索中...")
    try:
        models_tagged = client.search_models_extended(
            tag="style", 
            model_type="LORA",
            additional_tag=base_model,
            max_requests=max_pages,
            sort="Highest Rated"
        )
        print(f"   タグ検索結果: {len(models_tagged)}個")
    except Exception as e:
        print(f"   タグ検索エラー: {e}")
        models_tagged = []
    
    # 2. styleタグのみで検索してベースモデルでフィルタリング
    print(f"2. styleタグ検索結果を{base_model}でフィルタリング中...")
    try:
        all_style_models = client.search_models_extended(
            tag="style",
            model_type="LORA", 
            max_requests=max_pages,
            sort="Highest Rated"
        )
        print(f"   全styleタグLoRA: {len(all_style_models)}個")
        
        filtered_models = filter_models_by_base_model(all_style_models, base_model)
        print(f"   {base_model}フィルタ結果: {len(filtered_models)}個")
    except Exception as e:
        print(f"   フィルタリング検索エラー: {e}")
        filtered_models = []
    
    # 3. 結果をマージして重複除去
    all_models = models_tagged + filtered_models
    seen_ids = set()
    unique_models = []
    
    for model in all_models:
        model_id = model.get('id')
        if model_id and model_id not in seen_ids:
            unique_models.append(model)
            seen_ids.add(model_id)
    
    print(f"3. 重複除去後の最終結果: {len(unique_models)}個")
    
    return unique_models


def main():
    print("=== ベースモデル別 style LoRA 収集ツール ===")
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        print(".envファイルでAPIキーを設定してください")
        return
    
    # ベースモデルのリスト
    base_models = ['pony', 'illustrious', 'noobai']
    max_pages = int(os.getenv('MAX_PAGES', 5))
    
    try:
        # APIクライアントの初期化
        print(f"\nCivitai APIクライアントを初期化中...")
        client = CivitaiClient(api_key)
        
        # URL収集器とコンテキストマネージャーの初期化
        collector = URLCollector()
        cm = ContextManager()
        
        all_results = {}
        
        # 各ベースモデルについて検索実行
        for base_model in base_models:
            print(f"\n{'='*50}")
            print(f"🔍 {base_model.upper()} ベースモデルの検索開始")
            print(f"{'='*50}")
            
            models = collect_style_lora_for_base_model(client, base_model, max_pages)
            
            if models:
                # URL情報を収集
                urls = collector.collect_model_urls(models)
                print(f"   ダウンロードURL収集: {len(urls)}個")
                
                # 結果を保存
                all_results[base_model] = {
                    'models': models,
                    'urls': urls,
                    'count': len(models)
                }
                
                # ベースモデル別ファイル出力
                filename_base = f"style_lora_{base_model}_highest_rated"
                
                csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
                json_file = collector.export_to_json(urls, f"{filename_base}.json") 
                text_file = collector.export_to_text(urls, f"{filename_base}.txt")
                
                print(f"   📁 ファイル出力完了:")
                print(f"     CSV:  {csv_file}")
                print(f"     JSON: {json_file}")
                print(f"     TXT:  {text_file}")
                
                # サマリー作成
                summary = cm.create_summary(models, [base_model])
                
                print(f"   📊 {base_model.upper()}統計:")
                print(f"     総数: {summary['total_count']}個")
                print(f"     タイプ別: {summary['by_type']}")
                print(f"     トップ作成者: {list(summary['top_creators'].items())[:3]}")
                
            else:
                print(f"   ❌ {base_model}のstyle LoRAが見つかりませんでした")
                all_results[base_model] = {'models': [], 'urls': [], 'count': 0}
        
        # 全体サマリー表示
        print(f"\n{'='*60}")
        print(f"🎯 最終結果サマリー")
        print(f"{'='*60}")
        
        total_count = 0
        for base_model in base_models:
            count = all_results[base_model]['count']
            total_count += count
            print(f"{base_model.upper():12}: {count:3d}個のstyle LoRA")
        
        print(f"{'総計':>12}: {total_count:3d}個")
        
        # 統合ファイルも作成
        print(f"\n📄 統合結果ファイルを作成中...")
        all_urls = []
        for result in all_results.values():
            all_urls.extend(result['urls'])
        
        if all_urls:
            unified_csv = collector.export_to_csv(all_urls, "style_lora_all_basemodels_highest_rated.csv")
            unified_json = collector.export_to_json(all_urls, "style_lora_all_basemodels_highest_rated.json")
            unified_txt = collector.export_to_text(all_urls, "style_lora_all_basemodels_highest_rated.txt")
            
            print(f"   統合CSV:  {unified_csv}")
            print(f"   統合JSON: {unified_json}")
            print(f"   統合TXT:  {unified_txt}")
        
        print(f"\n✅ 全ベースモデルの収集が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()