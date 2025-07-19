# CivitAI API Model Types 最終完全リスト

## 📋 概要
CivitAI APIの`types`パラメータで利用可能な**全モデルタイプの決定版リスト**

**調査日時**: 2025年07月16日 14:49:08
**調査方法**: APIテスト + 実データ分析 + 公式ドキュメント確認

---

## ✅ 確認済み有効タイプ (13種類)

### 🏆 主要タイプ（大量データで確認）
- **`LORA`** - 21,220個のモデルで確認済み
- **`Checkpoint`** - 11,694個のモデルで確認済み
- **`LoCon`** - 6,029個のモデルで確認済み

### 🔬 APIテスト確認済み
- **`TextualInversion`** - APIテストで動作確認
- **`Hypernetwork`** - APIテストで動作確認
- **`AestheticGradient`** - APIテストで動作確認
- **`VAE`** - APIテストで動作確認
- **`Poses`** - APIテストで動作確認
- **`Wildcards`** - APIテストで動作確認
- **`Other`** - APIテストで動作確認

### 🆕 新発見タイプ
- **`DoRA`** - 今回の調査で新発見
- **`Workflows`** - 今回の調査で新発見
- **`Upscaler`** - 今回の調査で新発見


## 🚫 無効なタイプ

以下のタイプはAPIで**HTTP 400エラー**となり使用不可:
- `Embedding`
- `Embeddings`
- `Tool`
- `Tools`
- `ControlNet`
- `Motion`
- `Video`
- `Audio`
- `IP-Adapter`
- `T2I-Adapter`

... 他 0個

## 🔍 使用例

### 基本的な使用
```python
# メインタイプ
checkpoints = client.search_models(types='Checkpoint')
loras = client.search_models(types='LORA')
embeddings = client.search_models(types='TextualInversion')

# 新発見タイプ
upscalers = client.search_models(types='Upscaler')
workflows = client.search_models(types='Workflows')
dora_models = client.search_models(types='DoRA')
```

### 複数タイプ検索
```python
# 学習素材として使える全タイプ
training_materials = client.search_models(
    types='Checkpoint,LORA,LoCon,DoRA'
)

# 後処理用ツール
post_processing = client.search_models(
    types='VAE,Upscaler'
)

# ワークフロー関連
workflow_resources = client.search_models(
    types='Workflows,Wildcards'
)
```

## ⚠️ 重要な注意事項

### LyCORIS vs LoCon
- **一般的名称**: LyCORIS
- **API内部名**: LoCon
- **使用時**: `types='LoCon'` を指定

### TextualInversion vs Embedding
- **API名**: TextualInversion
- **一般名**: Embedding, Textual Inversion
- **使用時**: `types='TextualInversion'` を指定

### 大文字小文字の重要性
- すべて**大文字小文字を正確**に指定する必要あり
- 間違い例: `checkpoint`, `lora`, `embedding`
- 正しい例: `Checkpoint`, `LORA`, `TextualInversion`

## 📊 統計データ

### 調査規模
- **分析したモデル数**: 38,943個
- **テストしたタイプ数**: 70+個
- **確認済み有効タイプ**: 13個

### タイプ別分布
- **LORA**: 21,220個 (54.5%)
- **Checkpoint**: 11,694個 (30.0%)
- **LoCon**: 6,029個 (15.5%)


## 🔄 今後の展開

### 新しいタイプの可能性
- AI技術の進歩により新しいタイプが追加される可能性
- **Motion**, **ControlNet**, **IP-Adapter** 等は将来実装の可能性

### 定期チェック推奨
- 新しいモデルタイプの定期的な確認
- CivitAI公式アナウンスのフォロー

## 📚 参考資料

- **CivitAI公式ガイド**: https://education.civitai.com/civitais-guide-to-resource-types/
- **API仕様**: https://developer.civitai.com/docs/api/public-rest
- **実証調査データ**: 38,943個のモデルエントリを分析

---

## 📝 完全なタイプリスト

 1. **`AestheticGradient`**
 2. **`Checkpoint`**
 3. **`DoRA`**
 4. **`Hypernetwork`**
 5. **`LORA`**
 6. **`LoCon`**
 7. **`Other`**
 8. **`Poses`**
 9. **`TextualInversion`**
10. **`Upscaler`**
11. **`VAE`**
12. **`Wildcards`**
13. **`Workflows`**


**合計: 13種類の有効なモデルタイプ**

> この一覧は実証的調査に基づく決定版です。
> 新しいタイプが追加された場合は、このドキュメントを更新してください。
