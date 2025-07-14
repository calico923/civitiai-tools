# Civitai API 技術仕様調査レポート

## 1. 概要
本ドキュメントは、「Civitai Model Downloader」開発にあたり、Civitai APIの公開仕様を調査し、実装に必要な技術要素をまとめたものである。

## 2. 認証

APIリクエストにはAPIキーによる認証が必要。

- **方法**: HTTPリクエストの `Authorization` ヘッダーにBearerトークンとしてAPIキーを含める。
  ```http
  Authorization: Bearer <YOUR_API_KEY>
  ```
- **代替案**: クエリパラメータ `?token=<YOUR_API_KEY>` も利用可能だが、ヘッダー方式を推奨。
- **実装方針**: `CivitaiClient`の初期化時にAPIキーを受け取り、`requests.Session`オブジェクトのデフォルトヘッダーに設定する。

## 3. 主要エンドポイント

### 3.1 モデル検索: `GET /api/v1/models`

モデルの検索とフィルタリングには、このエンドポイントを使用する。

- **URL**: `https://civitai.com/api/v1/models`
- **主要クエリパラメータ**:
  - `limit`: 1ページあたりの取得件数（最大: 200, デフォルト: 100）。
  - `cursor`: **カーソルベースページネーション用のカーソル値**（重要：下記参照）。
  - `page`: ページ番号（**非推奨**: オフセットベースのため、データの抜け漏れが発生する）。
  - `query`: 検索キーワード。
  - `tag`: フィルタリング対象のタグ名。
  - `types`: モデルタイプ。複数指定可能 (`Checkpoint`, `LORA`, `TextualInversion`など)。
    - **要件**: Checkpoint検索時は `types=Checkpoint`、LoRA検索時は `types=LORA` を指定する。
  - `sort`: ソート順 (`Highest Rated`, `Most Downloaded`, `Newest`など)。
  - `baseModels`: ベースモデルフィルター（`Pony`, `SDXL 1.0` など）。

#### カーソルベースページネーション（重要）

**問題点**: 従来の`page`パラメータを使用したオフセットベースのページネーションは、新しいモデルが追加された際にデータの重複や欠落を引き起こす。

**解決策**: CivitAI APIは`cursor`パラメータを使用したカーソルベースページネーションをサポート。

- **仕組み**:
  1. 初回リクエスト: `cursor`パラメータなしでリクエスト
  2. レスポンスの`metadata.nextCursor`フィールドに次ページのカーソル値が含まれる
  3. 次回リクエスト: `cursor=<nextCursor値>`を指定してリクエスト
  4. `nextCursor`が`null`になるまで繰り返す

- **実装例**:
  ```python
  def fetch_all_models_with_cursor(self, **params):
      all_models = []
      cursor = None
      
      while True:
          if cursor:
              params['cursor'] = cursor
          
          response = self.request('GET', '/models', params=params)
          data = response.json()
          
          all_models.extend(data['items'])
          
          # 次のカーソルを取得
          cursor = data.get('metadata', {}).get('nextCursor')
          if not cursor:
              break
              
      return all_models
  ```

- **実装方針**:
  - `ModelExplorer`は、カーソルベースページネーションを使用して全データを確実に取得する。
  - 要件定義書にあるLoRAのタグ条件（`pony`等）は、APIから取得した各モデルの`tags`フィールドをクライアントサイドでフィルタリングして実現する。

### 3.2 モデルバージョンごとのダウンロード

- **URL形式**: `https://civitai.com/api/download/models/<modelVersionId>`
- **挙動**:
  1. 上記URLにアクセスすると、実際のファイ���が保存されている署名付きURL（S3など）へリダイレクトされる。
  2. `Content-Disposition` ヘッダーに元のファイル名が含まれているため、これを解析して保存ファイル名を決定する。
- **認証**:
  - モデルによってはダウンロードにも認証が必要な場合がある。その際は、ダウンロードURLに `?token=<YOUR_API_KEY>` を付与する必要がある。
- **実装方針**:
  - `ModelDownloader`は、`requests.get`を実行する際に `allow_redirects=True` を設定する。
  - レスポンスの `response.headers['Content-Disposition']` をパースしてファイル名を取得する。
  - `stream=True` を使用し、大容量ファイルをチャンク単位でダウンロードしてプログレスバーを更新する。

## 4. データ構造の要点

`GET /api/v1/models` のレスポンスは以下の構造を持つ。

```json
{
  "items": [
    {
      "id": 123,
      "name": "Model Name",
      "type": "Checkpoint", // "LORA" など
      "tags": ["tag1", "tag2"],
      "modelVersions": [
        {
          "id": 456,
          "name": "v1.0",
          "downloadUrl": "https://civitai.com/api/download/models/456",
          "baseModel": "SDXL 1.0", // ベースモデル情報
          "files": [
            {
              "name": "model.safetensors",
              "id": 789,
              "sizeKB": 2000000,
              "type": "Model", // "Pruned Model" など
              "format": "SafeTensors" // "PickleTensor" など
            }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "currentPage": 1,
    "pageSize": 10,
    "totalItems": 100,
    "totalPages": 10,
    "nextCursor": "eyJpZCI6MTIzNDU2fQ==" // カーソルベースページネーション用
  }
}
```

- **実装方針**:
  - `ModelExplorer`は、`items`配列をループ処理する。
  - 各モデルの`type`と`tags`を基にフィルタリングを行う。
  - ダウンロード対象のモデルバージョンを`modelVersions`配列から選択する（通常は最新版である最初の要素）。
  - 選択したバージョンの`files`配列から、`format: "SafeTensors"`のファイルを探し、その`downloadUrl`と`name`を`DownloadTask`に格納する。
  - `metadata`フィールドの`totalPages`を基に、ページネーションの終了条件を判���する。

## 5. 実装時の発見事項

### 5.1 デュアル検索方式の必要性

実装過程で、単一の検索方式だけでは一部のモデルを見逃すことが判明：

- **直接タグ検索**: `tag=style`など、タグで直接検索する方式
- **ベースモデル経由検索**: `baseModels=Pony`でベースモデルを指定し、その後クライアントサイドでタグフィルタリングを行う方式

**推奨アプローチ**: 両方の検索方式を組み合わせ、結果をmodel_idベースで重複除去する。

### 5.2 検索条件の最適化

効率的な検索のために以下の条件を使用：

- **LoRA検索**: 
  - `types=LORA`
  - `tag=style`（styleタグ付きLoRAの場合）
  - `sort=Highest Rated`
  - `limit=200`（最大値）

- **Checkpoint検索**:
  - `types=Checkpoint`
  - `baseModels=Pony`（ベースモデル指定）
  - `sort=Highest Rated`
  - `limit=200`

### 5.3 パフォーマンスの最適化

- **カーソルベースページネーション**: データの整合性を保証
- **重複除去**: `model_id`ベースで効率的な重複除去
- **レート制限**: API呼び出し間に適切な間隔（1-2秒）を設ける

## 6. レート制限

- **仕様**: 明確な回数や時間に関する規定はドキュメントにない。
- **エラー**: 制限を超えると、HTTPステータスコード `429 Too Many Requests` が返される。
- **実装方針**:
  - 計画書通り、API呼び出し間に固定のウェイト（例: 2秒）を入れる`RateLimiter`を実装し、デフォルトで有効にする。
  - `429`エラーを検知した場合、指数関数的に待機時間を増やすバックオフ機構を`CivitaiClient`に実装する。

## 7. まとめ

上記の仕様に基づき、各コンポーネントの実装を進める。特に、**カーソルベースページネーション**、**デュアル検索方式**、**クライアントサイドでのタグフィルタリング**、**ダウンロード時のリダイレクトとファイル名取得**が実装のキーポイントとなる。

### 実装済み成果物

- **カーソルベースページネーション**: `src/api/client.py`で実装済み
- **デュアル検索方式**: `scripts/collection/`配下のスクリプトで実装
- **URL収集器**: `src/core/url_collector.py`でURL収集とエクスポート機能を実装
- **成果**: 合計735個のモデルURL（Checkpoint: 450個、LoRA: 285個）を収集
