#!/usr/bin/env python3
"""2つの検索方法を統合してベースモデルチェックポイントを完全取得"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Set

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def collect_complete_checkpoints(client: CivitaiClient, base_model: str, max_pages_direct: int = 5, max_pages_base: int = 30) -> List[Dict]:
    """2つの方法でベースモデルチェックポイントを完全取得"""
    
    all_models = []
    seen_ids = set()  # 重複除去用
    
    print(f"\n{'='*60}")
    print(f"🔍 {base_model.upper()} チェックポイント完全取得")
    print(f"{'='*60}")
    
    # 方法1: 直接タグ検索
    print(f"1. {base_model}タグで直接検索中...")
    try:
        direct_models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag=base_model,
            sort="Most Downloaded",
            limit=100,
            max_pages=max_pages_direct
        )
        
        print(f"   直接タグ検索結果: {len(direct_models)}個")
        
        # 重複除去しながら追加
        for model in direct_models:
            model_id = model.get('id')
            if model_id and model_id not in seen_ids:
                all_models.append(model)
                seen_ids.add(model_id)
        
        print(f"   追加済み: {len(all_models)}個")
        
    except Exception as e:
        print(f"   直接タグ検索エラー: {e}")
    
    # 方法2: base modelタグから検索してフィルタリング
    print(f"\n2. base modelタグから{base_model}検索中...")
    try:
        base_model_checkpoints = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=max_pages_base
        )
        
        print(f"   base model総取得数: {len(base_model_checkpoints)}個")
        
        # base_modelでフィルタリング
        filtered_models = []
        base_model_lower = base_model.lower()
        
        for model in base_model_checkpoints:
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            description = model.get('description', '').lower()
            
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
    return all_models


def main():
    print("=== ベースモデルチェックポイント完全取得 ===")
    print("2つの検索方法を統合してWebページと同等の結果を取得")
    
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
        collector = URLCollector()
        
        # 対象ベースモデル
        base_models = ['pony', 'illustrious', 'noobai']
        all_results = {}
        
        # 各ベースモデルの完全取得
        for base_model in base_models:
            complete_models = collect_complete_checkpoints(
                client, 
                base_model, 
                max_pages_direct=5,   # 直接タグ検索: 最大500個
                max_pages_base=30     # base model検索: 最大3000個
            )
            
            if complete_models:
                # URL収集
                urls = collector.collect_model_urls(complete_models)
                print(f"   ダウンロードURL: {len(urls)}個")
                
                # ファイル出力
                filename_base = f"{base_model}_checkpoints_complete"
                
                csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
                json_file = collector.export_to_json(urls, f"{filename_base}.json")
                text_file = collector.export_to_text(urls, f"{filename_base}.txt")
                
                print(f"   📁 ファイル出力:")
                print(f"     CSV:  {csv_file}")
                print(f"     JSON: {json_file}")
                print(f"     TXT:  {text_file}")
                
                # 結果保存
                all_results[base_model] = {
                    'models': complete_models,
                    'urls': urls,
                    'count': len(complete_models)
                }
                
                # サンプル表示
                print(f"   📊 {base_model.upper()}サンプル（上位5個）:")
                for i, model in enumerate(complete_models[:5], 1):
                    name = model.get('name', 'Unknown')
                    tags = ', '.join(model.get('tags', [])[:3])
                    print(f"     {i}. {name}")
                    print(f"        タグ: {tags}")
            else:
                print(f"   ❌ {base_model}チェックポイントが見つかりませんでした")
                all_results[base_model] = {'models': [], 'urls': [], 'count': 0}
        
        # 統合ファイル作成
        print(f"\n{'='*60}")
        print(f"📄 統合ファイル作成中...")
        print(f"{'='*60}")
        
        all_urls = []
        for result in all_results.values():
            all_urls.extend(result['urls'])
        
        if all_urls:
            # 重複除去（URLベース）
            seen_urls = set()
            unique_urls = []
            for url_info in all_urls:
                url = url_info.download_url
                if url not in seen_urls:
                    unique_urls.append(url_info)
                    seen_urls.add(url)
            
            print(f"統合前: {len(all_urls)}個")
            print(f"重複除去後: {len(unique_urls)}個")
            
            unified_csv = collector.export_to_csv(unique_urls, "all_base_model_checkpoints_complete.csv")
            unified_json = collector.export_to_json(unique_urls, "all_base_model_checkpoints_complete.json")
            unified_txt = collector.export_to_text(unique_urls, "all_base_model_checkpoints_complete.txt")
            
            print(f"統合CSV:  {unified_csv}")
            print(f"統合JSON: {unified_json}")
            print(f"統合TXT:  {unified_txt}")
        
        # 最終結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 最終結果サマリー（完全版）")
        print(f"{'='*60}")
        
        print(f"{'ベースモデル':<12} {'以前':<8} {'現在':<8} {'増加数':<8} {'増加率'}")
        print(f"{'-'*55}")
        
        previous_counts = {'pony': 97, 'illustrious': 243, 'noobai': 47}  # 直接タグ検索の結果
        total_previous = sum(previous_counts.values())
        total_current = 0
        
        for base_model in base_models:
            result = all_results[base_model]
            current = result['count']
            previous = previous_counts[base_model]
            increase = current - previous
            increase_rate = f"{(increase / previous * 100):.1f}%" if previous > 0 else "N/A"
            
            print(f"{base_model:<12} {previous:<8} {current:<8} {increase:<8} {increase_rate}")
            total_current += current
        
        print(f"{'-'*55}")
        total_increase = total_current - total_previous
        total_increase_rate = f"{(total_increase / total_previous * 100):.1f}%"
        print(f"{'合計':<12} {total_previous:<8} {total_current:<8} {total_increase:<8} {total_increase_rate}")
        
        # Webページとの比較
        print(f"\n🌐 推定Webページ数との比較:")
        estimated_web_counts = {'pony': 1000, 'illustrious': 500, 'noobai': 200}  # 推定値
        for base_model in base_models:
            current = all_results[base_model]['count']
            estimated = estimated_web_counts[base_model]
            coverage = f"{(current / estimated * 100):.1f}%" if estimated > 0 else "N/A"
            print(f"  {base_model}: {current}個 / 推定{estimated}個 (カバー率: {coverage})")
        
        print(f"\n✅ 全ベースモデルの完全取得が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()