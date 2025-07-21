#!/usr/bin/env python3
"""pony, noobai, illustriousを高速で比較確認"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient


def quick_count_by_tag(client, tag_name):
    """指定タグで直接検索（3ページまで）"""
    try:
        models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag=tag_name,
            sort="Most Downloaded",
            limit=100,
            max_pages=3  # 最大300個
        )
        return len(models)
    except Exception as e:
        print(f"  エラー: {e}")
        return 0


def quick_sample_from_base_model(client, target_name):
    """base modelタグから検索して対象でフィルター（サンプルのみ）"""
    try:
        # base modelの最初の500個のみ取得
        base_models = client.search_models_with_cursor(
            types=["Checkpoint"],
            tag="base model", 
            sort="Most Downloaded",
            limit=100,
            max_pages=5  # 最大500個
        )
        
        # 対象名でフィルタリング
        filtered_count = 0
        target_lower = target_name.lower()
        samples = []
        
        for model in base_models:
            name = model.get('name', '').lower()
            tags = [tag.lower() for tag in model.get('tags', [])]
            description = model.get('description', '').lower()
            
            if (target_lower in name or 
                target_lower in tags or 
                target_lower in description):
                filtered_count += 1
                if len(samples) < 3:  # サンプル3個まで
                    samples.append(model.get('name', 'Unknown'))
        
        return filtered_count, samples
        
    except Exception as e:
        print(f"  エラー: {e}")
        return 0, []


def main():
    print("=== 高速ベースモデル比較調査 ===")
    
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
        
        # 調査対象
        base_models = ['pony', 'illustrious', 'noobai']
        results = {}
        
        for base_model in base_models:
            print(f"\n--- {base_model.upper()} 調査 ---")
            
            # 方法1: 直接タグ検索
            print(f"方法1: {base_model}タグで直接検索（最大3ページ）")
            direct_count = quick_count_by_tag(client, base_model)
            print(f"  結果: {direct_count}個")
            
            # 方法2: base modelタグから検索（サンプル）
            print(f"方法2: base modelから{base_model}検索（最大5ページのサンプル）")
            filtered_count, samples = quick_sample_from_base_model(client, base_model)
            print(f"  結果: {filtered_count}個（500個中）")
            
            if samples:
                print(f"  サンプル: {', '.join(samples)}")
            
            # 結果保存
            results[base_model] = {
                'direct_tag': direct_count,
                'base_model_sample': filtered_count
            }
        
        # 結果サマリー
        print(f"\n{'='*60}")
        print(f"🎯 高速調査結果サマリー")
        print(f"{'='*60}")
        
        print(f"{'モデル名':<12} {'直接タグ':<10} {'base model(500個中)':<20} {'状況'}")
        print(f"{'-'*65}")
        
        for base_model in base_models:
            result = results[base_model]
            direct = result['direct_tag']
            sample = result['base_model_sample']
            
            # 状況判定
            if sample > direct * 0.2:  # サンプルで20%以上見つかった場合
                status = "⚠️  取得漏れの可能性大"
            elif sample > 0:
                status = "📊 追加チェックポイント有り"
            else:
                status = "✅ 直接タグで十分"
            
            print(f"{base_model:<12} {direct:<10} {sample:<20} {status}")
        
        # 詳細分析
        print(f"\n📈 詳細分析:")
        for base_model in base_models:
            result = results[base_model]
            direct = result['direct_tag']
            sample = result['base_model_sample']
            
            # 全体推定（500個のサンプルから推定）
            if sample > 0:
                # base modelの全数を仮に5000個と仮定して推定
                estimated_additional = int(sample * 10)  # 500個 × 10 = 5000個全体の推定
                estimated_total = direct + estimated_additional
                
                print(f"\n{base_model.upper()}:")
                print(f"  直接タグ: {direct}個")
                print(f"  base model サンプル: {sample}個（500個中）")
                print(f"  推定追加数: ~{estimated_additional}個")
                print(f"  推定合計: ~{estimated_total}個")
                
                if estimated_additional > direct:
                    print(f"  🚨 重要: illustriousと同様の大幅な取得漏れの可能性！")
            else:
                print(f"\n{base_model.upper()}: base modelからの追加発見なし")
        
        # 結論
        print(f"\n🎯 結論:")
        print(f"  📍 illustrious: 既に確認済み（大幅な取得漏れあり）")
        
        pony_result = results['pony']
        if pony_result['base_model_sample'] > pony_result['direct_tag'] * 0.2:
            print(f"  📍 pony: 取得漏れの可能性大！base model経由で大幅増加見込み")
        else:
            print(f"  📍 pony: 直接タグ検索で概ね十分")
        
        noobai_result = results['noobai']
        if noobai_result['base_model_sample'] > noobai_result['direct_tag'] * 0.2:
            print(f"  📍 noobai: 取得漏れの可能性大！base model経由で大幅増加見込み")
        else:
            print(f"  📍 noobai: 直接タグ検索で概ね十分")
        
        print(f"\n✅ 高速調査が完了しました！")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()