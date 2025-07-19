#!/usr/bin/env python3
"""
CivitAI API での illustrious バージョンと non-illustrious バージョンの詳細比較

複数のバージョンを持つモデルから、illustriousバージョンとそうでないバージョンの
具体的な違いを分析します。
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.client import CivitaiClient
from dotenv import load_dotenv


def compare_versions(client: CivitaiClient, model_id: int, model_name: str) -> dict:
    """
    1つのモデルのillustriousバージョンと非illustriousバージョンを比較
    
    Args:
        client: CivitaiClient instance
        model_id: モデルID
        model_name: モデル名
        
    Returns:
        比較結果辞書
    """
    print(f"\n🔍 {model_name} (ID: {model_id}) のバージョン比較...")
    
    try:
        # モデルの詳細情報を取得
        model_data = client.get_model_by_id(model_id)
        model_versions = model_data.get('modelVersions', [])
        
        print(f"📋 総バージョン数: {len(model_versions)}")
        
        # illustriousバージョンとnon-illustriousバージョンに分類
        illustrious_versions = []
        non_illustrious_versions = []
        
        for version in model_versions:
            version_id = version.get('id')
            version_name = version.get('name', 'Unknown')
            version_base_model = version.get('baseModel', 'Unknown')
            version_description = version.get('description', '')
            
            # バージョン個別のデータを取得
            try:
                version_detail = client.request('GET', f'/model-versions/{version_id}')
                if version_detail.status_code == 200:
                    version_data = version_detail.json()
                    
                    # illustrious判定
                    is_illustrious = check_illustrious_version(
                        version_name, version_base_model, version_description
                    )
                    
                    version_info = {
                        'version_id': version_id,
                        'version_name': version_name,
                        'base_model': version_base_model,
                        'description': version_description,
                        'created_at': version_data.get('createdAt'),
                        'updated_at': version_data.get('updatedAt'),
                        'status': version_data.get('status'),
                        'published_at': version_data.get('publishedAt'),
                        'trained_words': version_data.get('trainedWords', []),
                        'files': version_data.get('files', []),
                        'stats': version_data.get('stats', {}),
                        'download_url': version_data.get('downloadUrl'),
                        'upload_type': version_data.get('uploadType'),
                        'usage_control': version_data.get('usageControl'),
                        'early_access_config': version_data.get('earlyAccessConfig'),
                        'air': version_data.get('air'),
                        'training_status': version_data.get('trainingStatus'),
                        'training_details': version_data.get('trainingDetails')
                    }
                    
                    if is_illustrious:
                        illustrious_versions.append(version_info)
                        print(f"  ✅ illustrious: {version_name} (ID: {version_id})")
                    else:
                        non_illustrious_versions.append(version_info)
                        print(f"  ❌ non-illustrious: {version_name} (ID: {version_id})")
                        
            except Exception as e:
                print(f"  ⚠️  バージョン {version_id} の詳細取得失敗: {e}")
        
        comparison_result = {
            'model_id': model_id,
            'model_name': model_name,
            'total_versions': len(model_versions),
            'illustrious_count': len(illustrious_versions),
            'non_illustrious_count': len(non_illustrious_versions),
            'illustrious_versions': illustrious_versions,
            'non_illustrious_versions': non_illustrious_versions
        }
        
        # 比較分析を実行
        if illustrious_versions and non_illustrious_versions:
            comparison_result['analysis'] = analyze_differences(
                illustrious_versions, non_illustrious_versions
            )
        
        return comparison_result
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        return {
            'model_id': model_id,
            'model_name': model_name,
            'error': str(e)
        }


def check_illustrious_version(version_name: str, base_model: str, description: str) -> bool:
    """illustrious バージョンかどうかを判定"""
    illustrious_keywords = [
        'illustrious', 'ill', 'ilxl', 'illustrious-xl', 'illustriousxl'
    ]
    
    version_name_lower = version_name.lower()
    base_model_lower = base_model.lower()
    description_lower = description.lower()
    
    for keyword in illustrious_keywords:
        if (keyword in version_name_lower or 
            keyword in base_model_lower or 
            keyword in description_lower):
            return True
    
    return False


def analyze_differences(illustrious_versions: List[Dict], non_illustrious_versions: List[Dict]) -> Dict:
    """illustriousバージョンと非illustriousバージョンの違いを分析"""
    
    analysis = {
        'base_model_comparison': {},
        'file_size_comparison': {},
        'stats_comparison': {},
        'training_words_comparison': {},
        'upload_type_comparison': {},
        'key_differences': []
    }
    
    # 1. ベースモデルの比較
    illustrious_base_models = [v['base_model'] for v in illustrious_versions]
    non_illustrious_base_models = [v['base_model'] for v in non_illustrious_versions]
    
    analysis['base_model_comparison'] = {
        'illustrious_base_models': list(set(illustrious_base_models)),
        'non_illustrious_base_models': list(set(non_illustrious_base_models))
    }
    
    # 2. ファイルサイズの比較
    illustrious_sizes = []
    non_illustrious_sizes = []
    
    for version in illustrious_versions:
        for file in version.get('files', []):
            size_kb = file.get('sizeKB', 0)
            if size_kb > 0:
                illustrious_sizes.append(size_kb)
    
    for version in non_illustrious_versions:
        for file in version.get('files', []):
            size_kb = file.get('sizeKB', 0)
            if size_kb > 0:
                non_illustrious_sizes.append(size_kb)
    
    analysis['file_size_comparison'] = {
        'illustrious_avg_size_mb': sum(illustrious_sizes) / len(illustrious_sizes) / 1024 if illustrious_sizes else 0,
        'non_illustrious_avg_size_mb': sum(non_illustrious_sizes) / len(non_illustrious_sizes) / 1024 if non_illustrious_sizes else 0,
        'illustrious_file_count': len(illustrious_sizes),
        'non_illustrious_file_count': len(non_illustrious_sizes)
    }
    
    # 3. 統計情報の比較
    illustrious_stats = {
        'download_count': [],
        'rating_count': [],
        'rating': [],
        'favorite_count': []
    }
    
    non_illustrious_stats = {
        'download_count': [],
        'rating_count': [],
        'rating': [],
        'favorite_count': []
    }
    
    for version in illustrious_versions:
        stats = version.get('stats', {})
        for key in illustrious_stats:
            if key in stats:
                illustrious_stats[key].append(stats[key])
    
    for version in non_illustrious_versions:
        stats = version.get('stats', {})
        for key in non_illustrious_stats:
            if key in stats:
                non_illustrious_stats[key].append(stats[key])
    
    # 平均値を計算
    for key in illustrious_stats:
        illustrious_avg = sum(illustrious_stats[key]) / len(illustrious_stats[key]) if illustrious_stats[key] else 0
        non_illustrious_avg = sum(non_illustrious_stats[key]) / len(non_illustrious_stats[key]) if non_illustrious_stats[key] else 0
        
        analysis['stats_comparison'][key] = {
            'illustrious_avg': illustrious_avg,
            'non_illustrious_avg': non_illustrious_avg
        }
    
    # 4. 学習キーワードの比較
    illustrious_words = []
    non_illustrious_words = []
    
    for version in illustrious_versions:
        words = version.get('trained_words', [])
        if words:
            illustrious_words.extend(words)
    
    for version in non_illustrious_versions:
        words = version.get('trained_words', [])
        if words:
            non_illustrious_words.extend(words)
    
    analysis['training_words_comparison'] = {
        'illustrious_unique_words': list(set(illustrious_words)),
        'non_illustrious_unique_words': list(set(non_illustrious_words)),
        'common_words': list(set(illustrious_words) & set(non_illustrious_words))
    }
    
    # 5. アップロードタイプの比較
    illustrious_upload_types = [v.get('upload_type') for v in illustrious_versions]
    non_illustrious_upload_types = [v.get('upload_type') for v in non_illustrious_versions]
    
    analysis['upload_type_comparison'] = {
        'illustrious_upload_types': list(set(filter(None, illustrious_upload_types))),
        'non_illustrious_upload_types': list(set(filter(None, non_illustrious_upload_types)))
    }
    
    # 6. 重要な差異の特定
    key_differences = []
    
    # ベースモデルの違い
    illustrious_base_set = set(analysis['base_model_comparison']['illustrious_base_models'])
    non_illustrious_base_set = set(analysis['base_model_comparison']['non_illustrious_base_models'])
    
    if illustrious_base_set != non_illustrious_base_set:
        key_differences.append({
            'category': 'base_model',
            'description': 'ベースモデルに違いがある',
            'illustrious_only': list(illustrious_base_set - non_illustrious_base_set),
            'non_illustrious_only': list(non_illustrious_base_set - illustrious_base_set)
        })
    
    # ファイルサイズの有意な違い
    illustrious_avg_size = analysis['file_size_comparison']['illustrious_avg_size_mb']
    non_illustrious_avg_size = analysis['file_size_comparison']['non_illustrious_avg_size_mb']
    
    if abs(illustrious_avg_size - non_illustrious_avg_size) > 100:  # 100MB以上の差
        key_differences.append({
            'category': 'file_size',
            'description': 'ファイルサイズに有意な違いがある',
            'illustrious_avg_mb': illustrious_avg_size,
            'non_illustrious_avg_mb': non_illustrious_avg_size
        })
    
    analysis['key_differences'] = key_differences
    
    return analysis


def main():
    """メイン関数"""
    load_dotenv()
    
    # APIキーの取得
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("❌ CIVITAI_API_KEY が設定されていません")
        return
    
    # APIクライアントの初期化
    client = CivitaiClient(api_key)
    
    # 比較対象のモデル（illustriousと非illustriousの両方のバージョンを持つモデル）
    models_to_compare = [
        (338712, "[PVC Style Model]Movable figure model XL"),
        (428826, "DAMN! [Pony/Illustrious Realistic Model]"),
        (241844, "Galena CAT - Galena Citron Anime Treasure"),
        (137193, "Golden CAT - Golden Citron Anime Treasure")
    ]
    
    print(f"🚀 CivitAI API バージョン詳細比較開始")
    print(f"📊 比較対象モデル数: {len(models_to_compare)}")
    
    all_comparisons = []
    
    # 各モデルの比較を実行
    for model_id, model_name in models_to_compare:
        comparison_result = compare_versions(client, model_id, model_name)
        all_comparisons.append(comparison_result)
        
        # 結果のサマリー表示
        if 'analysis' in comparison_result:
            print(f"\n📈 {model_name} の比較結果:")
            
            analysis = comparison_result['analysis']
            
            # ベースモデルの違い
            base_comp = analysis['base_model_comparison']
            print(f"  🔧 ベースモデル:")
            print(f"    illustrious: {base_comp['illustrious_base_models']}")
            print(f"    non-illustrious: {base_comp['non_illustrious_base_models']}")
            
            # ファイルサイズの違い
            size_comp = analysis['file_size_comparison']
            print(f"  📁 平均ファイルサイズ:")
            print(f"    illustrious: {size_comp['illustrious_avg_size_mb']:.1f} MB")
            print(f"    non-illustrious: {size_comp['non_illustrious_avg_size_mb']:.1f} MB")
            
            # 重要な差異
            key_diffs = analysis['key_differences']
            if key_diffs:
                print(f"  ⚠️  重要な差異:")
                for diff in key_diffs:
                    print(f"    - {diff['description']}")
        
        print(f"\n{'='*80}")
    
    # 全体の結果サマリー
    print(f"\n📈 全体比較結果サマリー")
    print(f"{'='*80}")
    
    total_models = len(all_comparisons)
    models_with_both = sum(1 for comp in all_comparisons if 
                          comp.get('illustrious_count', 0) > 0 and 
                          comp.get('non_illustrious_count', 0) > 0)
    
    print(f"📊 比較対象モデル数: {total_models}")
    print(f"📊 両方のバージョンを持つモデル数: {models_with_both}")
    
    # 共通のパターンを分析
    print(f"\n🔍 共通パターン分析:")
    
    # ベースモデルの傾向
    all_illustrious_bases = set()
    all_non_illustrious_bases = set()
    
    for comp in all_comparisons:
        if 'analysis' in comp:
            base_comp = comp['analysis']['base_model_comparison']
            all_illustrious_bases.update(base_comp.get('illustrious_base_models', []))
            all_non_illustrious_bases.update(base_comp.get('non_illustrious_base_models', []))
    
    print(f"  🔧 illustriousバージョンで使用されるベースモデル:")
    for base in sorted(all_illustrious_bases):
        print(f"    - {base}")
    
    print(f"  🔧 non-illustriousバージョンで使用されるベースモデル:")
    for base in sorted(all_non_illustrious_bases):
        print(f"    - {base}")
    
    # 結果をJSONファイルに保存
    output_file = f"outputs/analysis/detailed_version_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 詳細比較結果を保存: {output_file}")


if __name__ == "__main__":
    main()