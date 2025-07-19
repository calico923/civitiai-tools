#!/usr/bin/env python3
"""CivitAI APIの画像データ構造を詳細に調査するスクリプト"""

import os
import sys
import json
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import CivitaiClient

# 環境変数読み込み
load_dotenv()

def investigate_image_structure():
    """画像データ構造の詳細調査"""
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません。")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== CivitAI API 画像データ構造調査 ===\n")
    
    # 1. モデル一覧APIの生データを確認
    print("1. モデル一覧APIの生のレスポンス構造")
    print("-" * 50)
    
    try:
        response = client.search_models(limit=1, sort="Most Downloaded")
        
        if 'items' in response and len(response['items']) > 0:
            model = response['items'][0]
            
            # モデルの基本情報
            print(f"モデル名: {model.get('name')}")
            print(f"モデルID: {model.get('id')}")
            
            # modelVersionsの最初のバージョンを詳細に確認
            if 'modelVersions' in model and len(model['modelVersions']) > 0:
                version = model['modelVersions'][0]
                print(f"\nバージョン名: {version.get('name')}")
                
                # imagesフィールドの内容を詳細に出力
                if 'images' in version and len(version['images']) > 0:
                    print(f"\nimages配列の要素数: {len(version['images'])}")
                    print("\n最初の3つの画像データ:")
                    
                    for i, img in enumerate(version['images'][:3]):
                        print(f"\n--- 画像 {i+1} ---")
                        print(json.dumps(img, indent=2, ensure_ascii=False))
                        
    except Exception as e:
        print(f"エラー: {e}")
    
    # 2. /api/v1/images エンドポイントの構造確認
    print("\n\n2. /api/v1/images エンドポイントのデータ構造")
    print("-" * 50)
    
    try:
        response = client.request('GET', '/images', params={'limit': 2})
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            print(f"画像数: {len(data['items'])}")
            print("\n最初の画像の完全なデータ構造:")
            print(json.dumps(data['items'][0], indent=2, ensure_ascii=False))
            
            # メタデータの確認
            if 'metadata' in data:
                print("\nメタデータ:")
                print(json.dumps(data['metadata'], indent=2))
                
    except Exception as e:
        print(f"エラー: {e}")
    
    # 3. モデル詳細APIから画像データを取得
    print("\n\n3. モデル詳細APIの画像データ構造")
    print("-" * 50)
    
    try:
        # 特定のモデルIDで詳細を取得
        model_id = 4201
        detail = client.get_model_by_id(model_id)
        
        print(f"モデル名: {detail.get('name')}")
        print(f"モデルID: {detail.get('id')}")
        
        # 最初のバージョンの画像を確認
        if 'modelVersions' in detail and len(detail['modelVersions']) > 0:
            version = detail['modelVersions'][0]
            print(f"\nバージョン名: {version.get('name')}")
            
            if 'images' in version and len(version['images']) > 0:
                print(f"画像数: {len(version['images'])}")
                print("\n最初の画像の詳細:")
                print(json.dumps(version['images'][0], indent=2, ensure_ascii=False))
                
                # 画像URLのパターンを分析
                print("\n画像URLパターン分析:")
                for i, img in enumerate(version['images'][:5]):
                    url = img.get('url', '')
                    print(f"\n画像 {i+1}:")
                    print(f"  完全URL: {url}")
                    
                    # URLの構成要素を分解
                    if 'image.civitai.com' in url:
                        parts = url.split('/')
                        print(f"  ドメイン: {parts[2]}")
                        print(f"  パス1: {parts[3]}")
                        print(f"  パス2: {parts[4]}")
                        if 'width=' in url:
                            print(f"  幅指定: {url.split('width=')[1].split('/')[0]}")
                        if len(parts) > 6:
                            print(f"  ファイル名: {parts[-1]}")
                
    except Exception as e:
        print(f"エラー: {e}")
    
    # 4. 画像関連のすべてのフィールドをリストアップ
    print("\n\n4. 画像オブジェクトの全フィールド分析")
    print("-" * 50)
    
    try:
        # /api/v1/images から画像を1つ取得
        response = client.request('GET', '/images', params={'limit': 1})
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            image = data['items'][0]
            
            print("画像オブジェクトのすべてのフィールド:")
            for key, value in image.items():
                value_type = type(value).__name__
                if isinstance(value, (dict, list)):
                    print(f"  {key} ({value_type}): {len(value)} items" if isinstance(value, list) else f"  {key} ({value_type}): {len(value)} keys")
                else:
                    print(f"  {key} ({value_type}): {value}")
            
            # metaフィールドの詳細
            if 'meta' in image and isinstance(image['meta'], dict):
                print("\nmetaフィールドの内容:")
                for key, value in image['meta'].items():
                    print(f"  {key}: {value if len(str(value)) < 100 else str(value)[:100] + '...'}")
                    
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    investigate_image_structure()