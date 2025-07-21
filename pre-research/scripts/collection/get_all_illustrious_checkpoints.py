#!/usr/bin/env python3
"""base modelタグからillustriousチェックポイントを正しく取得"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def main():
    print("=== 正しいillustriousチェックポイント取得 ===")
    print("base modelタグから検索してillustriousでフィルタリング")
    
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
        
        # base modelタグで全チェックポイントを取得
        print("\n2. base modelタグで全チェックポイントを取得中...")
        print("   これには数分かかります...")
        
        all_base_model_checkpoints = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=50  # 最大5000個まで
        )
        
        print(f"base modelタグでの総取得数: {len(all_base_model_checkpoints)}個")
        
        # illustriousを含むものをフィルタ
        print("\n3. illustriousに関連するチェックポイントをフィルタリング中...")
        
        illustrious_checkpoints = []
        for model in all_base_model_checkpoints:
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            description = model.get('description', '').lower()
            
            # illustriousが含まれているかチェック
            if ('illustrious' in name or 
                'illustrious' in tags or 
                'illustrious' in description):
                illustrious_checkpoints.append(model)
        
        print(f"illustrious関連チェックポイント: {len(illustrious_checkpoints)}個")
        
        # URL収集器の初期化
        collector = URLCollector()
        
        # URL情報を収集
        urls = collector.collect_model_urls(illustrious_checkpoints)
        print(f"ダウンロードURL: {len(urls)}個")
        
        # ファイル出力
        filename_base = "illustrious_checkpoints_complete"
        
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        
        print(f"\n📁 出力ファイル:")
        print(f"  CSV:  {csv_file}")
        print(f"  JSON: {json_file}")
        print(f"  TXT:  {text_file}")
        
        # 結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 完全なillustriousチェックポイント取得結果")
        print(f"{'='*60}")
        
        print(f"base modelタグ総数: {len(all_base_model_checkpoints):,}個")
        print(f"illustrious関連: {len(illustrious_checkpoints):,}個")
        print(f"ダウンロードURL数: {len(urls):,}個")
        
        # 以前の結果と比較
        print(f"\n📈 以前の結果との比較:")
        print(f"  以前（illustriousタグのみ）: 243個")
        print(f"  現在（base modelから検索）: {len(illustrious_checkpoints):,}個")
        if len(illustrious_checkpoints) > 243:
            improvement = len(illustrious_checkpoints) - 243
            print(f"  改善: {improvement:,}個増加 ({(improvement / 243 * 100):.1f}%向上)")
        
        # WebページとのQ比較
        print(f"\n🌐 Webページとの比較:")
        print(f"  Webページ表示: 500+個")
        print(f"  API取得結果: {len(illustrious_checkpoints):,}個")
        if len(illustrious_checkpoints) >= 500:
            print(f"  ✅ Webページの数値に一致または超過")
        else:
            print(f"  ⚠️  まだ差がある可能性（{500 - len(illustrious_checkpoints)}個差）")
        
        # サンプル表示
        print(f"\n📊 サンプルillustriousチェックポイント（上位10個）:")
        for i, model in enumerate(illustrious_checkpoints[:10], 1):
            name = model.get('name', 'Unknown')
            tags = ', '.join(model.get('tags', [])[:3])
            creator = model.get('creator', {})
            if isinstance(creator, dict):
                creator_name = creator.get('username', 'Unknown')
            else:
                creator_name = str(creator)
            
            print(f"{i:2d}. {name}")
            print(f"     タグ: {tags}")
            print(f"     作成者: {creator_name}")
            print()
        
        # タグ統計
        print(f"\n📈 タグ統計:")
        tag_counts = {}
        for model in illustrious_checkpoints:
            for tag in model.get('tags', []):
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
        
        # トップ10タグ
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for tag, count in top_tags:
            print(f"  {tag}: {count}個")
        
        print(f"\n✅ 完全なillustriousチェックポイント取得が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()