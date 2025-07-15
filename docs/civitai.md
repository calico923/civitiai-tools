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
  - `types`: モデルタイプ。複数指定可能 (`Checkpoint`, `LORA`, `LoCon`, `TextualInversion`など)。
    - **要件**: 
      - Checkpoint検索時は `types=Checkpoint`
      - LoRA検索時は `types=LORA`
      - LyCORIS検索時は `types=LoCon`（内部的にはLoConとして処理される）
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
  - `tag=style`（styleタグ付きLoRAの場合）または `tag=style,pony,illustrious`（複数タグはOR演算）
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

## 7. CivitAI API の制限事項と対策

### 7.1 ページネーション制限（最も深刻）

**問題**: オフセットベース(`page`パラメータ)のページネーションは、検索中に新しいモデルが追加されるとデータの重複・欠落を引き起こす。

**症状**:
- 同じモデルが複数ページで重複して表示される
- 一部のモデルが検索結果から漏れる
- 総件数と実際の取得件数に差が生じる

**対策**: カーソルベースページネーション(`cursor`パラメータ)を使用（実装済み）

### 7.2 検索機能の制限

**問題**: 単一の検索方式では取得漏れが発生する。

**具体的な制限**:
- **タグ検索の不完全性**: `tag=style`で検索しても、実際にstyleタグを持つ全モデルが取得されない
- **AND検索未対応**: `tag=style,pony`は OR演算のみ（styleタグ**または**ponyタグ）
- **大文字小文字の区別**: タグマッチングで予期しない結果
- **検索方式の違い**: `tag`と`query`パラメータで異なる結果セット

**対策**: デュアル検索方式の実装
1. 直接タグ検索: `tag=style`
2. ベースモデル経由検索: `baseModels=Pony` → クライアントサイドでタグフィルタリング
3. 結果をmodel_idベースで重複除去

### 7.3 データ整合性の問題

**問題**: APIが報告するメタデータと実際のデータに不一致が発生する。

**具体的な症状**:
- **モデル数不一致**: Webインターフェースと API結果で異なる件数
- **ソート順による総数変動**: 同じ検索条件でもソート順で`totalItems`が変わる
- **メタデータ不整合**: `metadata.totalItems`と実際の取得数に差分

**証拠**: `scripts/debug/debug_api_pagination.py`で実証

**対策**: 
- メタデータに依存しない実装
- 実際の取得データをベースとした処理
- カーソルベースページネーションによる完全性保証

### 7.4 レート制限の不透明性

**問題**: 公式な制限値が明確でないため、適切なレート調整が困難。

**症状**:
- 頻繁な`429 Too Many Requests`エラー
- 制限値が動的に変わる可能性
- 指数バックオフの最適値が不明

**対策**: 
- 保守的なレート制限（0.5回/秒、2秒間隔）
- 固定タイムアウト（30秒）
- 将来的な指数バックオフ実装の検討

### 7.5 応答サイズ・パフォーマンス制限

**制限値**:
- 最大ページサイズ: 200件
- デフォルトページサイズ: 100件
- レスポンスタイムアウト: 30秒

**問題**:
- バルク操作不可（1件ずつ処理）
- 並列処理制限（レート制限により実質シーケンシャル）
- 大量データ取得時の長時間実行

**対策**:
- 最大ページサイズ（200件）の使用
- 効率的なカーソルベースページネーション
- 適切なタイムアウト設定

### 7.6 認証・アクセス制限

**制限**:
- 全リクエストにAPIキー必須
- プライベートモデルのダウンロード時追加認証
- APIキーのクォータ・制限値不明

**対策**:
- Bearerトークン認証の実装
- ダウンロード時の条件付きトークン付与
- APIキー管理の適切な実装

### 7.7 ベースモデル分類の問題

**問題**: ベースモデルの分類が不整合で、フィルタリングが困難。

**具体的な問題**:
- `base model`タグと`baseModel`フィールドの混同
- Pony、Illustrious、NoobAIの不正確な分類
- 同じモデルが複数のベースモデルに分類される

**対策**:
- 複数の分類方法の組み合わせ
- クライアントサイドでの正規化処理
- 実際のデータに基づく分類ロジック

### 7.8 エラーハンドリングの制限

**問題**: 構造化されたエラー情報が不足。

**制限**:
- 汎用的な`RequestException`のみ
- 詳細なエラー情報なし
- リトライ戦略のガイダンス不足

**対策**:
- 包括的な例外処理
- ログベースのエラー追跡
- 保守的なリトライ戦略

## 8. 実装された回避策の総括

### 8.1 主要な回避策

1. **カーソルベースページネーション**: データ整合性保証
2. **デュアル検索方式**: 取得漏れの最小化
3. **クライアントサイド重複除去**: model_idベースでの正確な重複処理
4. **保守的レート制限**: 安定した API アクセス
5. **柔軟な検索戦略**: 複数のアプローチで完全性確保

### 8.2 実証された効果

- **データ整合性**: 735個のモデルURL収集に成功
- **重複除去**: 効率的な重複除去により正確なデータセット
- **安定性**: レート制限により安定したAPI アクセス
- **完全性**: デュアル検索により高い網羅率

### 8.3 継続的な改善点

- 指数バックオフの実装
- 並列処理の最適化
- エラーハンドリングの強化
- パフォーマンスモニタリング

## 9. モデルタイプ仕様

### 9.1 API内部でのモデルタイプ表記

CivitAI APIでは、一般的な呼称と内部的なAPI表記が異なるモデルタイプが存在する：

- **Checkpoint**: `types=Checkpoint`（表記一致）
- **LoRA**: `types=LORA`（表記一致）
- **LyCORIS**: `types=LoCon`（⚠️ 注意：APIでは "LoCon" として扱われる）

### 9.2 実装時の注意点

#### 型名正規化の必要性
```python
def normalize_type(type_str):
    if type_str.lower() == "checkpoint":
        return "Checkpoint"
    elif type_str.lower() == "lora":
        return "LORA"
    elif type_str.lower() in ["lycoris", "locon"]:
        return "LoCon"  # LyCORISはAPIでLoConとして処理
    else:
        return type_str.title()
```

#### コマンドライン引数での対応
- ユーザー入力: `--type lycoris`
- API送信時: `types=LoCon`
- 出力ファイル名: `illustrious_lycoris_*`（ユーザー向けはLyCORIS表記を維持）

### 9.3 検索結果の特徴

- **Checkpoint**: 大容量モデル（平均2-6GB）、ベースモデルとして機能
- **LORA**: 軽量アダプター（平均10-200MB）、最も豊富なモデル数
- **LoCon/LyCORIS**: 中間的な容量とモデル数、スタイル特化が多い

## 10. まとめ

CivitAI APIには多くの制限があるが、適切な回避策により実用的なデータ収集が可能。特に、**カーソルベースページネーション**、**デュアル検索方式**、**クライアントサイドでのタグフィルタリング**、**ダウンロード時のリダイレクトとファイル名取得**が実装のキーポイントとなる。

### 実装済み成果物

- **カーソルベースページネーション**: `src/api/client.py`で実装済み
- **デュアル検索方式**: `scripts/collection/`配下のスクリプトで実装
- **URL収集器**: `src/core/url_collector.py`でURL収集とエクスポート機能を実装
- **成果**: 合計735個のモデルURL（Checkpoint: 450個、LoRA: 285個）を収集
- **デバッグツール**: `scripts/debug/`配下で制限の調査・実証
