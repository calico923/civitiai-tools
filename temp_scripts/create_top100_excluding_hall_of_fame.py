#!/usr/bin/env python3
"""
殿堂入りを除いてTop100ランキングを作成するスクリプト
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

def detect_nsfw(tags):
    """タグからNSFW分類を判定"""
    if pd.isna(tags):
        return False
    
    tags_lower = str(tags).lower()
    nsfw_keywords = [
        'nsfw', 'hentai', 'sexy', 'porn', 'nude', 'naked', 
        'erotic', 'adult', 'xxx', 'sex', 'yiff', 'bara',
        'ecchi', 'lewd', 'provocative'
    ]
    
    return any(keyword in tags_lower for keyword in nsfw_keywords)

def main():
    # 完全なデータセットを読み込み
    df = pd.read_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_complete_metrics.csv')
    
    print(f"完全データセット: {len(df)}モデル")
    
    # 殿堂入りモデル（WAI-NSFW-illustrious-SDXL）を除外
    df_filtered = df[df['model_id'] != 827184].copy()
    print(f"殿堂入り除外後: {len(df_filtered)}モデル")
    
    # 'base model'タグを持つモデルのみをフィルタリング
    df_filtered = df_filtered[df_filtered['tags'].str.contains('base model', na=False)].copy()
    print(f"'base model'タグフィルタリング後: {len(df_filtered)}モデル")
    
    # NSFW分類を更新
    df_filtered['nsfw'] = df_filtered['tags'].apply(detect_nsfw)
    
    # エンゲージメントスコアを計算（既存のカラムを使用）
    # 各メトリクスを正規化
    df_filtered['thumbs_up_normalized'] = normalize_score(df_filtered['thumbs_up_count'])
    df_filtered['download_normalized'] = normalize_score(df_filtered['updated_download_count'])
    df_filtered['engagement_normalized'] = normalize_score(df_filtered['engagement_score'])
    df_filtered['comment_normalized'] = normalize_score(df_filtered['comment_count'])
    
    # 重み付きスコアを計算
    df_filtered['quality_score'] = (
        df_filtered['thumbs_up_normalized'] * 0.40 +      # いいね数
        df_filtered['download_normalized'] * 0.30 +       # ダウンロード数  
        df_filtered['engagement_normalized'] * 0.20 +     # エンゲージメント
        df_filtered['comment_normalized'] * 0.10          # コメント数
    )
    
    # ランキングスコアを計算（最高得点を100として正規化）
    max_quality_score = df_filtered['quality_score'].max()
    df_filtered['final_ranking_score'] = 100 * df_filtered['quality_score'] / max_quality_score
    
    # ランキング順にソート
    df_filtered = df_filtered.sort_values('final_ranking_score', ascending=False)
    
    # Top100を取得
    top100 = df_filtered.head(100).copy()
    
    # ランクを付与
    top100['rank'] = range(1, len(top100) + 1)
    
    # 統計情報
    sfw_count = (~top100['nsfw']).sum()
    nsfw_count = top100['nsfw'].sum()
    
    print(f"\n=== Top100統計 ===")
    print(f"SFW: {sfw_count}モデル ({sfw_count/len(top100)*100:.1f}%)")
    print(f"NSFW: {nsfw_count}モデル ({nsfw_count/len(top100)*100:.1f}%)")
    
    # 新しいトップ10を表示
    print(f"\n=== 新Top 10 ===")
    for i, (_, row) in enumerate(top100.head(10).iterrows(), 1):
        nsfw_status = "NSFW" if row['nsfw'] else "SFW"
        print(f"{i:2d}. {row['model_name'][:40]:<40} | スコア: {row['final_ranking_score']:5.2f} | {nsfw_status}")
    
    # 必要なカラムを選択して保存
    output_columns = ['rank', 'model_name', 'model_id', 'creator', 'final_ranking_score', 
                     'thumbs_up_count', 'updated_download_count', 'engagement_score', 'nsfw', 'tags', 'civitai_page_url']
    
    top100_output = top100[output_columns].copy()
    top100_output.to_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top100_excluding_hall_of_fame.csv', 
                        index=False, encoding='utf-8')
    
    # 殿堂入りモデルの情報も保存
    hall_of_fame = df[df['model_id'] == 827184].copy()
    hall_of_fame['nsfw'] = hall_of_fame['tags'].apply(detect_nsfw)
    
    hall_of_fame_output = hall_of_fame[['model_name', 'model_id', 'creator', 'thumbs_up_count', 
                                       'updated_download_count', 'engagement_score', 'nsfw', 'tags', 'civitai_page_url']].copy()
    hall_of_fame_output.to_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame_final.csv', 
                              index=False, encoding='utf-8')
    
    print(f"\n=== ファイル出力完了 ===")
    print(f"Top100: /Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top100_excluding_hall_of_fame.csv")
    print(f"殿堂入り: /Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame_final.csv")

if __name__ == "__main__":
    main()