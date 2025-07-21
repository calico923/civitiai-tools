#!/usr/bin/env python3
"""CivitAI APIの画像ダウンロード機能を検証するスクリプト"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import CivitaiClient

# 環境変数読み込み
load_dotenv()

def test_image_download():
    """画像ダウンロードのテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません。")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== 画像ダウンロード機能テスト ===\n")
    
    # 1. モデルから画像URLを取得
    print("1. モデルから画像URLを取得")
    print("-" * 50)
    
    try:
        # 人気モデルを1つ取得
        response = client.search_models(limit=1, sort="Most Downloaded")
        
        if 'items' in response and len(response['items']) > 0:
            model = response['items'][0]
            print(f"モデル: {model.get('name', 'Unknown')} (ID: {model.get('id')})")
            
            # modelVersionsから画像を探す
            if 'modelVersions' in model and len(model['modelVersions']) > 0:
                version = model['modelVersions'][0]
                if 'images' in version and len(version['images']) > 0:
                    image = version['images'][0]
                    image_url = image.get('url')
                    
                    print(f"\n画像情報:")
                    print(f"  ID: {image.get('id')}")
                    print(f"  URL: {image_url}")
                    print(f"  サイズ: {image.get('width')}x{image.get('height')}")
                    print(f"  タイプ: {image.get('type')}")
                    print(f"  NSFW レベル: {image.get('nsfwLevel')}")
                    
                    # URLの構造を分析
                    if image_url:
                        print(f"\nURL構造の分析:")
                        print(f"  ベースURL: {image_url.split('/width=')[0]}")
                        if '/width=' in image_url:
                            print(f"  幅指定: {image_url.split('/width=')[1].split('/')[0]}")
                        
                        # 様々なサイズのURLを生成
                        base_url = image_url.split('/width=')[0]
                        sizes = [256, 512, 1024, 2048]
                        print(f"\n利用可能なサイズ:")
                        for size in sizes:
                            print(f"  - {size}px: {base_url}/width={size}/{image.get('id')}.jpeg")
                    
                    # 2. 画像のダウンロードテスト
                    print(f"\n\n2. 画像ダウンロードテスト")
                    print("-" * 50)
                    
                    if image_url:
                        # 小さいサイズでテスト
                        test_url = f"{base_url}/width=256/{image.get('id')}.jpeg"
                        print(f"テストURL: {test_url}")
                        
                        try:
                            # ダウンロードリクエスト
                            headers = {
                                'User-Agent': 'CivitaiModelDownloader/1.0'
                            }
                            response = requests.get(test_url, headers=headers, timeout=30)
                            response.raise_for_status()
                            
                            print(f"ダウンロード成功!")
                            print(f"  ステータスコード: {response.status_code}")
                            print(f"  コンテンツタイプ: {response.headers.get('content-type')}")
                            print(f"  コンテンツサイズ: {len(response.content)} bytes")
                            
                            # 保存テスト
                            output_dir = "test_images"
                            os.makedirs(output_dir, exist_ok=True)
                            
                            filename = f"{output_dir}/test_image_{image.get('id')}.jpeg"
                            with open(filename, 'wb') as f:
                                f.write(response.content)
                            
                            print(f"  保存先: {filename}")
                            
                        except Exception as e:
                            print(f"ダウンロードエラー: {e}")
        
    except Exception as e:
        print(f"エラー: {e}")
    
    # 3. /api/v1/images エンドポイントから画像情報を取得
    print(f"\n\n3. /api/v1/images エンドポイントの詳細調査")
    print("-" * 50)
    
    try:
        # パラメータオプションを調査
        params_to_test = [
            {'limit': 5},
            {'limit': 5, 'sort': 'Most Reactions'},
            {'limit': 5, 'period': 'Day'},
            {'limit': 5, 'nsfw': 'false'}
        ]
        
        for params in params_to_test:
            print(f"\nパラメータ: {params}")
            try:
                response = client.request('GET', '/images', params=params)
                data = response.json()
                
                if 'items' in data:
                    print(f"  画像数: {len(data['items'])}")
                    if 'metadata' in data:
                        print(f"  メタデータ: {data['metadata']}")
                        
            except Exception as e:
                print(f"  エラー: {e}")
    
    except Exception as e:
        print(f"エラー: {e}")
    
    # 4. モデル詳細APIから全画像リストを取得
    print(f"\n\n4. モデル詳細から全画像リストを取得")
    print("-" * 50)
    
    try:
        # 特定のモデルIDで詳細を取得
        model_id = 4201  # Realistic Vision
        print(f"モデルID {model_id} の詳細を取得...")
        
        detail = client.get_model_by_id(model_id)
        
        all_images = []
        
        # modelVersionsから全画像を収集
        if 'modelVersions' in detail:
            for version in detail['modelVersions']:
                version_name = version.get('name', 'Unknown')
                if 'images' in version:
                    print(f"\nバージョン '{version_name}' の画像:")
                    for img in version['images']:
                        all_images.append({
                            'version': version_name,
                            'id': img.get('id'),
                            'url': img.get('url'),
                            'width': img.get('width'),
                            'height': img.get('height'),
                            'nsfwLevel': img.get('nsfwLevel')
                        })
                        print(f"  - ID: {img.get('id')}, サイズ: {img.get('width')}x{img.get('height')}")
        
        print(f"\n合計画像数: {len(all_images)}")
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_image_download()