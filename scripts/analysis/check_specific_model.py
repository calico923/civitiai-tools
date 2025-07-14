#!/usr/bin/env python3
"""特定のモデルの詳細を確認するスクリプト"""

import os
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
api_key = os.getenv('CIVITAI_API_KEY')

# モデルID
model_id = 827184

# APIリクエスト
headers = {
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "CivitaiModelDownloader/1.0"
}

# モデル詳細を取得
url = f"https://civitai.com/api/v1/models/{model_id}"
print(f"APIリクエスト: {url}")

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    model_data = response.json()
    
    print(f"\nモデル情報:")
    print(f"  ID: {model_data.get('id')}")
    print(f"  名前: {model_data.get('name')}")
    print(f"  タイプ: {model_data.get('type')}")
    print(f"  作成者: {model_data.get('creator', {}).get('username')}")
    print(f"  タグ: {model_data.get('tags', [])}")
    
    # illustriousタグの確認
    tags_lower = [tag.lower() for tag in model_data.get('tags', [])]
    has_illustrious = 'illustrious' in tags_lower
    print(f"\n  illustriousタグ: {'あり' if has_illustrious else 'なし'}")
    
    # バージョン情報
    print(f"\n  バージョン数: {len(model_data.get('modelVersions', []))}")
    for version in model_data.get('modelVersions', [])[:3]:
        print(f"    - {version.get('name')} (ID: {version.get('id')})")
        if version.get('id') == 1761560:
            print(f"      ↑ これがお探しのバージョンです!")
    
except Exception as e:
    print(f"エラー: {e}")