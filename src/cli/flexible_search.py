#!/usr/bin/env python3
"""環境変数で設定可能な柔軟なモデル検索スクリプト"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


def get_search_config():
    """環境変数から検索設定を取得"""
    config = {
        'api_key': os.getenv('CIVITAI_API_KEY'),
        'sort': os.getenv('SEARCH_SORT', 'Most Downloaded'),
        'method': os.getenv('SEARCH_METHOD', 'extended'),
        'tag': os.getenv('SEARCH_TAG', 'illustrious'),
        'type': os.getenv('SEARCH_TYPE', 'Checkpoint'),
        'max_pages': int(os.getenv('MAX_PAGES', 3)),
        'output_format': os.getenv('OUTPUT_FORMAT', 'csv'),
        'additional_tag': os.getenv('ADDITIONAL_TAG'),
    }
    return config


def search_models_by_config(client: CivitaiClient, config: dict):
    """設定に基づいてモデルを検索"""
    search_type = [config['type']]
    tag = config['tag']
    sort = config['sort']
    max_pages = config['max_pages']
    method = config['method']
    
    print(f"検索設定:")
    print(f"  - タイプ: {config['type']}")
    print(f"  - タグ: {tag}")
    if config.get('additional_tag'):
        print(f"  - 追加タグ: {config['additional_tag']}")
    print(f"  - ソート: {sort}")
    print(f"  - 検索方法: {method}")
    print(f"  - 最大ページ: {max_pages}")
    
    if method == 'tag_only':
        # タグのみで検索
        print(f"\n🏷️  タグ検索のみ実行中...")
        response = client.search_models(
            types=search_type,
            tag=tag,
            sort=sort,
            limit=100,
            page=1
        )
        
        models = response.get("items", [])
        print(f"  {len(models)}個のモデルを発見")
        
        return models
        
    elif method == 'name_only':
        # 名前検索のみ
        print(f"\n📝 名前検索のみ実行中...")
        all_models = []
        model_ids = set()
        
        for page in range(1, max_pages + 1):
            print(f"\n  ページ {page} を検索中...")
            response = client.search_models(
                types=search_type,
                sort=sort,
                limit=100,
                page=page
            )
            
            items = response.get("items", [])
            print(f"    {len(items)}個のモデルを取得")
            
            # 名前にタグを含むモデルをフィルタリング
            for model in items:
                if tag.lower() in model.get('name', '').lower():
                    if model['id'] not in model_ids:
                        all_models.append(model)
                        model_ids.add(model['id'])
                        print(f"    発見: {model.get('name', 'Unknown')} (ID: {model.get('id')})")
        
        print(f"\n  合計 {len(all_models)} 個の名前マッチモデルを発見")
        return all_models
        
    elif method == 'extended':
        # 拡張検索（タグ + 名前）
        print(f"\n🔍 拡張検索実行中...")
        additional_tag = config.get('additional_tag')
        return client.search_models_extended(tag=tag, model_type=config['type'], max_requests=max_pages, sort=sort, additional_tag=additional_tag)
    
    else:
        raise ValueError(f"不明な検索方法: {method}")


def main():
    print("=== 柔軟なモデル検索ツール ===\n")
    print("環境変数(.env)の設定に基づいて検索を実行します")
    
    # 環境変数の読み込み
    load_dotenv()
    config = get_search_config()
    
    if not config['api_key']:
        print("エラー: CIVITAI_API_KEYが設定されていません")
        print(".envファイルでAPIキーを設定してください")
        return
    
    print(f"\nAPIキー: {config['api_key'][:8]}...")
    
    try:
        # APIクライアントの初期化
        print("\n1. Civitai APIクライアントを初期化中...")
        client = CivitaiClient(config['api_key'])
        
        # 設定に基づいて検索実行
        print("\n2. モデル検索を実行中...")
        models = search_models_by_config(client, config)
        
        if not models:
            print(f"\n{config['tag']}関連の{config['type']}が見つかりませんでした")
            return
        
        # URL収集器の初期化
        print("\n3. URL収集器を初期化中...")
        collector = URLCollector()
        
        # URLを収集
        print("\n4. ダウンロードURLを収集中...")
        urls = collector.collect_model_urls(models)
        print(f"   {len(urls)}個のダウンロードURLを収集")
        
        if not urls:
            print("ダウンロード可能なURLが見つかりませんでした")
            return
        
        # 結果を出力
        print("\n5. 結果をエクスポート中...")
        
        # ファイル名を設定に基づいて生成
        filename_base = f"{config['tag']}_{config['type'].lower()}_{config['method']}_{config['sort'].lower().replace(' ', '_')}"
        
        # 各形式で出力
        csv_file = collector.export_to_csv(urls, f"{filename_base}.csv")
        print(f"   CSV: {csv_file}")
        
        json_file = collector.export_to_json(urls, f"{filename_base}.json")
        print(f"   JSON: {json_file}")
        
        text_file = collector.export_to_text(urls, f"{filename_base}.txt")
        print(f"   Text: {text_file}")
        
        # 詳細を表示
        print(f"\n=== 収集結果詳細 ===")
        print(f"総モデル数: {len(urls)}")
        
        total_size_mb = sum(url.file_size for url in urls) / (1024 * 1024)
        print(f"総ファイルサイズ: {total_size_mb:.1f} MB")
        
        print(f"\n=== トップ5モデル ===")
        for i, url in enumerate(urls[:5], 1):
            print(f"{i:2d}. {url.model_name}")
            print(f"     タイプ: {url.model_type}")
            print(f"     サイズ: {url.file_size / (1024*1024):.1f} MB")
            print(f"     作成者: {url.creator}")
            print(f"     URL: {url.download_url}")
            print()
        
        if len(urls) > 5:
            print(f"（他 {len(urls) - 5} 個のモデル）")
        
        print(f"\n=== 設定変更方法 ===")
        print("検索条件を変更するには .env ファイルを編集してください:")
        print(f"  SEARCH_SORT={config['sort']} → 'Highest Rated' または 'Newest'")
        print(f"  SEARCH_METHOD={config['method']} → 'tag_only' または 'name_only' または 'extended'")
        print(f"  SEARCH_TAG={config['tag']} → 他のタグ名")
        print(f"  SEARCH_TYPE={config['type']} → 'LORA' または 'TextualInversion' など")
        
        print(f"\n=== 完了 ===")
        print(f"全ファイルは {collector.output_dir} に保存されました")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()