#!/usr/bin/env python3
"""効率的にillustriousチェックポイントを取得（制限付き）"""

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
    print("=== 効率的illustriousチェックポイント取得 ===")
    
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
        
        # base modelタグでチェックポイントを取得（制限付き）
        print("\n2. base modelタグでチェックポイントを取得中（最大20ページ）...")
        
        all_base_model_checkpoints = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model",
            sort="Most Downloaded",
            limit=100,
            max_pages=20  # 最大2000個に制限
        )
        
        print(f"base modelタグでの取得数: {len(all_base_model_checkpoints)}個")
        
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
        filename_base = "illustrious_checkpoints_from_base_model"
        
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        
        print(f"\n📁 出力ファイル:")
        print(f"  CSV:  {csv_file}")
        print(f"  JSON: {json_file}")
        print(f"  TXT:  {text_file}")
        
        # 結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 illustriousチェックポイント取得結果（効率版）")
        print(f"{'='*60}")
        
        print(f"base modelタグから取得: {len(all_base_model_checkpoints):,}個")
        print(f"illustrious関連抽出: {len(illustrious_checkpoints):,}個")
        print(f"ダウンロードURL数: {len(urls):,}個")
        
        # 以前の結果と比較
        print(f"\n📈 取得方法別比較:")
        print(f"  illustriousタグのみ: 243個")
        print(f"  base modelから抽出: {len(illustrious_checkpoints):,}個")
        print(f"  合計推定値: {243 + len(illustrious_checkpoints):,}個")
        
        improvement = len(illustrious_checkpoints) - 243
        if improvement > 0:
            print(f"  追加発見: {improvement:,}個 ({(improvement / 243 * 100):.1f}%増)")
        
        # WebページとのQ比較
        total_estimated = 243 + len(illustrious_checkpoints)
        print(f"\n🌐 Webページとの比較:")
        print(f"  Webページ表示: 500+個")
        print(f"  推定合計: {total_estimated:,}個")
        if total_estimated >= 500:
            print(f"  ✅ Webページの数値に近似または超過")
        else:
            print(f"  📊 差異: {500 - total_estimated}個（まだ取得できる可能性）")
        
        # サンプル表示
        print(f"\n📊 base modelからのillustriousサンプル（上位10個）:")
        for i, model in enumerate(illustrious_checkpoints[:10], 1):
            name = model.get('name', 'Unknown')
            tags = ', '.join(model.get('tags', [])[:3])
            
            print(f"{i:2d}. {name}")
            print(f"     タグ: {tags}")
            print()
        
        # 推奨アクション
        print(f"\n💡 推奨アクション:")
        print(f"  1. illustriousタグのみ: 243個 + base modelから: {len(illustrious_checkpoints)}個")
        print(f"  2. 重複除去を行って統合ファイルを作成")
        print(f"  3. より多くのページを取得すればさらに増加の可能性")
        
        print(f"\n✅ 効率的illustriousチェックポイント取得が完了しました！")
        print(f"出力ディレクトリ: {collector.output_dir}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()