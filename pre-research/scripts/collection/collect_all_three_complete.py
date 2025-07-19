#!/usr/bin/env python3
"""3つのベースモデル全てを順次完全取得"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def collect_single_base_model(client, collector, base_model):
    """単一ベースモデルを2つの方法で取得"""
    
    all_models = []
    seen_ids = set()
    
    print(f"\n{'='*50}")
    print(f"🔍 {base_model.upper()} チェックポイント取得")
    print(f"{'='*50}")
    
    # 方法1: 直接タグ検索
    print(f"1. {base_model}タグで直接検索...")
    try:
        direct_models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag=base_model,
            sort="Most Downloaded", 
            limit=100,
            max_pages=3
        )
        
        print(f"   直接タグ結果: {len(direct_models)}個")
        
        for model in direct_models:
            model_id = model.get('id')
            if model_id and model_id not in seen_ids:
                all_models.append(model)
                seen_ids.add(model_id)
        
        print(f"   追加済み: {len(all_models)}個")
        
    except Exception as e:
        print(f"   直接タグエラー: {e}")
    
    # 方法2: base modelから検索（制限付き）
    print(f"2. base modelから{base_model}フィルター...")
    try:
        base_models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=10  # 効率化のため10ページに制限
        )
        
        print(f"   base model取得: {len(base_models)}個")
        
        # フィルタリング
        filtered = []
        base_model_lower = base_model.lower()
        
        for model in base_models:
            try:
                name = (model.get('name') or '').lower()
                tags = [tag.lower() for tag in model.get('tags', []) if tag]
                description = (model.get('description') or '').lower()
                
                if (base_model_lower in name or 
                    base_model_lower in tags or 
                    base_model_lower in description):
                    filtered.append(model)
            except Exception:
                continue  # エラーがある場合はスキップ
        
        print(f"   フィルター結果: {len(filtered)}個")
        
        # 重複除去して追加
        added = 0
        for model in filtered:
            model_id = model.get('id')
            if model_id and model_id not in seen_ids:
                all_models.append(model)
                seen_ids.add(model_id)
                added += 1
        
        print(f"   新規追加: {added}個")
        
    except Exception as e:
        print(f"   base modelエラー: {e}")
    
    print(f"✅ {base_model.upper()}合計: {len(all_models)}個")
    
    # URL収集とファイル出力
    if all_models:
        urls = collector.collect_model_urls(all_models)
        
        filename_base = f"{base_model}_checkpoints_dual_method"
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        
        print(f"📁 {base_model.upper()}ファイル:")
        print(f"   CSV: {csv_file}")
        print(f"   JSON: {json_file}")
        print(f"   TXT: {text_file}")
        
        return all_models, urls
    
    return [], []


def main():
    print("=== 3つのベースモデル完全取得 ===")
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    try:
        # 初期化
        client = CivitaiClient(api_key)
        collector = URLCollector()
        
        # 3つのベースモデル
        base_models = ['pony', 'illustrious', 'noobai']
        all_results = {}
        
        # 各ベースモデルを順次処理
        for base_model in base_models:
            models, urls = collect_single_base_model(client, collector, base_model)
            all_results[base_model] = {
                'models': models,
                'urls': urls,
                'count': len(models)
            }
        
        # 統合ファイル作成
        print(f"\n{'='*50}")
        print(f"📄 統合ファイル作成")
        print(f"{'='*50}")
        
        all_urls = []
        for result in all_results.values():
            all_urls.extend(result['urls'])
        
        if all_urls:
            # 重複除去
            seen_urls = set()
            unique_urls = []
            for url_info in all_urls:
                url = url_info.download_url
                if url not in seen_urls:
                    unique_urls.append(url_info)
                    seen_urls.add(url)
            
            print(f"統合前: {len(all_urls)}個")
            print(f"重複除去後: {len(unique_urls)}個")
            
            # 統合ファイル出力
            unified_csv = collector.export_to_csv(unique_urls, "all_base_models_dual_method.csv")
            unified_json = collector.export_to_json(unique_urls, "all_base_models_dual_method.json")
            unified_txt = collector.export_to_text(unique_urls, "all_base_models_dual_method.txt")
            
            print(f"統合CSV: {unified_csv}")
            print(f"統合JSON: {unified_json}")
            print(f"統合TXT: {unified_txt}")
        
        # 最終サマリー
        print(f"\n{'='*50}")
        print(f"🎯 最終結果サマリー")
        print(f"{'='*50}")
        
        previous = {'pony': 97, 'illustrious': 243, 'noobai': 47}
        
        print(f"{'モデル':<12} {'以前':<8} {'現在':<8} {'増加':<8} {'率'}")
        print(f"{'-'*45}")
        
        total_prev = 0
        total_curr = 0
        
        for base_model in base_models:
            prev = previous[base_model]
            curr = all_results[base_model]['count']
            increase = curr - prev
            rate = f"{(increase/prev*100):.1f}%" if prev > 0 else "N/A"
            
            print(f"{base_model:<12} {prev:<8} {curr:<8} {increase:<8} {rate}")
            
            total_prev += prev
            total_curr += curr
        
        print(f"{'-'*45}")
        total_increase = total_curr - total_prev
        total_rate = f"{(total_increase/total_prev*100):.1f}%"
        print(f"{'合計':<12} {total_prev:<8} {total_curr:<8} {total_increase:<8} {total_rate}")
        
        print(f"\n✅ 全ベースモデルの取得が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()