# CivitAI API 画像取得機能の調査結果

## 概要

CivitAI APIは、モデルに関連する画像の取得と、ユーザーが生成した画像の取得の両方をサポートしています。

## 利用可能なエンドポイント

### 1. モデル関連の画像取得

#### `/api/v1/models` エンドポイント
- モデル一覧取得時に、各モデルバージョンの画像情報が含まれる
- `modelVersions[].images[]` 配列に画像データが格納

#### `/api/v1/models/{modelId}` エンドポイント
- 特定モデルの詳細情報に、全バージョンの画像が含まれる
- より詳細な画像情報を取得可能

### 2. 画像専用エンドポイント

#### `/api/v1/images` エンドポイント
- ユーザーが生成した画像の一覧を取得
- パラメータ:
  - `limit`: 取得数（最大100）
  - `sort`: ソート順（"Most Reactions", "Newest" など）
  - `period`: 期間フィルタ（"Day", "Week", "Month" など）
  - `nsfw`: NSFWフィルタ（"false" でSFWのみ）
  - `cursor`: カーソルベースページネーション

## 画像データ構造

### モデル画像（modelVersions内）
```json
{
  "id": 12221824,
  "url": "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/1c65dc07-2e32-4e76-a0b7-458c450ff1ae/width=1024/12221824.jpeg",
  "nsfwLevel": 1,
  "width": 1024,
  "height": 1536,
  "hash": "UADu}F9a00xb+sIW?uNG0NoL}?D*0gD*-Uxu",
  "type": "image",
  "minor": false,
  "poi": false,
  "hasMeta": true,
  "hasPositivePrompt": true,
  "onSite": false,
  "remixOfId": null
}
```

### ユーザー生成画像（/api/v1/images）
```json
{
  "id": 9173928,
  "url": "https://image.civitai.com/...",
  "hash": "UA8N5},:Ioni~C#laKxaoznNwvx]XmRkVstR",
  "width": 832,
  "height": 1216,
  "nsfwLevel": "None",
  "type": "image",
  "nsfw": false,
  "browsingLevel": 1,
  "createdAt": "2025-04-17T21:28:57.225Z",
  "postId": 1981754,
  "stats": {
    "cryCount": 1532,
    "laughCount": 2381,
    "likeCount": 18997,
    "dislikeCount": 0,
    "heartCount": 7040,
    "commentCount": 49
  },
  "meta": {
    "Size": "832x1216",
    "seed": 1938345220,
    "steps": 45,
    "prompt": "...",
    "sampler": "DPM++ 2M",
    "cfgScale": 5,
    "clipSkip": 2,
    "negativePrompt": "...",
    "civitaiResources": [...]
  },
  "username": "Ajuro",
  "baseModel": "SDXL 1.0",
  "modelVersionIds": [...]
}
```

## 画像URLの構造

画像URLは以下の形式で構成されています：

```
https://image.civitai.com/{hash1}/{hash2}/width={width}/{filename}.jpeg
```

- `hash1`: 固定のハッシュ値（例: xG1nkqKTMzGDvpLrqFT7WA）
- `hash2`: 画像固有のUUID
- `width`: 画像の幅（256, 512, 1024, 2048など）
- `filename`: 画像ID.jpeg

### サイズ変更

URLの`width`パラメータを変更することで、異なるサイズの画像を取得できます：

```python
# オリジナルURL
original_url = "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/1c65dc07-2e32-4e76-a0b7-458c450ff1ae/width=1024/12221824.jpeg"

# サイズ変更
base_url = original_url.split('/width=')[0]
image_id = original_url.split('/')[-1]

# 異なるサイズのURL生成
thumbnail_url = f"{base_url}/width=256/{image_id}"
medium_url = f"{base_url}/width=512/{image_id}"
large_url = f"{base_url}/width=2048/{image_id}"
```

## 画像ダウンロードの実装例

```python
import requests
import os

def download_image(image_url, output_path, width=None):
    """
    CivitAI画像をダウンロード
    
    Args:
        image_url: 画像URL
        output_path: 保存先パス
        width: 画像幅（None=オリジナル）
    """
    # サイズ調整
    if width:
        base_url = image_url.split('/width=')[0]
        filename = image_url.split('/')[-1]
        image_url = f"{base_url}/width={width}/{filename}"
    
    # ダウンロード
    headers = {'User-Agent': 'CivitaiModelDownloader/1.0'}
    response = requests.get(image_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    # 保存
    with open(output_path, 'wb') as f:
        f.write(response.content)
    
    return output_path
```

## 注意事項

1. **画像ID**: モデル画像では、`/api/v1/models`エンドポイントからは画像IDが取得できるが、`/api/v1/models/{modelId}`エンドポイントでは画像IDが含まれない場合がある

2. **NSFW レベル**: 
   - モデル画像: 数値（0-4程度）
   - ユーザー生成画像: 文字列（"None", "Soft", "Mature", "X"）

3. **レート制限**: 画像ダウンロード自体にはAPIキーは不要だが、大量ダウンロード時は適切な間隔を設ける

4. **メタデータ**: ユーザー生成画像には生成パラメータ（プロンプト、シード値など）が含まれるが、モデル画像には含まれない場合が多い

## まとめ

CivitAI APIは画像取得に関して以下の機能を提供：

1. **モデル画像**: モデルAPIレスポンスに含まれる画像URLから直接ダウンロード可能
2. **ユーザー生成画像**: `/api/v1/images`エンドポイントで検索・取得可能
3. **サイズ調整**: URL内のwidthパラメータで任意のサイズに変更可能
4. **メタデータ**: 生成パラメータなどの詳細情報も取得可能

画像ダウンロード自体にAPIキーは不要で、通常のHTTPリクエストで取得できます。