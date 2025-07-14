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
- **主要クエリパ��メータ**:
  - `limit`: 1ページあたりの取得件数（最大: 200, デフォルト: 100）。
  - `page`: ページ番号。ページネーションのために使用する。
  - `query`: 検索キーワード。
  - `tag`: フィルタリング対象のタグ名。
  - `types`: モデルタイプ。複数指定可能 (`Checkpoint`, `LORA`, `TextualInversion`など)。
    - **要件**: Checkpoint検索時は `types=Checkpoint`、LoRA検索時は `types=LORA` を指定する。
  - `sort`: ソート順 (`Highest Rated`, `Most Downloaded`, `Newest`など)。
- **実装方針**:
  - `ModelExplorer`は、このエンドポイントをページネーションしながら呼び出し、全対象モデルの情報を収集する。
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
    "totalPages": 10
  }
}
```

- **実装方針**:
  - `ModelExplorer`は、`items`配列をループ処理する。
  - 各モデルの`type`と`tags`を基にフィルタリングを行う。
  - ダウンロード対象のモデルバージョンを`modelVersions`配列から選択する（通常は最新版である最初の要素）。
  - 選択したバージョンの`files`配列から、`format: "SafeTensors"`のファイルを探し、その`downloadUrl`と`name`を`DownloadTask`に格納する。
  - `metadata`フィールドの`totalPages`を基に、ページネーションの終了条件を判���する。

## 5. レート制限

- **仕様**: 明確な回数や時間に関する規定はドキュメントにない。
- **エラー**: 制限を超えると、HTTPステータスコード `429 Too Many Requests` が返される。
- **実装方針**:
  - 計画書通り、API呼び出し間に固定のウェイト（例: 2秒）を入れる`RateLimiter`を実装し、デフォルトで有効にする。
  - `429`エラーを検知した場合、指数関数的に待機時間を増やすバックオフ機構を`CivitaiClient`に実装する。

## 6. まとめ

上記の仕様に基づき、各コンポーネントの実装を進める。特に、ページネーション処理、クライアントサイドでのタグフィルタリング、ダウンロード時のリダイレクトとファイル名取得が実装のキーポイントとなる。
