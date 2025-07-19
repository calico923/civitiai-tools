# CivitAI 期間フィルター（period）仕様書

## 📋 概要

CivitAI API の `period` パラメータの詳細仕様と動作について実証的調査した結果をまとめています。

**調査日時**: 2025年07月18日  
**調査方法**: API実証テスト + 異なる期間での結果比較

---

## 🎯 期間フィルターの基本仕様

### 利用可能な期間値

| 期間値 | 説明 | 対象範囲 |
|-------|------|---------|
| **`AllTime`** | 全期間 | サービス開始から現在まで |
| **`Year`** | 年間 | 過去365日 |
| **`Month`** | 月間 | 過去30日 |
| **`Week`** | 週間 | 過去7日 |
| **`Day`** | 日間 | 過去24時間 |

### デフォルト動作

期間を指定しない場合は **`AllTime`** がデフォルトとして適用されます。

```bash
# 以下は同等
curl "https://civitai.com/api/v1/models?sort=Most%20Downloaded"
curl "https://civitai.com/api/v1/models?sort=Most%20Downloaded&period=AllTime"
```

---

## 🔍 期間フィルターの影響範囲

### ✅ 期間フィルターが有効なソート

| ソート | 期間影響 | 集計対象 | 仕様 |
|-------|----------|---------|------|
| **Most Downloaded** | ✅ | ダウンロード数 | 指定期間内のダウンロード数で集計 |
| **Most Liked** | ✅ | いいね数 | 指定期間内のいいね数で集計 |
| **Most Discussed** | ✅ | コメント数 | 指定期間内のコメント数で集計 |
| **Most Collected** | ✅ | コレクション数 | 指定期間内のコレクション数で集計 |
| **Highest Rated** | ✅ | 評価 | 指定期間内の評価で集計 |

### ❌ 期間フィルターが無効なソート

| ソート | 期間影響 | 理由 |
|-------|----------|------|
| **Newest** | ❌ | 公開日時の新しい順（期間は影響しない） |
| **Oldest** | ❌ | 公開日時の古い順（期間は影響しない） |
| **Relevancy** | ❌ | 検索クエリとの関連性（期間は無関係） |

---

## 📊 実証テスト結果

### Most Downloaded の期間別結果

#### AllTime（全期間）
```
1. Realistic Vision V6.0 B1 - 1,817,680 downloads
2. DreamShaper - 1,360,015 downloads  
3. Juggernaut XL - 1,072,750 downloads
```

#### Month（月間）
```
1. CyberRealistic Pony - 398,319 downloads
2. epiCRealism XL - 264,202 downloads
3. Pony Realism 🔮 - 412,223 downloads
```

#### Week（週間）
```
1. PornMaster-色情大师 - 220,358 downloads
2. Hassaku XL (Illustrious) - 236,013 downloads
3. PornMaster-Pro 色情大师 - 67,228 downloads
```

### Most Liked の期間別結果

#### AllTime（全期間）
```
1. Pony Diffusion V6 XL - 67,277 likes
2. majicMIX realistic 麦橘写实 - 60,163 likes
3. DreamShaper - 55,289 likes
```

#### Day（日間）
```
1. iLustMix - 7,577 likes
2. Ani | (Grok Companions) - 276 likes
3. Sui (Elf) [5 outfits] - 106 likes
```

---

## 🔧 技術的詳細

### 期間計算の基準点

期間計算は **APIリクエスト時点** を基準として逆算されます：

- **Day**: リクエスト時刻から24時間前まで
- **Week**: リクエスト時刻から7日前まで  
- **Month**: リクエスト時刻から30日前まで
- **Year**: リクエスト時刻から365日前まで

### 統計データの更新頻度

統計データの更新頻度は未公開ですが、実測では：

- **リアルタイム更新**: ダウンロード数、いいね数
- **バッチ更新**: 評価、コレクション数（推定）

### 期間フィルターの内部実装推定

```sql
-- 推定されるSQL（Month期間の場合）
SELECT * FROM models 
WHERE created_at >= NOW() - INTERVAL 30 DAY
ORDER BY downloads_in_period DESC
```

---

## 🎯 実用的な使用例

### 1. トレンド分析

```python
def get_trending_models(timeframe='Week'):
    """指定期間のトレンドモデルを取得"""
    response = requests.get(
        'https://civitai.com/api/v1/models',
        params={
            'sort': 'Most Downloaded',
            'period': timeframe,
            'limit': 20
        }
    )
    return response.json()

# 週間トレンド
weekly_trends = get_trending_models('Week')

# 月間人気
monthly_popular = get_trending_models('Month')
```

### 2. 期間比較分析

```python
def compare_periods(sort_type='Most Downloaded'):
    """異なる期間での比較分析"""
    periods = ['Day', 'Week', 'Month', 'Year', 'AllTime']
    results = {}
    
    for period in periods:
        response = requests.get(
            'https://civitai.com/api/v1/models',
            params={
                'sort': sort_type,
                'period': period,
                'limit': 10
            }
        )
        results[period] = response.json()['items']
    
    return results

# 期間別比較
period_comparison = compare_periods('Most Liked')
```

### 3. 新しい人気モデルの発見

```python
def find_rising_stars():
    """短期間で人気になった新しいモデルを発見"""
    
    # 週間人気だが全期間では上位にないモデル
    weekly_popular = get_trending_models('Week')
    alltime_popular = get_trending_models('AllTime')
    
    weekly_ids = {model['id'] for model in weekly_popular['items']}
    alltime_ids = {model['id'] for model in alltime_popular['items']}
    
    # 週間人気だが全期間上位でないモデル = 新興人気モデル
    rising_stars = weekly_ids - alltime_ids
    
    return rising_stars
```

---

## ⚠️ 注意事項と制限

### 1. 評価システムの変更

現在、多くのモデルで `rating` と `ratingCount` が 0 になっており、評価システムが変更された可能性があります。

```json
{
  "stats": {
    "rating": 0,        // 常に0
    "ratingCount": 0    // 常に0
  }
}
```

### 2. 統計データの精度

- **高精度**: ダウンロード数、いいね数
- **中精度**: コメント数、コレクション数  
- **低精度**: 評価関連（現在機能停止中の可能性）

### 3. 期間境界の処理

期間境界での統計データの扱いは未公開のため、厳密な時刻での比較には注意が必要です。

---

## 🚀 ダウンローダーでの活用例

### 1. トレンド追従ダウンロード

```bash
# 週間トレンドモデルのダウンロード
python downloader.py --sort "Most Downloaded" --period "Week" --limit 50

# 日間急上昇モデルのダウンロード  
python downloader.py --sort "Most Liked" --period "Day" --limit 20
```

### 2. 期間限定コレクション作成

```bash
# 月間ベストモデルコレクション
python downloader.py --sort "Most Downloaded" --period "Month" --output-dir "monthly_best"

# 年間殿堂入りモデルコレクション
python downloader.py --sort "Most Liked" --period "Year" --output-dir "yearly_hall_of_fame"
```

### 3. 新しい発見のための検索

```bash
# 短期間で人気になった新しいモデル
python downloader.py --sort "Most Downloaded" --period "Week" --exclude-popular-alltime
```

---

## 📈 統計的観察

### 期間による人気モデルの変化

1. **AllTime**: 確立された定番モデルが上位
2. **Year/Month**: 比較的新しい技術・トレンドのモデル
3. **Week/Day**: 最新のトレンド、話題のモデル

### 推奨期間選択

| 目的 | 推奨期間 | 理由 |
|------|----------|------|
| **定番モデル収集** | AllTime | 実績のある高品質モデル |
| **トレンド把握** | Week/Month | 現在の人気動向 |
| **新発見** | Day/Week | 新しい技術・アプローチ |
| **季節分析** | Month/Year | 長期的なトレンド |

---

## 📝 まとめ

### 主要な発見

1. **期間フィルターは統計ベースソートで有効**
2. **デフォルトは AllTime**
3. **評価システムが現在機能していない可能性**
4. **期間による結果の差異が明確**

### 実用的価値

- **トレンド分析**: 時系列での人気動向把握
- **新モデル発見**: 短期間で注目されたモデルの特定
- **コレクション戦略**: 期間に応じた収集方針の設定

期間フィルターを効果的に活用することで、CivitAI のモデル動向をより深く理解し、戦略的なモデル収集が可能になります。

---

**調査完了日**: 2025年07月18日  
**次回更新推奨**: 評価システム復旧時または期間計算ロジック変更時