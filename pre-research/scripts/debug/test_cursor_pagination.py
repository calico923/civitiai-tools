#!/usr/bin/env python3
"""CivitAI APIのカーソルベースページネーションをテスト"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient


def test_cursor_pagination():
    """カーソルベースのページネーションをテスト"""
    
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== CivitAI API カーソルベースページネーション テスト ===\n")
    
    all_models = []
    cursor = None
    page_count = 0
    max_pages = 20  # 安全のため最大20ページ
    
    while page_count < max_pages:
        page_count += 1
        print(f"ページ {page_count} を取得中...")
        
        try:
            # カーソルを使ってリクエスト
            params = {
                "types": ["LORA"],
                "tag": "style",
                "sort": "Highest Rated",
                "limit": 100,
                "page": 1  # カーソルを使う場合もpage=1
            }
            
            if cursor:
                # 直接URLを構築してカーソルを追加
                url = f"{client.base_url}/models"
                url += f"?limit=100&page=1&sort=Highest+Rated&types=LORA&tag=style&cursor={cursor}"
                
                print(f"  カーソル使用: {cursor}")
                print(f"  URL: {url}")
                
                response = client.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
            else:
                # 初回リクエスト
                data = client.search_models(**params)
            
            items = data.get("items", [])
            metadata = data.get("metadata", {})
            
            print(f"  取得数: {len(items)}")
            print(f"  メタデータ: {metadata}")
            
            if not items:
                print("  データがありません。終了します。")
                break
            
            all_models.extend(items)
            
            # サンプル表示
            if items:
                print(f"  サンプル: {items[0].get('name', 'Unknown')}")
            
            # 次のカーソルを取得
            next_cursor = metadata.get("nextCursor")
            if not next_cursor:
                print("  nextCursorがありません。すべてのデータを取得しました。")
                break
            
            cursor = next_cursor
            
        except Exception as e:
            print(f"  エラー: {e}")
            break
    
    print(f"\n=== 取得結果 ===")
    print(f"総取得ページ数: {page_count}")
    print(f"総取得モデル数: {len(all_models)}")
    
    # 重複チェック
    model_ids = [model.get('id') for model in all_models]
    unique_ids = set(model_ids)
    print(f"重複除去後: {len(unique_ids)}個")
    
    if len(model_ids) != len(unique_ids):
        print(f"⚠️  重複があります: {len(model_ids) - len(unique_ids)}個")
    
    # サンプル表示
    print(f"\n=== サンプルモデル（最初の10個） ===")
    for i, model in enumerate(all_models[:10], 1):
        name = model.get('name', 'Unknown')
        tags = model.get('tags', [])
        print(f"{i:2d}. {name}")
        print(f"    タグ: {', '.join(tags[:5])}")
        print()
    
    return all_models


if __name__ == "__main__":
    models = test_cursor_pagination()