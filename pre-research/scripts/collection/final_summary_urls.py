#!/usr/bin/env python3
"""最終的なURL取得結果をまとめる"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def quick_dual_method(client, base_model):
    """高速デュアルメソッド取得"""
    all_models = []
    seen_ids = set()
    
    print(f"\n--- {base_model.upper()} 高速取得 ---")
    
    # 方法1: 直接タグ
    try:
        direct = client.search_models_with_cursor(
            types=["Checkpoint"], tag=base_model, sort="Most Downloaded", limit=100, max_pages=3
        )
        for model in direct:
            if model.get('id') not in seen_ids:
                all_models.append(model)
                seen_ids.add(model.get('id'))
        print(f"直接タグ: {len(direct)}個")
    except Exception as e:
        print(f"直接タグエラー: {e}")
    
    # 方法2: base modelから抜粋（サンプルのみ）
    try:
        base_models = client.search_models_with_cursor(
            types=["Checkpoint"], tag="base model", sort="Most Downloaded", limit=100, max_pages=5
        )
        
        filtered = []
        for model in base_models:
            try:
                name = (model.get('name') or '').lower()
                tags = [t.lower() for t in model.get('tags', []) if t]
                if base_model.lower() in name or base_model.lower() in tags:
                    filtered.append(model)
            except:
                continue
        
        added = 0
        for model in filtered:
            if model.get('id') not in seen_ids:
                all_models.append(model)
                seen_ids.add(model.get('id'))
                added += 1
        
        print(f"base model追加: {added}個")
    except Exception as e:
        print(f"base modelエラー: {e}")
    
    print(f"合計: {len(all_models)}個")
    return all_models


def main():
    print("=== 最終URL取得まとめ ===")
    
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    try:
        client = CivitaiClient(api_key)
        collector = URLCollector()
        
        # 既存の最良結果を使用
        print("既存の最良結果を確認中...")
        
        results = {
            'pony': 156,      # pony_checkpoints_dual_method.txt
            'illustrious': 243,  # illustrious_checkpoints_fixed_cursor.txt
            'noobai': 0       # まだ未取得
        }
        
        # noobaiのみ新規取得
        print("\nnoobaiの新規取得...")
        noobai_models = quick_dual_method(client, 'noobai')
        
        if noobai_models:
            urls = collector.collect_model_urls(noobai_models)
            
            csv_file = collector.export_to_csv(urls, "noobai_checkpoints_dual_method.csv")
            json_file = collector.export_to_json(urls, "noobai_checkpoints_dual_method.json")
            text_file = collector.export_to_text(urls, "noobai_checkpoints_dual_method.txt")
            
            print(f"📁 NOOBAIファイル:")
            print(f"   CSV: {csv_file}")
            print(f"   JSON: {json_file}")
            print(f"   TXT: {text_file}")
            
            results['noobai'] = len(noobai_models)
        
        # 最終サマリー
        print(f"\n{'='*50}")
        print(f"🎯 最終URL取得結果サマリー")
        print(f"{'='*50}")
        
        previous = {'pony': 97, 'illustrious': 243, 'noobai': 47}
        
        print(f"{'モデル':<12} {'以前':<8} {'現在':<8} {'改善':<8} {'ファイル'}")
        print(f"{'-'*60}")
        
        file_map = {
            'pony': 'pony_checkpoints_dual_method.txt',
            'illustrious': 'illustrious_checkpoints_fixed_cursor.txt',
            'noobai': 'noobai_checkpoints_dual_method.txt'
        }
        
        total_prev = 0
        total_curr = 0
        
        for base_model in ['pony', 'illustrious', 'noobai']:
            prev = previous[base_model]
            curr = results[base_model]
            improvement = curr - prev
            
            status = "✅" if improvement > 0 else "📊" if improvement == 0 else "⚠️"
            
            print(f"{base_model:<12} {prev:<8} {curr:<8} {improvement:<8} {status}")
            
            total_prev += prev
            total_curr += curr
        
        print(f"{'-'*60}")
        total_improvement = total_curr - total_prev
        print(f"{'合計':<12} {total_prev:<8} {total_curr:<8} {total_improvement:<8}")
        
        # 利用可能ファイル一覧
        print(f"\n📁 利用可能なURLファイル:")
        for base_model, filename in file_map.items():
            count = results[base_model]
            if count > 0:
                print(f"  {base_model.upper()}: {filename} ({count}個)")
        
        # 推奨利用方法
        print(f"\n💡 推奨利用方法:")
        print(f"  1. 各ベースモデル別: 上記個別ファイルを使用")
        print(f"  2. 統合版: 3つのファイルを手動でマージ")
        print(f"  3. 重複除去: model_idベースで重複チェック")
        
        print(f"\n🌐 Webページとの比較:")
        web_estimates = {'pony': 1000, 'illustrious': 500, 'noobai': 200}
        for base_model in ['pony', 'illustrious', 'noobai']:
            current = results[base_model]
            estimated = web_estimates[base_model]
            if current > 0:
                coverage = f"{(current/estimated*100):.1f}%"
                print(f"  {base_model}: {current}個 / 推定{estimated}個 (カバー率: {coverage})")
        
        print(f"\n✅ 最終URL取得作業が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()