#!/usr/bin/env python3
"""
CivitAI API Model Types の最終的な包括調査結果
"""

import json
from datetime import datetime

def create_final_documentation():
    """最終的な包括ドキュメントを作成"""
    
    # 全調査結果を統合
    final_results = {
        # APIテストで確認済みの基本タイプ
        "confirmed_basic_types": [
            "Checkpoint", "LORA", "LoCon", "TextualInversion", 
            "Hypernetwork", "AestheticGradient", "VAE", 
            "Poses", "Wildcards", "Other"
        ],
        
        # 新発見のタイプ
        "newly_discovered_types": [
            "DoRA", "Workflows", "Upscaler"
        ],
        
        # 公式教育記事で言及されているタイプ
        "officially_mentioned_types": [
            "Checkpoint", "LORA", "LyCORIS", "Embedding", "VAE", "Workflows", "Wildcards"
        ],
        
        # APIで無効/利用不可
        "invalid_types": [
            "Embedding", "Embeddings", "Tool", "Tools", "ControlNet", 
            "Motion", "Video", "Audio", "IP-Adapter", "T2I-Adapter"
        ],
        
        # 実データ統計
        "data_statistics": {
            "LORA": 21220,
            "Checkpoint": 11694,
            "LoCon": 6029
        }
    }
    
    # 全有効タイプリスト（重複除去）
    all_valid = set()
    all_valid.update(final_results["confirmed_basic_types"])
    all_valid.update(final_results["newly_discovered_types"])
    
    final_valid_types = sorted(list(all_valid))
    
    # ドキュメント作成
    doc = f"""# CivitAI API Model Types 最終完全リスト

## 📋 概要
CivitAI APIの`types`パラメータで利用可能な**全モデルタイプの決定版リスト**

**調査日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**調査方法**: APIテスト + 実データ分析 + 公式ドキュメント確認

---

## ✅ 確認済み有効タイプ ({len(final_valid_types)}種類)

### 🏆 主要タイプ（大量データで確認）
"""
    
    for type_name in ["LORA", "Checkpoint", "LoCon"]:
        count = final_results["data_statistics"].get(type_name, 0)
        doc += f"- **`{type_name}`** - {count:,}個のモデルで確認済み\n"
    
    doc += "\n### 🔬 APIテスト確認済み\n"
    for type_name in final_results["confirmed_basic_types"]:
        if type_name not in final_results["data_statistics"]:
            doc += f"- **`{type_name}`** - APIテストで動作確認\n"
    
    doc += "\n### 🆕 新発見タイプ\n"
    for type_name in final_results["newly_discovered_types"]:
        doc += f"- **`{type_name}`** - 今回の調査で新発見\n"
    
    doc += f"""

## 🚫 無効なタイプ

以下のタイプはAPIで**HTTP 400エラー**となり使用不可:
"""
    
    for type_name in final_results["invalid_types"][:10]:  # 最初の10個
        doc += f"- `{type_name}`\n"
    
    doc += f"""
... 他 {len(final_results['invalid_types']) - 10}個

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
- **分析したモデル数**: {sum(final_results['data_statistics'].values()):,}個
- **テストしたタイプ数**: 70+個
- **確認済み有効タイプ**: {len(final_valid_types)}個

### タイプ別分布
"""
    
    for type_name, count in sorted(final_results["data_statistics"].items(), key=lambda x: x[1], reverse=True):
        percentage = count / sum(final_results["data_statistics"].values()) * 100
        doc += f"- **{type_name}**: {count:,}個 ({percentage:.1f}%)\n"
    
    doc += f"""

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

"""
    
    for i, type_name in enumerate(final_valid_types, 1):
        doc += f"{i:2d}. **`{type_name}`**\n"
    
    doc += f"""

**合計: {len(final_valid_types)}種類の有効なモデルタイプ**

> この一覧は実証的調査に基づく決定版です。
> 新しいタイプが追加された場合は、このドキュメントを更新してください。
"""
    
    return doc, final_valid_types

def main():
    print("📚 CivitAI Model Types 最終包括調査")
    print("=" * 50)
    
    documentation, final_types = create_final_documentation()
    
    # 最終ドキュメント保存
    with open('docs/civitai_model_types_final_complete.md', 'w', encoding='utf-8') as f:
        f.write(documentation)
    
    # 最終結果データ保存
    final_data = {
        'final_valid_types': final_types,
        'total_count': len(final_types),
        'investigation_date': datetime.now().isoformat(),
        'data_sources': [
            'API endpoint testing',
            'Real model data analysis (38,943 entries)',
            'Official documentation review'
        ]
    }
    
    with open('civitai_model_types_final_results.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print("🎯 最終結果:")
    print(f"  ✅ 有効なモデルタイプ: {len(final_types)}種類")
    print(f"  📊 分析データ: 38,943個のモデル")
    print(f"  🔬 テスト済みタイプ: 70+個")
    
    print(f"\n📋 完全なタイプリスト:")
    for i, type_name in enumerate(final_types, 1):
        print(f"  {i:2d}. {type_name}")
    
    print(f"\n📚 ドキュメント: docs/civitai_model_types_final_complete.md")
    print(f"📊 データファイル: civitai_model_types_final_results.json")

if __name__ == "__main__":
    main()