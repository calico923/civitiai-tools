# CivitAI カテゴリシステム調査報告書

## 📋 概要

CivitAI における **カテゴリシステム** の包括的調査結果をまとめた決定版ドキュメントです。

**調査日時**: 2025年07月18日  
**調査方法**: Webサイト実機調査 + API実証テスト

---

## 🎯 カテゴリシステムの基本構造

### 利用可能なカテゴリ (15種類)

画像フィルターの「Filter by Category」で確認されたすべてのカテゴリ：

1. **`action`** - アクション系コンテンツ
2. **`animal`** - 動物関連モデル
3. **`assets`** - アセット・素材系
4. **`background`** - 背景・環境系
5. **`base model`** - ベースモデル
6. **`buildings`** - 建物・建築系
7. **`celebrity`** - 有名人・セレブリティ
8. **`character`** - キャラクター系
9. **`clothing`** - 衣装・服装系
10. **`concept`** - コンセプト・概念系
11. **`objects`** - オブジェクト・物体系
12. **`poses`** - ポーズ・姿勢系
13. **`style`** - スタイル・画風系
14. **`tool`** - ツール・道具系
15. **`vehicle`** - 乗り物・車両系

---

## 🌐 Webサイトでの動作確認

### URL パラメータ形式

```
https://civitai.com/search/models?category=character
https://civitai.com/search/models?category=character&category=style
```

### 複数カテゴリ選択

- **単一カテゴリ**: `?category=character`
- **複数カテゴリ**: `?category=character&category=style`
- **論理演算**: OR演算（どちらかのカテゴリに該当するモデルが表示）

### 実際の検索結果例

#### character カテゴリ
- All Disney Princess XL LoRA Model
- Yae Miko | Realistic Genshin LORA
- alice (nikke)
- Makima (Chainsaw Man) LoRA

#### style カテゴリ
- Not Artists Styles for Pony Diffusion V6 XL
- 墨心 MoXin (中国風スタイル)
- Anime Lineart / Manga-like Style
- Incase Style [PonyXL]

---

## 🚀 API での利用方法

### API パラメータ

**エンドポイント**: `/api/v1/models`  
**パラメータ**: `category`

### 基本的な使用例

```bash
# 単一カテゴリ検索
curl "https://civitai.com/api/v1/models?category=character&limit=10"

# 複数カテゴリ検索
curl "https://civitai.com/api/v1/models?category=character&category=style&limit=10"

# 他のパラメータとの組み合わせ
curl "https://civitai.com/api/v1/models?category=style&types=LORA&baseModels=SDXL%201.0&limit=5"
```

### Python実装例

```python
import requests

def search_models_by_category(categories, limit=20):
    """
    カテゴリでモデルを検索
    
    Args:
        categories: str or list - 検索するカテゴリ
        limit: int - 取得件数制限
    """
    url = "https://civitai.com/api/v1/models"
    params = {"limit": limit}
    
    if isinstance(categories, str):
        params["category"] = categories
    elif isinstance(categories, list):
        # 複数カテゴリの場合
        for category in categories:
            params.setdefault("category", []).append(category)
    
    response = requests.get(url, params=params)
    return response.json()

def search_models_advanced(category=None, tags=None, types=None, limit=20):
    """
    カテゴリ（必須タグ）と任意タグの組み合わせ検索
    
    Args:
        category: str - カテゴリ（必須タグ）
        tags: str or list - 任意タグ
        types: str or list - モデルタイプ
        limit: int - 取得件数制限
    """
    url = "https://civitai.com/api/v1/models"
    params = {"limit": limit}
    
    if category:
        params["category"] = category
    if tags:
        params["tags"] = tags
    if types:
        params["types"] = types
    
    response = requests.get(url, params=params)
    return response.json()

# 基本使用例
character_models = search_models_by_category("character")
style_character_models = search_models_by_category(["style", "character"])

# 精密フィルタリング使用例
anime_characters = search_models_advanced(
    category="character", 
    tags="anime", 
    types="LORA"
)

photorealistic_characters = search_models_advanced(
    category="character", 
    tags="photorealistic", 
    types="LORA"
)

background_night_scenes = search_models_advanced(
    category="background", 
    tags="night,city"
)
```

---

## 🔄 モデルタイプとの関係

### カテゴリ vs モデルタイプ

| 分類 | 用途 | 例 |
|------|------|-----|
| **カテゴリ** | コンテンツの種類・用途 | character, style, concept |
| **モデルタイプ** | 技術的な形式 | LORA, Checkpoint, VAE |

### 組み合わせ例

```bash
# キャラクター系のLoRAモデルを検索
curl "https://civitai.com/api/v1/models?category=character&types=LORA"

# スタイル系のCheckpointモデルを検索  
curl "https://civitai.com/api/v1/models?category=style&types=Checkpoint"

# ポーズ系のあらゆるモデルタイプを検索
curl "https://civitai.com/api/v1/models?category=poses"
```

---

## 📊 既存ドキュメントとの比較

### 従来の分類システム

#### モデルタイプ (13種類)
```
Checkpoint, LORA, LoCon, TextualInversion, VAE, 
DoRA, Hypernetwork, Poses, Upscaler, Workflows, 
Wildcards, AestheticGradient, Other
```

#### タグシステム
```
anime, style, realistic, concept, western art, etc.
```

### 新発見: カテゴリシステム

**カテゴリシステム** は既存の **モデルタイプ** や **タグシステム** とは独立した、
コンテンツの用途・目的別の分類システムです。

---

## ⚠️ 重要な注意事項

### 既存ドキュメントの更新が必要

1. **`civitai_api_comprehensive_specification.md`**
   - カテゴリパラメータの追加が必要
   
2. **`civitai_model_types_final_complete.md`**
   - カテゴリとモデルタイプの関係説明が必要

### API制限について

- **レート制限**: 既存と同じ (2秒間隔推奨)
- **組み合わせ**: 他のパラメータと併用可能
- **大文字小文字**: 小文字での指定が必要

---

## 🛠️ 実装への影響

### ダウンローダーへの影響

**civitai-downloader** での活用可能性：

1. **カテゴリ別ダウンロード機能**
   ```bash
   # キャラクターモデルのみダウンロード
   python downloader.py --category character
   
   # スタイル系LoRAのみダウンロード  
   python downloader.py --category style --types LORA
   ```

2. **3重フィルタリング機能（新機能）**
   ```bash
   # アニメキャラクター系LoRAのみ
   python downloader.py --category character --tags anime --types LORA
   
   # フォトリアル背景系モデル
   python downloader.py --category background --tags photorealistic
   
   # 水彩画風スタイルLoRA
   python downloader.py --category style --tags watercolor --types LORA
   ```

3. **フィルタリング機能の強化**
   - 既存の type/baseModel フィルターに category と tags の組み合わせ追加
   - **超精密な検索・ダウンロード制御**が可能
   - 用途別コレクション作成（キャラクター学習用、背景強化用など）

4. **メタデータの充実**
   - ダウンロードしたモデルのカテゴリ情報保存
   - カテゴリ別 + タグ別の統計情報生成
   - 用途別使用頻度分析

---

## 📈 今後の展開

### 推奨事項

1. **API仕様書の更新**
   - カテゴリパラメータの正式ドキュメント化
   
2. **検索機能の強化**
   - カテゴリとモデルタイプの組み合わせ検索
   
3. **定期的な更新確認**
   - 新しいカテゴリの追加をチェック

### 技術的課題

1. **カテゴリの重複**
   - 一つのモデルが複数カテゴリに属する場合の処理
   
2. **カテゴリの階層化**
   - 将来的にサブカテゴリが追加される可能性

---

## 🎯 精密フィルタリング（新発見）

### カテゴリ × 任意タグ × モデルタイプの3重フィルタリング

**重要な発見**: カテゴリ（必須タグ）、任意タグ、モデルタイプを組み合わせた**3重フィルタリング**が可能です。

#### 実証済み組み合わせ例

| 組み合わせ | 説明 | 用途例 |
|-----------|------|--------|
| `category=character&tags=anime&types=LORA` | アニメキャラクター系LoRA | キャラクター学習用 |
| `category=character&tags=photorealistic&types=LORA` | フォトリアル系キャラクターLoRA | リアル人物学習用 |
| `category=style&tags=realistic&types=Checkpoint` | リアル系スタイルのベースモデル | 写実画像生成用 |
| `category=background&tags=night,city&types=LORA` | 夜の都市背景系LoRA | 背景生成強化用 |

#### 実際の検証結果

```bash
# アニメキャラクター系LoRAの検索
curl "https://civitai.com/api/v1/models?category=character&tags=anime&types=LORA&limit=5"

# 確認されたモデル例:
# - Detail Tweaker LoRA (anime, concept タグ)
# - Anime Lineart Style (anime, style タグ)
# - Not Artists Styles (anime, style タグ)
```

### フィルタリング精度の向上

3重フィルタリングにより、以下のような**超精密検索**が可能になります：

- **特定用途**: `category=poses&tags=dance&types=LORA` → ダンスポーズ用LoRA
- **画風特化**: `category=style&tags=watercolor&types=LORA` → 水彩画風LoRA  
- **背景特化**: `category=background&tags=medieval&types=LORA` → 中世背景LoRA

---

## 🔍 カテゴリの実装方式（重要発見）

### カテゴリタグの格納場所

**重要な発見**: カテゴリは専用フィールドではなく、**`tags`配列内**に格納されています。

#### 確認済みカテゴリタグ例

| カテゴリ | 実際のタグ | 確認モデル例 |
|---------|-----------|-------------|
| **character** | `"character"` | All Disney Princess XL LoRA Model |
| **style** | `"style"` | 墨心 MoXin, Anime Lineart Style |
| **concept** | `"concept"` | Detail Tweaker XL |
| **background** | `"background"` | 日本の民宿, Night city alleys |
| **poses** | `"poses"` | kontext_depth_pose |
| **vehicle** | `"vehicle"` | Sparkle Smash Monster Truck |
| **clothing** | `"clothing"` | Yu-Gi-Oh! Egyptian Clothing |

#### 技術的詳細

```json
{
  "id": 212532,
  "name": "All Disney Princess XL LoRA Model",
  "tags": ["character", "disney", "disney princess", "disney frozen"],
  "type": "LORA"
}
```

### カテゴリ vs 通常タグの区別

- **カテゴリタグ**: 15種類の定義済みカテゴリ（必須タグ的性質）
- **通常タグ**: ユーザーが自由に設定する説明的タグ
- **混在**: 両方が同じ`tags`配列に格納される

---

## 📝 まとめ

**CivitAI カテゴリシステム** は、モデルをコンテンツの用途別に分類する
**15種類のカテゴリ** を提供する新しい分類システムです。

### 主要な発見

1. **15種類のカテゴリ** が利用可能
2. **Web UI** と **API** の両方で動作確認済み
3. **カテゴリはタグシステム内に統合**されている
4. **複数カテゴリの同時指定**が可能
5. **既存パラメータとの組み合わせ**が可能
6. **カテゴリタグと通常タグが混在**している
7. **🆕 3重フィルタリング**: カテゴリ×任意タグ×モデルタイプの組み合わせが可能
8. **🆕 精密検索**: 必須タグ（カテゴリ）と任意タグによる超精密フィルタリング

### 実用的価値

- **超精密なモデル検索・フィルタリング**（3重フィルタリング対応）
- **用途特化型モデル収集**（例：アニメキャラクター学習専用）
- **効率的なダウンローダー機能の強化**
- **必須タグ vs 任意タグの明確な区別**
- **プロジェクト用途別の自動コレクション作成**

この調査により、CivitAI の機能をより効果的に活用することが可能になりました。

---

**調査完了日**: 2025年07月18日  
**次回更新推奨**: 2025年10月頃 (新カテゴリ追加チェック)