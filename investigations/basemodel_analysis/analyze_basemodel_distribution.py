#\!/usr/bin/env python3
"""
既存データから全モデルタイプのbaseModel分布を分析
"""

import pandas as pd
import json
from collections import Counter, defaultdict
from pathlib import Path
import re

def normalize_basemodel(basemodel):
    """baseModelを正規化"""
    if not basemodel or pd.isna(basemodel):
        return "Unknown"
    
    # 小文字変換
    base = str(basemodel).lower().strip()
    
    # 正規化ルール
    if 'illustrious' in base:
        return "Illustrious"
    elif 'pony' in base:
        return "Pony"
    elif 'noobai' in base or 'noob' in base:
        return "NoobAI"
    elif 'sdxl' in base or 'sd xl' in base:
        return "SDXL"
    elif 'flux' in base:
        return "Flux"
    elif 'sd 1.5' in base or 'sd1.5' in base:
        return "SD 1.5"
    elif 'sd 2.0' in base or 'sd2.0' in base:
        return "SD 2.0"
    elif 'sd 3.0' in base or 'sd3.0' in base:
        return "SD 3.0"
    elif 'other' in base:
        return "Other"
    else:
        return base.title()

def analyze_existing_data():
    """既存データからbaseModel分布を分析"""
    
    # 分析結果格納
    analysis_results = defaultdict(lambda: defaultdict(int))
    raw_basemodesl = defaultdict(set)
    
    # 1. Enhanced データを調査
    enhanced_dir = Path('/Users/kuniaki-k/Code/civitiai/outputs/enhanced')
    
    for csv_file in enhanced_dir.rglob('*.csv'):
        try:
            print(f"📊 分析中: {csv_file.name}")
            df = pd.read_csv(csv_file)
            
            # model_typeとbase_modelカラムを確認
            if 'model_type' in df.columns:
                type_col = 'model_type'
            elif 'type' in df.columns:
                type_col = 'type'
            else:
                continue
                
            if 'base_model' in df.columns:
                base_col = 'base_model'
            elif 'baseModel' in df.columns:
                base_col = 'baseModel'
            else:
                continue
            
            # 各行を分析
            for _, row in df.iterrows():
                model_type = row.get(type_col, 'Unknown')
                base_model = row.get(base_col, 'Unknown')
                
                # Raw データを保存
                raw_basemodesl[model_type].add(str(base_model))
                
                # 正規化して集計
                normalized = normalize_basemodel(base_model)
                analysis_results[model_type][normalized] += 1
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return dict(analysis_results), dict(raw_basemodesl)

def create_distribution_report():
    """分布レポートを作成"""
    
    print("🔍 既存データからbaseModel分布を分析中...")
    
    analysis, raw_data = analyze_existing_data()
    
    # 結果をまとめ
    total_models = 0
    type_summary = {}
    
    for model_type, base_counts in analysis.items():
        total_for_type = sum(base_counts.values())
        total_models += total_for_type
        
        type_summary[model_type] = {
            'total': total_for_type,
            'base_models': dict(base_counts),
            'raw_values': list(raw_data.get(model_type, set()))
        }
    
    # 全体統計
    all_base_models = Counter()
    for type_data in type_summary.values():
        for base_model, count in type_data['base_models'].items():
            all_base_models[base_model] += count
    
    print(f"\n📊 分析結果 (総モデル数: {total_models:,})")
    print("=" * 60)
    
    # タイプ別分布
    print("\n🎯 モデルタイプ別分布:")
    for model_type, data in sorted(type_summary.items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"\n{model_type}: {data['total']:,}個")
        
        # 上位baseModel
        top_bases = sorted(data['base_models'].items(), key=lambda x: x[1], reverse=True)[:5]
        for base_model, count in top_bases:
            percentage = (count / data['total']) * 100
            print(f"  - {base_model}: {count:,} ({percentage:.1f}%)")
    
    # 全体のbaseModel分布
    print(f"\n🌍 全体のbaseModel分布:")
    for base_model, count in all_base_models.most_common(10):
        percentage = (count / total_models) * 100
        print(f"  - {base_model}: {count:,} ({percentage:.1f}%)")
    
    # 詳細データ保存
    detailed_results = {
        'summary': {
            'total_models': total_models,
            'total_types': len(type_summary),
            'analysis_date': pd.Timestamp.now().isoformat()
        },
        'by_type': type_summary,
        'global_distribution': dict(all_base_models)
    }
    
    # JSON保存
    with open('basemodel_distribution_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # CSV保存
    csv_data = []
    for model_type, data in type_summary.items():
        for base_model, count in data['base_models'].items():
            csv_data.append({
                'model_type': model_type,
                'base_model': base_model,
                'count': count,
                'percentage': (count / data['total']) * 100
            })
    
    df_results = pd.DataFrame(csv_data)
    df_results.to_csv('basemodel_distribution_analysis.csv', index=False)
    
    print(f"\n📁 詳細結果:")
    print(f"  📊 CSV: basemodel_distribution_analysis.csv")
    print(f"  📋 JSON: basemodel_distribution_analysis.json")
    
    return detailed_results

if __name__ == "__main__":
    results = create_distribution_report()