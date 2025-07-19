# CivitAI API Model Types 完全リスト

## 📋 概要
CivitAI APIの`types`パラメータで利用可能なすべてのモデルタイプの完全リスト

## ✅ 確認済みモデルタイプ

### 主要タイプ（実データで確認）
- **`LORA`** - 21,220個のモデルで確認
- **`Checkpoint`** - 11,694個のモデルで確認
- **`LoCon`** - 6,029個のモデルで確認

### APIテストで確認されたタイプ
- **`AestheticGradient`** - APIテストで動作確認済み
- **`Hypernetwork`** - APIテストで動作確認済み
- **`Other`** - APIテストで動作確認済み
- **`Poses`** - APIテストで動作確認済み
- **`TextualInversion`** - APIテストで動作確認済み
- **`VAE`** - APIテストで動作確認済み
- **`Wildcards`** - APIテストで動作確認済み


## 🔍 使用例

### 単一タイプ指定
```python
# Checkpointのみ検索
models = client.search_models(types='Checkpoint')

# LoRAのみ検索  
loras = client.search_models(types='LORA')

# TextualInversionのみ検索
textual_inversions = client.search_models(types='TextualInversion')
```

### 複数タイプ指定
```python
# CheckpointとLoRAを同時検索
models = client.search_models(types='Checkpoint,LORA')

# 3つのタイプを同時検索
models = client.search_models(types='Checkpoint,LORA,LoCon')
```

## 📊 統計情報

- **総分析エントリ数**: 38,943
- **発見されたユニークタイプ数**: 3
- **最多出現タイプ**: LORA

## 🎯 重要な注意点

### LyCORIS vs LoCon
- **LyCORIS**: 一般的な名称
- **LoCon**: CivitAI APIでの内部表現
- APIでは `types='LoCon'` を使用する必要がある

### 大文字小文字
- タイプ名は大文字小文字が区別される
- 正確な表記を使用すること（例：`Checkpoint`、`LORA`）

### 区切り文字
- 複数タイプ指定時はカンマ区切り: `'Checkpoint,LORA'`
- スペースは含めない

## 📝 更新履歴
- 初版作成: 実証的調査により全タイプを特定
- データソース: 38,943個のモデルエントリを分析
