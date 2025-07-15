#!/usr/bin/env python3
"""
殿堂入り枠を作成し、残り99モデルでランキングスコアを再計算するスクリプト
"""

import pandas as pd
import numpy as np
from datetime import datetime

def normalize_score(series):
    """スコアを0-100の範囲に正規化"""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series([50.0] * len(series), index=series.index)
    return 100 * (series - min_val) / (max_val - min_val)

def calculate_engagement_score(df):
    """エンゲージメントスコアを計算（既存のengagement_scoreを使用）"""
    # 既にengagement_scoreが計算済みなのでそのまま使用
    return df

def main():
    # データを読み込み
    df = pd.read_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top100_essential_corrected.csv')
    
    print(f"元データ: {len(df)}モデル")
    
    # 殿堂入りモデル（WAI-NSFW-illustrious-SDXL）を分離
    hall_of_fame = df[df['model_id'] == 827184].copy()
    remaining_models = df[df['model_id'] != 827184].copy()
    
    print(f"殿堂入り: {len(hall_of_fame)}モデル")
    print(f"残りモデル: {len(remaining_models)}モデル")
    
    # 残り99モデルのランキングスコアを再計算
    print("\n99モデルのスコアを再計算中...")
    
    # エンゲージメントスコアを計算
    remaining_models = calculate_engagement_score(remaining_models)
    
    # 各メトリクスを正規化（99モデルの範囲で）
    remaining_models['thumbs_up_normalized'] = normalize_score(remaining_models['thumbs_up_count'])
    remaining_models['download_normalized'] = normalize_score(remaining_models['updated_download_count'])
    remaining_models['engagement_normalized'] = normalize_score(remaining_models['engagement_score'])
    # コメント数は個別データから計算する必要があるため、エンゲージメントスコアで代用
    remaining_models['comment_normalized'] = normalize_score(remaining_models['engagement_score'] * 0.1)
    
    # 重み付きスコアを計算
    remaining_models['quality_score'] = (
        remaining_models['thumbs_up_normalized'] * 0.40 +      # いいね数
        remaining_models['download_normalized'] * 0.30 +       # ダウンロード数  
        remaining_models['engagement_normalized'] * 0.20 +     # エンゲージメント
        remaining_models['comment_normalized'] * 0.10          # コメント数
    )
    
    # ランキングスコアを再計算（最高得点を100として正規化）
    max_quality_score = remaining_models['quality_score'].max()
    remaining_models['final_ranking_score'] = 100 * remaining_models['quality_score'] / max_quality_score
    
    # ランキング順にソート
    remaining_models = remaining_models.sort_values('final_ranking_score', ascending=False)
    
    # 新しいランクを付与
    remaining_models['rank'] = range(1, len(remaining_models) + 1)
    
    # 殿堂入りモデルの情報を表示
    print(f"\n=== 殿堂入り ===")
    hof_model = hall_of_fame.iloc[0]
    print(f"モデル名: {hof_model['model_name']}")
    print(f"いいね数: {hof_model['thumbs_up_count']:,}")
    print(f"ダウンロード数: {hof_model['updated_download_count']:,}")
    print(f"元スコア: {hof_model['final_ranking_score']:.2f}")
    
    # 新しいトップ10を表示
    print(f"\n=== 新Top 10 ===")
    for i, (_, row) in enumerate(remaining_models.head(10).iterrows(), 1):
        nsfw_status = "NSFW" if row['nsfw'] else "SFW"
        print(f"{i:2d}. {row['model_name'][:40]:<40} | スコア: {row['final_ranking_score']:5.2f} | {nsfw_status}")
    
    # 統計情報
    sfw_count = (~remaining_models['nsfw']).sum()
    nsfw_count = remaining_models['nsfw'].sum()
    print(f"\n=== 統計 (99モデル) ===")
    print(f"SFW: {sfw_count}モデル ({sfw_count/len(remaining_models)*100:.1f}%)")
    print(f"NSFW: {nsfw_count}モデル ({nsfw_count/len(remaining_models)*100:.1f}%)")
    
    # 必要なカラムを選択して保存
    output_columns = ['rank', 'model_name', 'model_id', 'creator', 'final_ranking_score', 
                     'thumbs_up_count', 'updated_download_count', 'engagement_score', 'nsfw', 'tags', 'civitai_page_url']
    
    # 殿堂入りファイルを保存
    hall_of_fame_output = hall_of_fame[['model_name', 'model_id', 'creator', 'final_ranking_score', 
                                       'thumbs_up_count', 'updated_download_count', 'engagement_score', 'nsfw', 'tags', 'civitai_page_url']].copy()
    hall_of_fame_output.to_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame.csv', 
                              index=False, encoding='utf-8')
    
    # 新しいTop99ランキングを保存
    remaining_output = remaining_models[output_columns].copy()
    remaining_output.to_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top99_recalculated.csv', 
                           index=False, encoding='utf-8')
    
    print(f"\n=== ファイル出力完了 ===")
    print(f"殿堂入り: /Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame.csv")
    print(f"Top99: /Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top99_recalculated.csv")

if __name__ == "__main__":
    main()