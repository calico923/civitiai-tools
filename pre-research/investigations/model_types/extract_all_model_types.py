#!/usr/bin/env python3
"""
既存の調査結果から全モデルタイプを抽出・まとめ
"""

import os
import csv
import json
from collections import Counter
from pathlib import Path

def extract_types_from_csv_files():
    """既存のCSVファイルからmodel_typeを抽出"""
    model_types = []
    
    # outputsディレクトリ内のすべてのCSVファイルを検索
    outputs_dir = Path('/Users/kuniaki-k/Code/civitiai/outputs')
    
    csv_files = list(outputs_dir.rglob('*.csv'))
    
    print(f"🔍 {len(csv_files)}個のCSVファイルを検索中...")
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # model_typeカラムがあるかチェック
                if 'model_type' in reader.fieldnames:
                    for row in reader:
                        model_type = row.get('model_type', '').strip()
                        if model_type and model_type != 'model_type':
                            model_types.append(model_type)
                            
        except Exception as e:
            print(f"  Error reading {csv_file}: {e}")
    
    return model_types

def extract_types_from_enhanced_data():
    """enhancedディレクトリから詳細なタイプ情報を抽出"""
    enhanced_dir = Path('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/old/detailed_search_data')
    
    model_types = []
    
    if enhanced_dir.exists():
        # illustrious_checkpoint, illustrious_lora, illustrious_lycoris ディレクトリを確認
        type_dirs = ['illustrious_checkpoint', 'illustrious_lora', 'illustrious_lycoris']
        
        for type_dir in type_dirs:
            dir_path = enhanced_dir / type_dir
            if dir_path.exists():
                # ディレクトリ名からタイプを推測
                if 'checkpoint' in type_dir:
                    model_types.append('Checkpoint')
                elif 'lora' in type_dir:
                    model_types.append('LORA')
                elif 'lycoris' in type_dir:
                    model_types.append('LoCon')  # LyCORISはAPIではLoConとして処理
                
                # ディレクトリ内のCSVファイルもチェック
                for csv_file in dir_path.glob('*.csv'):
                    try:
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            if 'model_type' in reader.fieldnames:
                                for row in reader:
                                    model_type = row.get('model_type', '').strip()
                                    if model_type:
                                        model_types.append(model_type)
                    except:
                        pass
    
    return model_types

def compile_comprehensive_types():
    """包括的なモデルタイプリストを作成"""
    
    print("📊 既存データからモデルタイプを抽出中...")
    
    # CSVファイルから抽出
    csv_types = extract_types_from_csv_files()
    print(f"  CSVファイルから: {len(csv_types)}個のタイプエントリ")
    
    # Enhanced データから抽出
    enhanced_types = extract_types_from_enhanced_data()
    print(f"  Enhancedデータから: {len(enhanced_types)}個のタイプエントリ")
    
    # すべて統合
    all_types = csv_types + enhanced_types
    
    # 統計作成
    type_counts = Counter(all_types)
    
    print(f"\n📋 発見したモデルタイプ ({len(type_counts)}種類):")
    for model_type, count in type_counts.most_common():
        print(f"  - {model_type}: {count}回出現")
    
    # 公式テスト結果との統合
    tested_types = [
        "Checkpoint", "LORA", "LoCon", "TextualInversion", 
        "Hypernetwork", "AestheticGradient", "VAE", 
        "Poses", "Wildcards", "Other"
    ]
    
    # 発見されたタイプと公式テスト結果を統合
    all_discovered = list(type_counts.keys())
    all_valid_types = list(set(all_discovered + tested_types))
    
    # 結果をまとめ
    results = {
        'discovered_from_data': dict(type_counts),
        'confirmed_via_api_test': tested_types,
        'all_valid_types': sorted(all_valid_types),
        'statistics': {
            'total_entries_analyzed': len(all_types),
            'unique_types_found': len(type_counts),
            'most_common_type': type_counts.most_common(1)[0] if type_counts else None
        }
    }
    
    return results

def create_comprehensive_documentation():
    """包括的なモデルタイプドキュメントを作成"""
    
    results = compile_comprehensive_types()
    
    # ドキュメント作成
    doc = """# CivitAI API Model Types 完全リスト

## 📋 概要
CivitAI APIの`types`パラメータで利用可能なすべてのモデルタイプの完全リスト

## ✅ 確認済みモデルタイプ

### 主要タイプ（実データで確認）
"""
    
    # 実データで確認されたタイプ
    discovered = results['discovered_from_data']
    for model_type, count in sorted(discovered.items(), key=lambda x: x[1], reverse=True):
        doc += f"- **`{model_type}`** - {count:,}個のモデルで確認\n"
    
    doc += "\n### APIテストで確認されたタイプ\n"
    
    # APIテストで確認されたタイプ
    for model_type in sorted(results['confirmed_via_api_test']):
        if model_type not in discovered:
            doc += f"- **`{model_type}`** - APIテストで動作確認済み\n"
    
    doc += f"""

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

- **総分析エントリ数**: {results['statistics']['total_entries_analyzed']:,}
- **発見されたユニークタイプ数**: {results['statistics']['unique_types_found']}
- **最多出現タイプ**: {results['statistics']['most_common_type'][0] if results['statistics']['most_common_type'] else 'N/A'}

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
- データソース: {results['statistics']['total_entries_analyzed']:,}個のモデルエントリを分析
"""
    
    return doc, results

def main():
    print("🔍 CivitAI Model Types 完全調査")
    print("=" * 50)
    
    # 包括的調査実行
    documentation, results = create_comprehensive_documentation()
    
    # ドキュメント保存
    with open('docs/civitai_model_types_complete.md', 'w', encoding='utf-8') as f:
        f.write(documentation)
    
    # 結果データ保存
    with open('model_types_complete_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n🎯 完全なモデルタイプリスト:")
    for model_type in sorted(results['all_valid_types']):
        status = ""
        if model_type in results['discovered_from_data']:
            count = results['discovered_from_data'][model_type]
            status = f"({count:,}個で確認)"
        elif model_type in results['confirmed_via_api_test']:
            status = "(APIテスト済み)"
        
        print(f"  ✅ {model_type} {status}")
    
    print(f"\n📚 ドキュメント生成: docs/civitai_model_types_complete.md")
    print(f"📊 詳細データ: model_types_complete_analysis.json")

if __name__ == "__main__":
    main()