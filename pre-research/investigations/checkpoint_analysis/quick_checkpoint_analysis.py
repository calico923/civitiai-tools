#!/usr/bin/env python3
"""
既存データからCheckpoint Type（Merge/Trained）を分析
"""

import pandas as pd
import re
from pathlib import Path

def analyze_checkpoint_names():
    """既存のCheckpointデータから名前パターンを分析"""
    
    # 既存のCheckpointデータを読み込み
    enhanced_dir = Path('/Users/kuniaki-k/Code/civitiai/outputs/enhanced')
    
    checkpoint_names = []
    
    # Checkpointデータを収集
    for csv_file in enhanced_dir.rglob('*checkpoint*.csv'):
        try:
            df = pd.read_csv(csv_file)
            if 'name' in df.columns:
                names = df['name'].dropna().tolist()
                checkpoint_names.extend(names)
        except:
            pass
    
    print(f"📊 {len(checkpoint_names)}個のCheckpoint名を分析中...")
    
    # キーワード分析
    merge_keywords = ['merge', 'merged', 'mix', 'blend', 'fusion', 'combo', 'combined']
    trained_keywords = ['trained', 'training', 'fine-tuned', 'finetune', 'custom', 'original']
    
    merge_checkpoints = []
    trained_checkpoints = []
    
    for name in checkpoint_names:
        name_lower = name.lower()
        
        # Merge系の判定
        if any(keyword in name_lower for keyword in merge_keywords):
            merge_checkpoints.append(name)
        
        # Trained系の判定
        if any(keyword in name_lower for keyword in trained_keywords):
            trained_checkpoints.append(name)
    
    print(f"\n🔍 分析結果:")
    print(f"  総Checkpoint数: {len(set(checkpoint_names))}個")
    print(f"  Merge系: {len(merge_checkpoints)}個 ({len(merge_checkpoints)/len(set(checkpoint_names))*100:.1f}%)")
    print(f"  Trained系: {len(trained_checkpoints)}個 ({len(trained_checkpoints)/len(set(checkpoint_names))*100:.1f}%)")
    
    print(f"\n📝 Merge系の例:")
    for example in list(set(merge_checkpoints))[:10]:
        print(f"    - {example}")
    
    print(f"\n📝 Trained系の例:")
    for example in list(set(trained_checkpoints))[:10]:
        print(f"    - {example}")
    
    return {
        'total_checkpoints': len(set(checkpoint_names)),
        'merge_count': len(merge_checkpoints),
        'trained_count': len(trained_checkpoints),
        'merge_examples': list(set(merge_checkpoints)),
        'trained_examples': list(set(trained_checkpoints))
    }

def create_checkpoint_subtype_filter():
    """Checkpoint subtype フィルタリング機能の実装例"""
    
    print(f"\n💡 Checkpoint Type フィルタリング実装例:")
    print("=" * 50)
    
    example_code = '''
def filter_checkpoints_by_subtype(checkpoints, subtype):
    """
    CheckpointリストをMerge/Trainedでフィルタリング
    """
    if subtype.lower() == 'merge':
        keywords = ['merge', 'merged', 'mix', 'blend', 'fusion', 'combo', 'combined']
    elif subtype.lower() == 'trained':
        keywords = ['trained', 'training', 'fine-tuned', 'finetune', 'custom', 'original']
    else:
        return checkpoints
    
    filtered = []
    for checkpoint in checkpoints:
        name = checkpoint.get('name', '').lower()
        description = checkpoint.get('description', '').lower()
        
        # 名前または説明にキーワードが含まれているかチェック
        if any(keyword in name or keyword in description for keyword in keywords):
            filtered.append(checkpoint)
    
    return filtered

# 使用例
def get_merge_checkpoints(client, base_model='Illustrious', limit=50):
    """Merge系のCheckpointを取得"""
    
    # 1. 通常のCheckpoint検索
    all_checkpoints = client.search_models(
        types='Checkpoint',
        limit=limit*2  # 多めに取得
    )
    
    # 2. baseModelでフィルタリング
    basemodel_filtered = filter_models_by_basemodel(
        all_checkpoints['items'], 
        base_model
    )
    
    # 3. Merge系でフィルタリング
    merge_checkpoints = filter_checkpoints_by_subtype(
        basemodel_filtered,
        'merge'
    )
    
    return merge_checkpoints[:limit]
'''
    
    print(example_code)

def main():
    print("🎯 Checkpoint Type (Merge/Trained) 分析")
    print("=" * 50)
    
    # 既存データ分析
    analysis = analyze_checkpoint_names()
    
    # 実装例表示
    create_checkpoint_subtype_filter()
    
    # 結果保存
    import json
    with open('checkpoint_subtype_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: checkpoint_subtype_analysis.json")
    
    # 結論
    print(f"\n🎯 結論:")
    print("1. CivitAI APIにはCheckpoint Type パラメータが存在しない")
    print("2. Webサイトのフィルターはクライアントサイドで実装されている")
    print("3. 解決策: 名前・説明文のキーワードフィルタリング")
    print("4. baseModel問題と同様の対処法が必要")

if __name__ == "__main__":
    main()