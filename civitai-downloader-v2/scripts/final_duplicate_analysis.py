#!/usr/bin/env python3
"""
最新のクリーンアップされたデータに基づく最終重複分析
"""
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any
import sys

def load_json_data(file_path: Path) -> List[Dict[str, Any]]:
    """JSONファイルからデータを読み込み"""
    print(f"Loading {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  → {len(data)} models loaded")
            return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def analyze_duplicates():
    """重複分析を実行"""
    base_path = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search")
    
    # カテゴリごとのデータを読み込み
    categories = {
        'CHARACTER': load_json_data(base_path / "character_models_category.json"),
        'STYLE': load_json_data(base_path / "style_models_category.json"),
        'CONCEPT': load_json_data(base_path / "concept_models_category.json"),
        'POSES': load_json_data(base_path / "poses_models_category.json")
    }
    
    # モデルIDごとのカテゴリ情報を収集
    model_categories = defaultdict(list)
    model_info = {}  # ID -> model info
    
    for category, models in categories.items():
        print(f"\nProcessing {category} category...")
        for model in models:
            model_id = model.get('id')
            if model_id:
                model_categories[model_id].append(category)
                model_info[model_id] = {
                    'name': model.get('name', 'Unknown'),
                    'creator': model.get('creator', {}).get('username', 'Unknown'),
                    'type': model.get('type', 'Unknown'),
                    'downloadCount': model.get('stats', {}).get('downloadCount', 0),
                    'tags': [tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in model.get('tags', [])]
                }
    
    print(f"\nTotal unique model IDs: {len(model_categories)}")
    
    # 重複分析
    category_overlaps = defaultdict(int)
    duplicate_models = []
    
    for model_id, cats in model_categories.items():
        if len(cats) > 1:
            cats_sorted = sorted(cats)
            overlap_key = " + ".join(cats_sorted)
            category_overlaps[overlap_key] += 1
            duplicate_models.append({
                'id': model_id,
                'categories': cats,
                'info': model_info[model_id]
            })
    
    # ダウンロード数でソート
    duplicate_models.sort(key=lambda x: x['info']['downloadCount'], reverse=True)
    
    # 統計計算
    total_unique = len(model_categories)
    models_in_single_category = sum(1 for cats in model_categories.values() if len(cats) == 1)
    total_duplicates = total_unique - models_in_single_category
    
    # カテゴリ別統計
    category_stats = {}
    for category, models in categories.items():
        unique_ids = set(model.get('id') for model in models if model.get('id'))
        total_downloads = sum(model.get('stats', {}).get('downloadCount', 0) for model in models)
        avg_downloads = total_downloads / len(unique_ids) if unique_ids else 0
        
        # このカテゴリで重複していたモデル数
        duplicate_from_this_category = sum(1 for model_id in unique_ids if len(model_categories[model_id]) > 1)
        
        category_stats[category] = {
            'total_models': len(unique_ids),
            'total_downloads': total_downloads,
            'avg_downloads': int(avg_downloads),
            'duplicate_models': duplicate_from_this_category
        }
    
    return {
        'total_unique': total_unique,
        'models_in_single_category': models_in_single_category,
        'total_duplicates': total_duplicates,
        'category_overlaps': dict(category_overlaps),
        'duplicate_models': duplicate_models[:20],  # Top 20
        'category_stats': category_stats
    }

def generate_final_report(analysis_results: Dict[str, Any]) -> str:
    """最終レポートを生成"""
    report = []
    report.append("=" * 80)
    report.append("CIVITAI MODEL FINAL ANALYSIS REPORT (Updated)")
    report.append("=" * 80)
    report.append("")
    
    # サマリー統計
    report.append("SUMMARY STATISTICS")
    report.append("-" * 40)
    report.append(f"Total unique models across all categories: {analysis_results['total_unique']:,}")
    report.append("")
    
    # モデル重複情報
    report.append("MODELS BY CATEGORY OVERLAP")
    report.append("-" * 40)
    report.append(f"Models in only 1 category: {analysis_results['models_in_single_category']:,}")
    
    if analysis_results['total_duplicates'] > 0:
        report.append(f"Models in multiple categories: {analysis_results['total_duplicates']:,}")
        report.append(f"Total cross-category duplicates: {analysis_results['total_duplicates']:,}")
        report.append("")
        
        # 重複の組み合わせ
        report.append("DUPLICATE MODELS BY CATEGORY COMBINATIONS")
        report.append("-" * 40)
        for combo, count in analysis_results['category_overlaps'].items():
            report.append(f"{combo}: {count:,} models")
        report.append("")
        
        # トップ重複モデル
        report.append("TOP 10 MOST DOWNLOADED CROSS-CATEGORY DUPLICATE MODELS")
        report.append("-" * 40)
        for i, duplicate in enumerate(analysis_results['duplicate_models'][:10], 1):
            info = duplicate['info']
            cats = " + ".join(sorted(duplicate['categories']))
            report.append(f" {i:2d}. {info['name']}")
            report.append(f"    ID: {duplicate['id']} | Downloads: {info['downloadCount']:,}")
            report.append(f"    Categories: {cats}")
            report.append(f"    Creator: {info['creator']} | Type: {info['type']}")
            report.append("")
    else:
        report.append("Models in multiple categories: 0")
        report.append("Total cross-category duplicates: 0")
        report.append("")
        report.append("✅ NO CROSS-CATEGORY DUPLICATES FOUND!")
        report.append("All models are properly categorized into single categories.")
        report.append("")
    
    # カテゴリ別詳細統計
    report.append("DETAILED CATEGORY STATISTICS")
    report.append("=" * 50)
    report.append("")
    
    for category, stats in analysis_results['category_stats'].items():
        report.append(f"{category} CATEGORY")
        report.append("-" * 30)
        report.append(f"Total unique models: {stats['total_models']:,}")
        report.append(f"Total downloads: {stats['total_downloads']:,}")
        report.append(f"Average downloads per model: {stats['avg_downloads']:,}")
        if stats['duplicate_models'] > 0:
            report.append(f"Models also in other categories: {stats['duplicate_models']:,}")
        report.append("")
    
    # 最終サマリー
    report.append("FINAL SUMMARY")
    report.append("-" * 40)
    total_downloads = sum(stats['total_downloads'] for stats in analysis_results['category_stats'].values())
    report.append(f"Total models analyzed: {analysis_results['total_unique']:,}")
    report.append(f"Total downloads across all categories: {total_downloads:,}")
    report.append(f"Cross-category duplicate rate: {(analysis_results['total_duplicates'] / analysis_results['total_unique'] * 100):.2f}%")
    
    return "\n".join(report)

def main():
    """メイン実行関数"""
    print("Starting final duplicate analysis...")
    
    # 分析実行
    analysis_results = analyze_duplicates()
    
    # レポート生成
    print("\nGenerating final report...")
    report_content = generate_final_report(analysis_results)
    
    # レポート保存
    output_path = Path("/Users/kuniaki-k/Code/civitiai/civitai-downloader-v2/reports/success_category_search/final_analysis_report.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n✅ Final report saved to: {output_path}")
    print(f"📊 Total unique models: {analysis_results['total_unique']:,}")
    print(f"🔄 Cross-category duplicates: {analysis_results['total_duplicates']:,}")
    
    return analysis_results

if __name__ == "__main__":
    main()