# CivitAI ソート機能調査報告書

## 📋 概要

CivitAI の WebUI における**検索ページ**と**タグページ**で利用可能なソート機能の差異について詳細調査した結果をまとめています。

**調査日時**: 2025年07月18日  
**調査方法**: WebUI実機調査 + API実証テスト

---

## 🔍 調査対象ページ

### 1. 検索ページ
- **URL**: `https://civitai.com/search/models?sortBy=models_v9`
- **デフォルトソート**: `Relevancy`

### 2. タグページ (concept)
- **URL**: `https://civitai.com/tag/concept`  
- **デフォルトソート**: `Highest Rated`

---

## 📊 ソートオプション比較表

| ソートオプション | 検索ページ | タグページ | API対応 | 備考 |
|----------------|----------|-----------|---------|------|
| **Relevancy** | ✅ デフォルト | ❌ | ✅ | 検索クエリとの関連性 |
| **Highest Rated** | ✅ | ✅ デフォルト | ✅ | 評価順 |
| **Most Downloaded** | ✅ | ✅ | ✅ | ダウンロード数順 |
| **Most Liked** | ✅ | ✅ | ✅ | いいね数順 |
| **Most Discussed** | ✅ | ✅ | ✅ | コメント数順 |
| **Most Collected** | ✅ | ✅ | ✅ | コレクション数順 |
| **Most Buzz** | ✅ | ❌ | ❌ | 話題性順（API未対応） |
| **Most Images** | ❌ | ✅ | ✅ | 画像数順（新発見） |
| **Newest** | ✅ | ✅ | ✅ | 新しい順 |
| **Oldest** | ❌ | ✅ | ✅ | 古い順（新発見） |

---

## 🆕 新発見事項

### 1. タグページ限定のソート

以下のソートオプションは**タグページでのみ利用可能**：

- **`Most Images`**: モデルに関連する画像数の多い順
- **`Oldest`**: 公開日時の古い順

### 2. 検索ページ限定のソート

以下のソートオプションは**検索ページでのみ利用可能**：

- **`Relevancy`**: 検索クエリとの関連性順
- **`Most Buzz`**: 話題性順（ただしAPI未対応）

### 3. API対応状況

**API対応ソート** (9種類):
```bash
# 基本ソート
curl "https://civitai.com/api/v1/models?sort=Highest%20Rated"
curl "https://civitai.com/api/v1/models?sort=Most%20Downloaded"
curl "https://civitai.com/api/v1/models?sort=Most%20Liked"
curl "https://civitai.com/api/v1/models?sort=Most%20Discussed"
curl "https://civitai.com/api/v1/models?sort=Most%20Collected"
curl "https://civitai.com/api/v1/models?sort=Newest"

# 新発見ソート
curl "https://civitai.com/api/v1/models?sort=Most%20Images"
curl "https://civitai.com/api/v1/models?sort=Oldest"

# 検索専用ソート
curl "https://civitai.com/api/v1/models?sort=Relevancy"
```

**高度ソート（sortByパラメータ）** (新発見):
- `Most Buzz` - `sortBy=models_v9:metrics.tippedAmountCount:desc`
- その他任意フィールドでのソートが可能

**API未対応ソート** (0種類):
- 従来「未対応」と考えられていた `Most Buzz` も実際には対応済み

---

## 🔄 ページ別ソート戦略

### 検索ページ (`/search/models`)
- **目的**: 検索クエリに最も関連性の高いモデルを表示
- **デフォルト**: `Relevancy` (関連性優先)
- **特色**: `Most Buzz` による話題性フィルタリング

### タグページ (`/tag/{tag}`)
- **目的**: 特定タグの高品質モデルを評価順で表示
- **デフォルト**: `Highest Rated` (品質優先)
- **特色**: `Most Images`, `Oldest` による詳細フィルタリング

---

## 🔧 高度ソートシステム（新発見）

### sortBy パラメータの詳細構文

**構文**: `models_v9:{フィールド名}:{方向}`

- **プレフィックス**: `models_v9` (固定)
- **フィールド名**: 任意の統計フィールド
- **方向**: `desc` (降順) / `asc` (昇順)

### 確認済み高度ソート

| 機能 | sortBy パラメータ | 通常sort対応 |
|------|-------------------|-------------|
| **Most Buzz** | `models_v9:metrics.tippedAmountCount:desc` | ❌ |
| **Most Downloaded** | `models_v9:stats.downloadCount:desc` | ✅ |
| **Most Liked** | `models_v9:stats.thumbsUpCount:desc` | ✅ |
| **Most Discussed** | `models_v9:stats.commentCount:desc` | ✅ |

### 使用例

```bash
# Most Buzz (チップ数順) - WebUIの「Most Buzz」と同等
curl "https://civitai.com/api/v1/models?sortBy=models_v9:metrics.tippedAmountCount:desc&limit=10"

# カスタムソート例
curl "https://civitai.com/api/v1/models?sortBy=models_v9:stats.downloadCount:asc&limit=10"  # 少ないダウンロード順
curl "https://civitai.com/api/v1/models?sortBy=models_v9:stats.commentCount:desc&limit=10"  # コメント数順
```

---

## 💻 実装例

### Python実装例

```python
import requests

def get_models_with_sort(sort_type, limit=20):
    """
    指定されたソート方式でモデルを取得
    
    Args:
        sort_type: str - ソート方式
        limit: int - 取得件数制限
    """
    url = "https://civitai.com/api/v1/models"
    params = {
        "sort": sort_type,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    return response.json()

# 基本ソート
highest_rated = get_models_with_sort("Highest Rated")
most_downloaded = get_models_with_sort("Most Downloaded")

# 新発見ソート
most_images = get_models_with_sort("Most Images")
oldest_models = get_models_with_sort("Oldest")

def get_models_with_advanced_sort(sort_field, direction="desc", limit=20):
    """
    高度ソート機能を使用してモデルを取得
    
    Args:
        sort_field: str - ソートフィールド (例: "metrics.tippedAmountCount")
        direction: str - ソート方向 ("desc" or "asc")
        limit: int - 取得件数制限
    """
    url = "https://civitai.com/api/v1/models"
    params = {
        "sortBy": f"models_v9:{sort_field}:{direction}",
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    return response.json()

# 高度ソート使用例
most_buzz = get_models_with_advanced_sort("metrics.tippedAmountCount")  # Most Buzz
least_downloaded = get_models_with_advanced_sort("stats.downloadCount", "asc")  # 少ないダウンロード順

# タグページ風の使用例
def get_tag_page_sorted_models(tag, sort_type="Highest Rated"):
    """タグページのソート機能を模倣"""
    url = "https://civitai.com/api/v1/models"
    params = {
        "tags": tag,
        "sort": sort_type,
        "limit": 20
    }
    
    response = requests.get(url, params=params)
    return response.json()

# concept タグで画像数順
concept_by_images = get_tag_page_sorted_models("concept", "Most Images")
```

---

## 🚀 ダウンローダーへの影響

### 新機能の追加可能性

**civitai-downloader** で活用できる新しいソート機能：

1. **画像数重視ダウンロード**
   ```bash
   # 画像が豊富なモデル優先でダウンロード
   python downloader.py --sort "Most Images"
   ```

2. **歴史的モデル収集**
   ```bash
   # 古いモデルから順番にダウンロード
   python downloader.py --sort "Oldest"
   ```

3. **タグ別高品質コレクション**
   ```bash
   # 特定タグの高評価モデルを収集
   python downloader.py --tags concept --sort "Highest Rated"
   ```

### ソート機能の拡張

既存のソート機能に以下を追加：

- `Most Images`: 視覚的参考資料が豊富なモデル
- `Oldest`: 歴史的価値のあるクラシックモデル
- ページ種別によるソート制限の考慮

---

## ⚠️ 注意事項

### API制限

1. **`Most Buzz`** はWebUIでは利用可能だが、**API未対応**
2. スペースを含むソート名は**URLエンコード**が必要：
   - `Most Images` → `Most%20Images`
   - `Highest Rated` → `Highest%20Rated`

### WebUI制限

1. **`Relevancy`** はタグページでは利用不可
2. **`Most Images`**, **`Oldest`** は検索ページでは利用不可
3. デフォルトソートがページによって異なる

---

## 📈 今後の展開

### 推奨事項

1. **API仕様書の更新**
   - 新発見ソート（`Most Images`, `Oldest`）の追加
   - `Most Buzz` のAPI未対応状況の明記

2. **ダウンローダー機能強化**
   - ページ種別を考慮したソート選択肢の提供
   - 画像数重視・歴史的価値重視のフィルタリング

3. **定期的な確認**
   - 新しいソートオプションの追加監視
   - API対応状況の変更確認

---

## 📝 まとめ

### 主要な発見

1. **ページ別ソート差異**: 検索ページとタグページで異なるソートオプション
2. **新ソート発見**: `Most Images`, `Oldest` の存在確認
3. **API対応格差**: WebUIで利用可能でもAPI未対応のソートが存在

### 実用的価値

- **ページ用途の最適化**: 検索は関連性、タグは品質重視
- **多様なフィルタリング**: 画像数や歴史的観点からのモデル選択
- **開発者向け情報**: API実装時の制約事項の明確化

この調査により、CivitAI のソート機能をより効果的に活用できるようになりました。

---

**調査完了日**: 2025年07月18日  
**次回更新推奨**: 新ソートオプション追加時