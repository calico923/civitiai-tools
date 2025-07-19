#!/usr/bin/env python3
"""
CivitAI API での illustrious バージョン取得方法の調査

このスクリプトは以下を調査します：
1. モデルAPIレスポンスで複数バージョンがどのように返されるか
2. バージョンIDを使った特定バージョンの取得方法
3. illustriousバージョンを識別する方法（バージョン名、タグ、baseModelなど）
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


def print_json_pretty(data: dict, title: str = ""):
    """JSON データを見やすく表示"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def analyze_model_versions(client: CivitaiClient, model_id: int) -> dict:
    """
    特定のモデルのバージョン情報を分析
    
    Args:
        client: CivitaiClient instance
        model_id: 調査対象のモデルID
        
    Returns:
        分析結果辞書
    """
    print(f"\n🔍 モデル ID {model_id} の分析開始...")
    
    try:
        # モデルの詳細情報を取得
        model_data = client.get_model_by_id(model_id)
        
        # 基本情報の取得
        model_name = model_data.get('name', 'Unknown')
        model_type = model_data.get('type', 'Unknown')
        model_tags = model_data.get('tags', [])
        
        print(f"📋 モデル名: {model_name}")
        print(f"📋 モデル タイプ: {model_type}")
        print(f"📋 モデル タグ: {', '.join(model_tags[:10])}")
        
        # バージョン情報の分析
        model_versions = model_data.get('modelVersions', [])
        print(f"📋 バージョン数: {len(model_versions)}")
        
        analysis_result = {
            'model_id': model_id,
            'model_name': model_name,
            'model_type': model_type,
            'model_tags': model_tags,
            'version_count': len(model_versions),
            'versions': [],
            'illustrious_versions': [],
            'non_illustrious_versions': []
        }
        
        # 各バージョンの詳細分析
        for i, version in enumerate(model_versions):
            version_id = version.get('id')
            version_name = version.get('name', 'Unknown')
            version_base_model = version.get('baseModel', 'Unknown')
            version_description = version.get('description', '')
            version_files = version.get('files', [])
            
            print(f"\n  📌 バージョン {i+1}/{len(model_versions)}")
            print(f"    ID: {version_id}")
            print(f"    名前: {version_name}")
            print(f"    ベースモデル: {version_base_model}")
            print(f"    ファイル数: {len(version_files)}")
            
            version_info = {
                'version_id': version_id,
                'version_name': version_name,
                'base_model': version_base_model,
                'description': version_description,
                'files': []
            }
            
            # ファイル情報の分析
            for file in version_files:
                file_name = file.get('name', 'Unknown')
                file_size = file.get('sizeKB', 0)
                download_url = file.get('downloadUrl', '')
                
                file_info = {
                    'file_name': file_name,
                    'file_size_kb': file_size,
                    'download_url': download_url
                }
                version_info['files'].append(file_info)
                
                print(f"      📄 ファイル: {file_name} ({file_size} KB)")
            
            analysis_result['versions'].append(version_info)
            
            # illustrious バージョンの判定
            is_illustrious = check_illustrious_version(version_name, version_base_model, version_description)
            if is_illustrious:
                analysis_result['illustrious_versions'].append(version_info)
                print(f"    ✅ illustrious バージョンと判定")
            else:
                analysis_result['non_illustrious_versions'].append(version_info)
                print(f"    ❌ illustrious バージョンではない")
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        return {
            'model_id': model_id,
            'error': str(e)
        }


def check_illustrious_version(version_name: str, base_model: str, description: str) -> bool:
    """
    illustrious バージョンかどうかを判定
    
    Args:
        version_name: バージョン名
        base_model: ベースモデル
        description: 説明文
        
    Returns:
        illustrious バージョンかどうか
    """
    # 検索キーワード
    illustrious_keywords = [
        'illustrious',
        'ill',
        'ilxl',
        'illustrious-xl',
        'illustriousxl'
    ]
    
    # 各フィールドを小文字に変換して検索
    version_name_lower = version_name.lower()
    base_model_lower = base_model.lower()
    description_lower = description.lower()
    
    # いずれかのフィールドでキーワードが見つかればtrue
    for keyword in illustrious_keywords:
        if (keyword in version_name_lower or 
            keyword in base_model_lower or 
            keyword in description_lower):
            return True
    
    return False


def check_model_version_endpoint(client: CivitaiClient, version_id: int) -> dict:
    """
    バージョン固有のエンドポイントが存在するかチェック
    
    Args:
        client: CivitaiClient instance
        version_id: バージョンID
        
    Returns:
        エンドポイントの調査結果
    """
    print(f"\n🔍 バージョン ID {version_id} の個別エンドポイント調査...")
    
    # /api/v1/model-versions/{versionId} エンドポイントを試す
    try:
        response = client.request('GET', f'/model-versions/{version_id}')
        
        if response.status_code == 200:
            version_data = response.json()
            print(f"✅ バージョン個別エンドポイント成功")
            print(f"📋 レスポンス構造: {list(version_data.keys())}")
            
            return {
                'version_id': version_id,
                'endpoint_available': True,
                'version_data': version_data
            }
        else:
            print(f"❌ バージョン個別エンドポイント失敗: {response.status_code}")
            return {
                'version_id': version_id,
                'endpoint_available': False,
                'error': f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        return {
            'version_id': version_id,
            'endpoint_available': False,
            'error': str(e)
        }


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
    
    # 調査対象のモデルID（CSVファイルから取得）
    sample_model_ids = [
        1277670,  # JANKU v4 NSFW
        1045588,  # PornMaster-Pro
        1025051,  # Illustrij
        1125067,  # CyberIllustrious
        1232765,  # Illustrious XL 1.0
        338712,   # PVC Style Model
        428826,   # DAMN! [Pony/Illustrious]
        241844,   # Galena CAT
        137193,   # Golden CAT
        1153444   # ReallyBigLust
    ]
    
    print(f"🚀 CivitAI API illustrious バージョン調査開始")
    print(f"📊 調査対象モデル数: {len(sample_model_ids)}")
    
    all_results = []
    
    # 各モデルのバージョン情報を分析
    for model_id in sample_model_ids:
        result = analyze_model_versions(client, model_id)
        all_results.append(result)
        
        # 最初のモデルのバージョンでエンドポイント調査
        if result.get('versions') and len(all_results) == 1:
            first_version_id = result['versions'][0]['version_id']
            endpoint_result = check_model_version_endpoint(client, first_version_id)
            result['endpoint_check'] = endpoint_result
        
        print(f"\n{'='*60}")
    
    # 結果の集計
    print(f"\n📈 調査結果サマリー")
    print(f"{'='*60}")
    
    total_models = len(all_results)
    total_versions = sum(r.get('version_count', 0) for r in all_results if 'version_count' in r)
    total_illustrious = sum(len(r.get('illustrious_versions', [])) for r in all_results)
    total_non_illustrious = sum(len(r.get('non_illustrious_versions', [])) for r in all_results)
    
    print(f"📊 調査済みモデル数: {total_models}")
    print(f"📊 総バージョン数: {total_versions}")
    print(f"📊 illustrious バージョン数: {total_illustrious}")
    print(f"📊 non-illustrious バージョン数: {total_non_illustrious}")
    
    # 結果をJSONファイルに保存
    output_file = f"outputs/analysis/illustrious_version_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 分析結果を保存: {output_file}")
    
    # 具体的な判定方法を表示
    print(f"\n🎯 illustrious バージョンの判定方法")
    print(f"{'='*60}")
    print(f"以下のフィールドでキーワードを検索:")
    print(f"  - version_name (バージョン名)")
    print(f"  - base_model (ベースモデル)")
    print(f"  - description (説明文)")
    print(f"")
    print(f"判定キーワード:")
    print(f"  - illustrious")
    print(f"  - ill")
    print(f"  - ilxl")
    print(f"  - illustrious-xl")
    print(f"  - illustriousxl")
    
    # 代表的なillustriousバージョンの詳細表示
    print(f"\n🔍 代表的なillustriousバージョンの詳細")
    print(f"{'='*60}")
    
    for result in all_results[:3]:  # 最初の3つのモデルのみ
        if result.get('illustrious_versions'):
            model_name = result.get('model_name', 'Unknown')
            print(f"\n📋 {model_name} (ID: {result['model_id']})")
            
            for version in result['illustrious_versions']:
                print(f"  ✅ バージョン: {version['version_name']}")
                print(f"     ID: {version['version_id']}")
                print(f"     ベースモデル: {version['base_model']}")
                if version['files']:
                    print(f"     ファイル数: {len(version['files'])}")
                    for file in version['files'][:1]:  # 最初のファイルのみ
                        print(f"       📄 {file['file_name']} ({file['file_size_kb']} KB)")


if __name__ == "__main__":
    main()