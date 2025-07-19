#!/usr/bin/env python3
"""CivitAI APIのページネーション問題を詳細調査"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient


def debug_api_pagination():
    """APIのページネーション情報を詳細に調査"""
    
    load_dotenv()
    api_key = os.getenv('CIVITAI_API_KEY')
    
    if not api_key:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        return
    
    client = CivitaiClient(api_key)
    
    print("=== CivitAI API ページネーション詳細調査 ===\n")
    
    # 1. styleタグLoRAの1ページ目のメタデータを確認
    print("1. styleタグLoRAの1ページ目メタデータ確認")
    print("-" * 50)
    
    try:
        response = client.search_models(
            types=["LORA"],
            tag="style",
            sort="Highest Rated",
            limit=100,
            page=1
        )
        
        items = response.get("items", [])
        metadata = response.get("metadata", {})
        
        print(f"取得アイテム数: {len(items)}")
        print(f"メタデータ: {metadata}")
        
        # 重要な情報を抜粋
        total_items = metadata.get("totalItems", 0)
        total_pages = metadata.get("totalPages", 0)
        current_page = metadata.get("currentPage", 0)
        page_size = metadata.get("pageSize", 0)
        
        print(f"\n📊 重要情報:")
        print(f"  総アイテム数: {total_items}")
        print(f"  総ページ数: {total_pages}")
        print(f"  現在のページ: {current_page}")
        print(f"  ページサイズ: {page_size}")
        
        # 2. 全ページを取得してみる
        if total_pages > 1:
            print(f"\n2. 全{total_pages}ページの取得テスト")
            print("-" * 50)
            
            all_models = []
            all_models.extend(items)
            
            for page in range(2, min(total_pages + 1, 11)):  # 最大10ページまでテスト
                print(f"\nページ {page}/{total_pages} を取得中...")
                
                try:
                    response = client.search_models(
                        types=["LORA"],
                        tag="style",
                        sort="Highest Rated",
                        limit=100,
                        page=page
                    )
                    
                    page_items = response.get("items", [])
                    print(f"  取得数: {len(page_items)}")
                    
                    all_models.extend(page_items)
                    
                    # サンプル表示
                    if page_items:
                        print(f"  サンプル: {page_items[0].get('name', 'Unknown')}")
                    
                except Exception as e:
                    print(f"  エラー: {e}")
                    break
            
            print(f"\n📈 取得結果:")
            print(f"  実際に取得したモデル数: {len(all_models)}")
            print(f"  APIが報告する総数: {total_items}")
            print(f"  差分: {total_items - len(all_models)}")
            
            # 重複チェック
            model_ids = [model.get('id') for model in all_models]
            unique_ids = set(model_ids)
            print(f"  重複除去後: {len(unique_ids)}個")
            
        else:
            print(f"\n⚠️  総ページ数が1なので、全データが1ページに含まれているとAPIが報告")
            print(f"しかし、この報告が正しいかは疑問です")
        
        # 3. 異なるソート条件での確認
        print(f"\n3. 異なるソート条件での確認")
        print("-" * 50)
        
        for sort_type in ["Most Downloaded", "Newest"]:
            print(f"\n{sort_type}での確認:")
            try:
                response = client.search_models(
                    types=["LORA"],
                    tag="style",
                    sort=sort_type,
                    limit=100,
                    page=1
                )
                
                items = response.get("items", [])
                metadata = response.get("metadata", {})
                total_items = metadata.get("totalItems", 0)
                total_pages = metadata.get("totalPages", 0)
                
                print(f"  取得数: {len(items)}")
                print(f"  総アイテム数: {total_items}")
                print(f"  総ページ数: {total_pages}")
                
            except Exception as e:
                print(f"  エラー: {e}")
        
        # 4. limitパラメータの影響確認
        print(f"\n4. limitパラメータの影響確認")
        print("-" * 50)
        
        for limit in [20, 50, 100]:
            print(f"\nlimit={limit}での確認:")
            try:
                response = client.search_models(
                    types=["LORA"],
                    tag="style",
                    sort="Highest Rated",
                    limit=limit,
                    page=1
                )
                
                items = response.get("items", [])
                metadata = response.get("metadata", {})
                total_items = metadata.get("totalItems", 0)
                total_pages = metadata.get("totalPages", 0)
                
                print(f"  取得数: {len(items)}")
                print(f"  総アイテム数: {total_items}")
                print(f"  総ページ数: {total_pages}")
                
            except Exception as e:
                print(f"  エラー: {e}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_api_pagination()