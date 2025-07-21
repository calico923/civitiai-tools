#!/usr/bin/env python3
"""効率的にstyleタグLoRAを取得（制限付き）"""

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


def classify_by_base_model(models: List[Dict], base_model: str) -> List[Dict]:
    """指定されたベースモデルに関連するモデルを分類"""
    filtered = []
    base_model_lower = base_model.lower()
    
    for model in models:
        # タグにベースモデル名が含まれているかチェック
        tags = model.get('tags', [])
        tag_match = any(base_model_lower in tag.lower() for tag in tags)
        
        # モデル名にベースモデル名が含まれているかチェック
        model_name = model.get('name', '')
        name_match = base_model_lower in model_name.lower()
        
        if tag_match or name_match:
            filtered.append(model)
    
    return filtered


def main():
    print("=== 効率的styleタグLoRA取得 ===")
    
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
        
        # 効率的に取得（最大10ページ = 1000個）
        print("\n2. styleタグLoRAを取得中（最大10ページ）...")
        
        all_style_models = client.search_models_with_cursor(
            types=["LORA"],
            tag="style",
            sort="Highest Rated",
            limit=100,
            max_pages=10  # 最大1000個に制限
        )
        
        print(f"\n✅ styleタグLoRA取得完了: {len(all_style_models)}個")
        
        # URL収集器の初期化
        collector = URLCollector()
        
        # ベースモデルのリスト
        base_models = ['pony', 'illustrious', 'noobai']
        base_model_results = {}
        
        print("\n3. ベースモデル別に分類中...")
        
        for base_model in base_models:
            print(f"\n--- {base_model.upper()} ベースモデルの分類 ---")
            
            # ベースモデルに関連するモデルを分類
            filtered_models = classify_by_base_model(all_style_models, base_model)
            print(f"  {base_model}関連: {len(filtered_models)}個")
            
            if filtered_models:
                # URL情報を収集
                urls = collector.collect_model_urls(filtered_models)
                print(f"  ダウンロードURL: {len(urls)}個")
                
                # ファイル出力
                filename_base = f"style_lora_{base_model}_efficient"
                
                csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
                json_file = collector.export_to_json(urls, f"{filename_base}.json")
                text_file = collector.export_to_text(urls, f"{filename_base}.txt")
                
                print(f"  📁 出力ファイル:")
                print(f"    CSV:  {csv_file}")
                print(f"    JSON: {json_file}")
                print(f"    TXT:  {text_file}")
                
                # 結果を保存
                base_model_results[base_model] = {
                    'count': len(filtered_models),
                    'urls': urls
                }
                
                # サンプル表示
                print(f"  📊 {base_model.upper()}サンプル（上位3個）:")
                for i, model in enumerate(filtered_models[:3], 1):
                    name = model.get('name', 'Unknown')
                    tags = ', '.join(model.get('tags', [])[:3])
                    print(f"    {i}. {name}")
                    print(f"       タグ: {tags}")
                
            else:
                print(f"  ❌ {base_model}関連のstyle LoRAが見つかりませんでした")
                base_model_results[base_model] = {'count': 0, 'urls': []}
        
        # 統合ファイルも作成
        print(f"\n4. 統合ファイルを作成中...")
        all_urls = collector.collect_model_urls(all_style_models)
        
        unified_csv = collector.export_to_csv(all_urls, "style_lora_all_efficient.csv")
        unified_json = collector.export_to_json(all_urls, "style_lora_all_efficient.json")
        unified_txt = collector.export_to_text(all_urls, "style_lora_all_efficient.txt")
        
        print(f"  統合CSV:  {unified_csv}")
        print(f"  統合JSON: {unified_json}")
        print(f"  統合TXT:  {unified_txt}")
        
        # 最終結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 最終結果サマリー（効率版）")
        print(f"{'='*60}")
        
        print(f"取得したstyleタグLoRA総数: {len(all_style_models):,}個")
        print(f"")
        print(f"ベースモデル別分類:")
        
        total_classified = 0
        for base_model in base_models:
            count = base_model_results[base_model]['count']
            total_classified += count
            print(f"  {base_model.upper():12}: {count:,}個")
        
        unclassified = len(all_style_models) - total_classified
        print(f"  {'その他':>12}: {unclassified:,}個")
        print(f"  {'総計':>12}: {len(all_style_models):,}個")
        
        # 以前の結果と比較
        print(f"\n📈 以前の結果との比較:")
        print(f"  以前: 54個 → 現在: {total_classified:,}個")
        if total_classified > 54:
            print(f"  改善: {total_classified - 54:,}個増加 ({((total_classified - 54) / 54 * 100):.1f}%向上)")
        
        print(f"\n✅ 全ベースモデルの収集が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()