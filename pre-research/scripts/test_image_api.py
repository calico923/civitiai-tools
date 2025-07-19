#!/usr/bin/env python3
"""CivitAI APIの画像取得機能を調査するスクリプト"""

import os
import sys
import json
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import CivitaiClient

# 環境変数読み込み
load_dotenv()

def investigate_image_api():
    """画像APIの調査"""
    api_key = os.getenv('CIVITAI_API_KEY')
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません。")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== CivitAI API 画像機能調査 ===\n")
    
    # 1. モデル一覧APIから画像情報を確認
    print("1. /api/v1/models エンドポイントの画像情報確認")
    print("-" * 50)
    
    try:
        # 少数のモデルを取得
        response = client.search_models(limit=2, sort="Most Downloaded")
        
        if 'items' in response and len(response['items']) > 0:
            for i, model in enumerate(response['items']):
                print(f"\nモデル {i+1}:")
                print(f"  名前: {model.get('name', 'Unknown')}")
                print(f"  ID: {model.get('id', 'Unknown')}")
                
                # 画像関連フィールドを探す
                if 'images' in model:
                    print(f"  画像数: {len(model['images'])}")
                    if len(model['images']) > 0:
                        print("  最初の画像:")
                        image = model['images'][0]
                        for key, value in image.items():
                            if isinstance(value, (dict, list)):
                                print(f"    {key}: {json.dumps(value, indent=6)}")
                            else:
                                print(f"    {key}: {value}")
                
                # modelVersionsの中の画像も確認
                if 'modelVersions' in model and len(model['modelVersions']) > 0:
                    version = model['modelVersions'][0]
                    print(f"\n  最初のバージョン:")
                    print(f"    バージョン名: {version.get('name', 'Unknown')}")
                    if 'images' in version:
                        print(f"    バージョン画像数: {len(version['images'])}")
                        if len(version['images']) > 0:
                            print("    最初のバージョン画像:")
                            v_image = version['images'][0]
                            for key, value in v_image.items():
                                if isinstance(value, (dict, list)):
                                    print(f"      {key}: {json.dumps(value, indent=8)}")
                                else:
                                    print(f"      {key}: {value}")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"エラー: {e}")
    
    # 2. 特定モデルの詳細情報から画像を確認
    print("\n2. /api/v1/models/{modelId} エンドポイントの画像情報確認")
    print("-" * 50)
    
    try:
        # 人気モデルの詳細を取得
        if 'items' in response and len(response['items']) > 0:
            model_id = response['items'][0]['id']
            print(f"モデルID {model_id} の詳細を取得中...")
            
            detail_response = client.get_model_by_id(model_id)
            
            print(f"\nモデル詳細:")
            print(f"  名前: {detail_response.get('name', 'Unknown')}")
            print(f"  ID: {detail_response.get('id', 'Unknown')}")
            
            # 画像情報の確認
            if 'images' in detail_response:
                print(f"  画像数: {len(detail_response['images'])}")
                if len(detail_response['images']) > 0:
                    print("  最初の画像の構造:")
                    image = detail_response['images'][0]
                    print(json.dumps(image, indent=4))
            
            # modelVersionsの画像も確認
            if 'modelVersions' in detail_response and len(detail_response['modelVersions']) > 0:
                version = detail_response['modelVersions'][0]
                if 'images' in version:
                    print(f"\n  バージョン '{version.get('name', 'Unknown')}' の画像数: {len(version['images'])}")
                    if len(version['images']) > 0:
                        print("  バージョン画像の構造:")
                        print(json.dumps(version['images'][0], indent=4))
        
    except Exception as e:
        print(f"エラー: {e}")
    
    # 3. 画像専用エンドポイントの探索
    print("\n\n3. 画像専用エンドポイントの探索")
    print("-" * 50)
    
    # /api/v1/images エンドポイントを試す
    print("試行: /api/v1/images")
    try:
        response = client.request('GET', '/images', params={'limit': 10})
        print("成功! /api/v1/images エンドポイントが存在します")
        data = response.json()
        
        if isinstance(data, dict) and 'items' in data:
            print(f"画像数: {len(data['items'])}")
            if len(data['items']) > 0:
                print("\n最初の画像:")
                print(json.dumps(data['items'][0], indent=2))
        else:
            print(f"レスポンス型: {type(data)}")
            if isinstance(data, list) and len(data) > 0:
                print(f"画像数: {len(data)}")
                print("\n最初の画像:")
                print(json.dumps(data[0], indent=2))
            else:
                print(f"レスポンス: {json.dumps(data, indent=2)}")
                
    except Exception as e:
        print(f"エラー: {e}")
    
    # 4. その他の画像関連エンドポイントを探索
    print("\n\n4. その他の画像関連エンドポイントの探索")
    print("-" * 50)
    
    # 画像IDで個別取得を試す
    if 'items' in response and len(response['items']) > 0:
        model = response['items'][0]
        if 'images' in model and len(model['images']) > 0:
            image_id = model['images'][0].get('id')
            if image_id:
                print(f"\n試行: /api/v1/images/{image_id}")
                try:
                    response = client.request('GET', f'/images/{image_id}')
                    print("成功! 個別画像取得エンドポイントが存在します")
                    data = response.json()
                    print(json.dumps(data, indent=2))
                except Exception as e:
                    print(f"エラー: {e}")

if __name__ == "__main__":
    investigate_image_api()