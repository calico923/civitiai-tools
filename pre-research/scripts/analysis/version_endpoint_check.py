#!/usr/bin/env python3
"""
CivitAI API のバージョン固有エンドポイントの調査

以下のエンドポイントを調査します：
- /api/v1/model-versions/{versionId}
- /api/v1/models/{modelId}/versions/{versionId}
- その他のバージョン関連エンドポイント
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


def test_version_endpoints(client: CivitaiClient, version_id: int, model_id: int) -> dict:
    """
    バージョン関連の各エンドポイントをテスト
    
    Args:
        client: CivitaiClient instance
        version_id: バージョンID
        model_id: モデルID
        
    Returns:
        テスト結果辞書
    """
    print(f"\n🔍 バージョン ID {version_id} (モデル ID {model_id}) のエンドポイント調査...")
    
    test_results = {
        'version_id': version_id,
        'model_id': model_id,
        'endpoints': {}
    }
    
    # 1. /api/v1/model-versions/{versionId}
    print(f"  📡 /api/v1/model-versions/{version_id}")
    try:
        response = client.request('GET', f'/model-versions/{version_id}')
        
        if response.status_code == 200:
            version_data = response.json()
            test_results['endpoints']['model_versions_id'] = {
                'status': 'success',
                'status_code': response.status_code,
                'data_keys': list(version_data.keys()),
                'data_sample': {k: v for k, v in version_data.items() if k in ['id', 'name', 'baseModel', 'description']}
            }
            print(f"    ✅ 成功: {response.status_code}")
            print(f"    📋 データキー: {list(version_data.keys())}")
        else:
            test_results['endpoints']['model_versions_id'] = {
                'status': 'failed',
                'status_code': response.status_code,
                'error': f"HTTP {response.status_code}"
            }
            print(f"    ❌ 失敗: {response.status_code}")
            
    except Exception as e:
        test_results['endpoints']['model_versions_id'] = {
            'status': 'error',
            'error': str(e)
        }
        print(f"    ❌ エラー: {e}")
    
    # 2. /api/v1/models/{modelId}/versions/{versionId}
    print(f"  📡 /api/v1/models/{model_id}/versions/{version_id}")
    try:
        response = client.request('GET', f'/models/{model_id}/versions/{version_id}')
        
        if response.status_code == 200:
            version_data = response.json()
            test_results['endpoints']['models_id_versions_id'] = {
                'status': 'success',
                'status_code': response.status_code,
                'data_keys': list(version_data.keys()),
                'data_sample': {k: v for k, v in version_data.items() if k in ['id', 'name', 'baseModel', 'description']}
            }
            print(f"    ✅ 成功: {response.status_code}")
            print(f"    📋 データキー: {list(version_data.keys())}")
        else:
            test_results['endpoints']['models_id_versions_id'] = {
                'status': 'failed',
                'status_code': response.status_code,
                'error': f"HTTP {response.status_code}"
            }
            print(f"    ❌ 失敗: {response.status_code}")
            
    except Exception as e:
        test_results['endpoints']['models_id_versions_id'] = {
            'status': 'error',
            'error': str(e)
        }
        print(f"    ❌ エラー: {e}")
    
    # 3. /api/v1/models/{modelId}/versions
    print(f"  📡 /api/v1/models/{model_id}/versions")
    try:
        response = client.request('GET', f'/models/{model_id}/versions')
        
        if response.status_code == 200:
            versions_data = response.json()
            test_results['endpoints']['models_id_versions'] = {
                'status': 'success',
                'status_code': response.status_code,
                'data_keys': list(versions_data.keys()) if isinstance(versions_data, dict) else 'array',
                'data_sample': versions_data[:2] if isinstance(versions_data, list) else versions_data
            }
            print(f"    ✅ 成功: {response.status_code}")
            if isinstance(versions_data, list):
                print(f"    📋 配列データ: {len(versions_data)}個のバージョン")
            else:
                print(f"    📋 データキー: {list(versions_data.keys())}")
        else:
            test_results['endpoints']['models_id_versions'] = {
                'status': 'failed',
                'status_code': response.status_code,
                'error': f"HTTP {response.status_code}"
            }
            print(f"    ❌ 失敗: {response.status_code}")
            
    except Exception as e:
        test_results['endpoints']['models_id_versions'] = {
            'status': 'error',
            'error': str(e)
        }
        print(f"    ❌ エラー: {e}")
    
    # 4. ダウンロードURL関連
    print(f"  📡 ダウンロードURL: /api/download/models/{version_id}")
    try:
        download_url = f"https://civitai.com/api/download/models/{version_id}"
        response = requests.head(download_url, headers={
            "Authorization": f"Bearer {client.api_key}",
            "User-Agent": "CivitaiModelDownloader/1.0"
        }, timeout=10)
        
        test_results['endpoints']['download_url'] = {
            'status': 'success' if response.status_code in [200, 302] else 'failed',
            'status_code': response.status_code,
            'url': download_url,
            'headers': dict(response.headers)
        }
        print(f"    ✅ ダウンロードURL確認: {response.status_code}")
        
    except Exception as e:
        test_results['endpoints']['download_url'] = {
            'status': 'error',
            'error': str(e)
        }
        print(f"    ❌ ダウンロードURL エラー: {e}")
    
    return test_results


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
    
    # テスト対象のバージョンID（分析結果から取得）
    test_cases = [
        # (version_id, model_id, description)
        (1945718, 1045588, "PornMaster-Pro - illustrious バージョン"),
        (1204729, 1045588, "PornMaster-Pro - illustrious バージョン (古い)"),
        (1223484, 338712, "PVC Style Model - NoobAI バージョン"),
        (924390, 338712, "PVC Style Model - illustrious バージョン"),
        (1809238, 428826, "DAMN! - illustrious バージョン"),
        (695277, 428826, "DAMN! - Pony バージョン"),
        (1389133, 1232765, "Illustrious XL 1.0 - illustrious バージョン"),
        (2001618, 1025051, "Illustrij - illustrious バージョン"),
        (1973422, 1125067, "CyberIllustrious - illustrious バージョン"),
        (1327422, 1153444, "ReallyBigLust - illustrious バージョン")
    ]
    
    print(f"🚀 CivitAI API バージョンエンドポイント調査開始")
    print(f"📊 テストケース数: {len(test_cases)}")
    
    all_results = []
    
    # 各バージョンのエンドポイントをテスト
    for version_id, model_id, description in test_cases:
        print(f"\n{'='*80}")
        print(f"🔍 {description}")
        print(f"    バージョンID: {version_id}")
        print(f"    モデルID: {model_id}")
        
        result = test_version_endpoints(client, version_id, model_id)
        all_results.append(result)
        
        print(f"{'='*80}")
    
    # 結果の集計
    print(f"\n📈 エンドポイント調査結果サマリー")
    print(f"{'='*80}")
    
    endpoint_stats = {}
    for result in all_results:
        for endpoint_name, endpoint_result in result.get('endpoints', {}).items():
            if endpoint_name not in endpoint_stats:
                endpoint_stats[endpoint_name] = {'success': 0, 'failed': 0, 'error': 0}
            
            status = endpoint_result.get('status', 'unknown')
            if status in endpoint_stats[endpoint_name]:
                endpoint_stats[endpoint_name][status] += 1
    
    for endpoint_name, stats in endpoint_stats.items():
        total = sum(stats.values())
        success_rate = (stats['success'] / total) * 100 if total > 0 else 0
        
        print(f"\n📊 {endpoint_name}:")
        print(f"    成功: {stats['success']}/{total} ({success_rate:.1f}%)")
        print(f"    失敗: {stats['failed']}/{total}")
        print(f"    エラー: {stats['error']}/{total}")
    
    # 成功したエンドポイントの詳細表示
    print(f"\n🎯 成功したエンドポイントの詳細")
    print(f"{'='*80}")
    
    for result in all_results[:3]:  # 最初の3つのテストケースのみ
        version_id = result['version_id']
        model_id = result['model_id']
        
        print(f"\n📋 バージョン {version_id} (モデル {model_id})")
        
        for endpoint_name, endpoint_result in result.get('endpoints', {}).items():
            if endpoint_result.get('status') == 'success':
                print(f"  ✅ {endpoint_name}")
                
                if 'data_sample' in endpoint_result:
                    print(f"    サンプルデータ: {endpoint_result['data_sample']}")
                
                if 'data_keys' in endpoint_result:
                    print(f"    データキー: {endpoint_result['data_keys']}")
    
    # 結果をJSONファイルに保存
    output_file = f"outputs/analysis/version_endpoint_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 エンドポイント調査結果を保存: {output_file}")


if __name__ == "__main__":
    main()