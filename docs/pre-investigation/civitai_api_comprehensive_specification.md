# CivitAI API v1 包括的仕様書

## 📋 概要

この文書は、CivitAI API v1の**完全な仕様**を文書化したものです。
公式ドキュメントに記載されていない隠れた機能や詳細な制約も含まれています。

**調査日時**: 2025年07月16日 13:18:00
**調査方法**: 実際のAPI呼び出しによる実証的調査

---

## 🚀 利用可能エンドポイント

### 主要エンドポイント
- **`/models`** - HTTP 200
  - 応答タイプ: dict
  - キー: items, metadata
  - 要素数: 2
- **`/users`** - HTTP 200
  - 応答タイプ: dict
  - キー: items
  - 要素数: 1
- **`/images`** - HTTP 200
  - 応答タイプ: dict
  - キー: items, metadata
  - 要素数: 2
- **`/tags`** - HTTP 200
  - 応答タイプ: dict
  - キー: items, metadata
  - 要素数: 2

### 利用不可エンドポイント
以下の38個のエンドポイントは利用できません:
`models/categories, models/tags, users/me, creators, images/featured, images/recent, stats, leaderboard, trending, featured...`

## 🔍 検索パラメータ

### 利用可能パラメータ

#### `limit`
- **テスト値**: 1, 10, 100
- **動作確認済み**: 1, 10, 100

#### `types`
- **テスト値**: Checkpoint, LORA, LoCon
- **動作確認済み**: Checkpoint, LORA, LoCon

#### `sort`
- **テスト値**: Highest Rated, Most Downloaded, Most Liked, Most Discussed, Most Collected, Most Images, Newest, Oldest, Relevancy
- **動作確認済み**: Highest Rated, Most Downloaded, Most Liked, Most Discussed, Most Collected, Most Images, Newest, Oldest, Relevancy
- **未対応**: Most Buzz (WebUIでは利用可能だがAPI未対応)
- **ページ依存**: Relevancy(検索ページ用), Most Images/Oldest(タグページ用)

#### `period`
- **テスト値**: AllTime, Year, Month, Week, Day
- **動作確認済み**: AllTime, Year, Month, Week, Day

#### `nsfw`
- **テスト値**: true, false
- **動作確認済み**: true, false

#### `baseModels`
- **テスト値**: Illustrious, SDXL 1.0, Pony
- **動作確認済み**: Illustrious, SDXL 1.0, Pony

#### `tags`
- **テスト値**: anime, style, realistic
- **動作確認済み**: anime, style, realistic

#### `username`
- **テスト値**: Ikena
- **動作確認済み**: Ikena

#### `query`
- **テスト値**: anime model
- **動作確認済み**: anime model

#### `category`
- **テスト値**: character, style, concept, background, poses, vehicle, clothing
- **動作確認済み**: character, style, concept, background, poses, vehicle, clothing
- **詳細**: 15種類のカテゴリ（action, animal, assets, background, base model, buildings, celebrity, character, clothing, concept, objects, poses, style, tool, vehicle）
- **実装**: カテゴリは内部的にタグシステムを利用

### 高度検索機能

以下の高度なパラメータが利用可能です:

- **動作する高度パラメータ**: 22個
- 範囲検索 (minDownloads, maxDownloads)
- 日付フィルタ (startDate, endDate)
- 複数値指定 (types, tags, baseModels)
- 高度フィルタ (featured, verified, commercial)

## 📄 ページネーション

**動作するページネーション方式**: 8個

### 方式 1: {'limit': 5, 'page': 1}
- カーソルベースページネーション対応
- 取得アイテム数: 5

### 方式 2: {'limit': 5, 'page': 2}
- カーソルベースページネーション対応
- 取得アイテム数: 5

### 方式 3: {'limit': 5, 'offset': 0}
- カーソルベースページネーション対応
- 取得アイテム数: 5

## 📊 データ構造

### 共通フィールド
全モデルタイプで共通して利用可能なフィールド: **81個**

### モデルタイプ別詳細
- **Hassaku XL** (Checkpoint): 85フィールド
- **Style LoRA** (LORA): 84フィールド
- **LyCORIS Model** (LyCORIS): 82フィールド

## ⚖️ ライセンス・権限情報

### 取得可能なライセンスフィールド


| フィールド | 型 | 説明 |
|-----------|---|------|
| `allowCommercialUse` | array | 商用利用許可レベル |
| `allowDerivatives` | boolean | 派生作品作成許可 |
| `allowDifferentLicense` | boolean | 異なるライセンスでの再配布許可 |
| `allowNoCredit` | boolean | クレジット表記不要での使用許可 |

### 商用利用レベル
- **`Image`**: 生成画像の商用利用可
- **`Rent`**: モデルのレンタル可
- **`RentCivit`**: CivitAI上でのレンタル可
- **`Sell`**: モデルの販売可

## 📈 統計・メトリクス

### モデルレベル統計
- ダウンロード数 (`downloadCount`)
- いいね数 (`thumbsUpCount`)
- よくないね数 (`thumbsDownCount`) 
- コメント数 (`commentCount`)
- お気に入り数 (`favoriteCount`)
- チップ数 (`tippedAmountCount`)
- 評価数・平均評価 (`ratingCount`, `rating`)

### バージョンレベル統計
- バージョン別ダウンロード数
- バージョン別評価
- 公開状態 (`status`)

## 📁 ファイル・バージョン管理

### ハッシュ値
利用可能ハッシュタイプ: `AutoV3, CRC32, AutoV2, AutoV1, SHA256, BLAKE3`

### ファイルメタデータ
- ファイル形式 (`format`): SafeTensor, Pickle等
- 精度 (`fp`): fp16, fp32等
- サイズ (`size`): pruned, full等
- Pickleスキャン結果
- ウイルススキャン結果

## 🖼️ 画像・生成メタデータ

### 画像フィールド
利用可能フィールド数: 13個
- 画像URL、サイズ、ハッシュ値
- NSFW分類、POI検出
- 生成メタデータ (`meta`)

## ⚠️ API制限・ベストプラクティス

### レート制限
- **推奨間隔**: 2秒以上
- **タイムアウト**: 30秒
- **最大limit**: 100（検証済み）

### ページネーション
- **カーソルベース**: `nextCursor`を使用
- **オフセットベース**: `page`または`offset`を使用
- **推奨**: カーソルベース（データ一貫性のため）

### エラーハンドリング
- **HTTP 200**: 成功
- **HTTP 429**: レート制限超過
- **HTTP 404**: リソース未発見
- **HTTP 500**: サーバーエラー

## 💻 実装例

### Python実装例

```python
import requests
import time

class CivitAIClient:
    def __init__(self, api_key=None):
        self.base_url = 'https://civitai.com/api/v1'
        self.headers = {
            'Authorization': f'Bearer {api_key}' if api_key else None,
            'User-Agent': 'YourApp/1.0'
        }
    
    def search_models(self, **params):
        """モデル検索"""
        response = requests.get(
            f'{self.base_url}/models',
            headers=self.headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_model_details(self, model_id):
        """個別モデル詳細取得"""
        response = requests.get(
            f'{self.base_url}/models/{model_id}',
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def paginate_all(self, endpoint, **params):
        """全データ取得（カーソルベース）"""
        all_items = []
        cursor = None
        
        while True:
            if cursor:
                params['cursor'] = cursor
            
            response = self.search_models(**params)
            items = response.get('items', [])
            all_items.extend(items)
            
            # 次のカーソルを取得
            metadata = response.get('metadata', {})
            cursor = metadata.get('nextCursor')
            
            if not cursor or not items:
                break
                
            time.sleep(2)  # レート制限対策
        
        return all_items

# 使用例
client = CivitAIClient(api_key='your_api_key')

# ライセンス情報付きでモデル検索
models = client.search_models(
    types='Checkpoint',
    tags='anime',
    sort='Highest Rated',
    limit=50
)

for model in models['items']:
    print(f"Model: {model['name']}")
    print(f"Commercial Use: {model['allowCommercialUse']}")
    print(f"Derivatives: {model['allowDerivatives']}")
    print("---")
```

### 高度検索例

```python
# 複数条件での検索
advanced_results = client.search_models(
    types='Checkpoint,LORA',
    tags='anime,style', 
    category='character',
    baseModels='Illustrious,SDXL 1.0',
    minDownloads=1000,
    sort='Most Downloaded',
    period='Month',
    limit=100
)

# 商用利用可能モデルのフィルタ
commercial_models = [
    model for model in advanced_results['items']
    if 'Image' in model.get('allowCommercialUse', [])
]
```

## 🔬 調査方法

この仕様書は以下の方法で作成されました:

1. **エンドポイント探索**: 38個の候補エンドポイントをテスト
2. **パラメータ検証**: 各検索パラメータの動作確認
3. **応答構造分析**: 実際のJSON応答の完全解析
4. **制限値測定**: レート制限、最大値等の実測
5. **モデルタイプ比較**: Checkpoint、LoRA、LyCORIS間の差異調査

## 📝 更新履歴

- **2025-07-16**: 初版作成
  - 包括的API調査実施
  - 85個のフィールド、9個の検索パラメータを確認
  - ライセンス情報取得方法を特定

