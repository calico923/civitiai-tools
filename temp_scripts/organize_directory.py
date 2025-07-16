#!/usr/bin/env python3
"""
ディレクトリの整理スクリプト
"""

import os
import shutil
from pathlib import Path

def organize_civitai_directory():
    """CivitAIディレクトリを適切に整理"""
    
    base_dir = Path('/Users/kuniaki-k/Code/civitiai')
    
    # 作成するディレクトリ構造
    directories = {
        'investigations': 'API調査・実験用スクリプト',
        'investigations/api_tests': 'API テスト関連',
        'investigations/model_types': 'モデルタイプ調査',
        'investigations/basemodel_analysis': 'BaseModel分析',
        'investigations/checkpoint_analysis': 'Checkpoint分析',
        'investigations/results': '調査結果JSON/CSV',
        'reports': 'HTMLレポート',
        'temp_scripts': '一時的なスクリプト',
    }
    
    # ディレクトリ作成
    for dir_path, description in directories.items():
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 作成: {dir_path} - {description}")
    
    # ファイル移動マッピング
    file_moves = {
        # API調査関連
        'analyze_full_api_schema.py': 'investigations/api_tests/',
        'comprehensive_api_investigation.py': 'investigations/api_tests/',
        'create_comprehensive_api_docs.py': 'investigations/api_tests/',
        'discover_hidden_endpoints.py': 'investigations/api_tests/',
        'compare_official_vs_discovered.py': 'investigations/api_tests/',
        'test_license_api.py': 'investigations/api_tests/',
        'test_image_api.py': 'investigations/api_tests/',
        'test_image_download.py': 'investigations/api_tests/',
        'test_image_structure.py': 'investigations/api_tests/',
        
        # モデルタイプ調査
        'investigate_model_types.py': 'investigations/model_types/',
        'extract_all_model_types.py': 'investigations/model_types/',
        'final_model_types_comprehensive.py': 'investigations/model_types/',
        'test_additional_model_types.py': 'investigations/model_types/',
        'quick_type_discovery.py': 'investigations/model_types/',
        'test_web_filter_types.py': 'investigations/model_types/',
        
        # BaseModel分析
        'analyze_basemodel_distribution.py': 'investigations/basemodel_analysis/',
        'test_basemodel_filtering.py': 'investigations/basemodel_analysis/',
        'test_basemodel_tags_search.py': 'investigations/basemodel_analysis/',
        
        # Checkpoint分析
        'test_checkpoint_types.py': 'investigations/checkpoint_analysis/',
        'test_checkpoint_subtypes.py': 'investigations/checkpoint_analysis/',
        'quick_checkpoint_analysis.py': 'investigations/checkpoint_analysis/',
        
        # 調査結果JSON/CSV
        'additional_model_types_investigation.json': 'investigations/results/',
        'api_response_sample.json': 'investigations/results/',
        'basemodel_distribution_analysis.csv': 'investigations/results/',
        'basemodel_distribution_analysis.json': 'investigations/results/',
        'basemodel_filtering_solution.json': 'investigations/results/',
        'basemodel_search_strategy_results.json': 'investigations/results/',
        'checkpoint_subtypes_investigation.json': 'investigations/results/',
        'checkpoint_types_investigation.json': 'investigations/results/',
        'civitai_api_comprehensive_investigation.json': 'investigations/results/',
        'civitai_api_hidden_features.json': 'investigations/results/',
        'civitai_model_types_final_results.json': 'investigations/results/',
        'model_types_complete_analysis.json': 'investigations/results/',
        'model_types_quick_results.json': 'investigations/results/',
        'web_filter_types_validation.json': 'investigations/results/',
        
        # HTMLレポート
        'civitai_api_specification_report.html': 'reports/',
        
        # 一時的なスクリプト（今後削除予定）
        'create_top100_excluding_hall_of_fame.py': 'temp_scripts/',
        'create_hall_of_fame_ranking.py': 'temp_scripts/',
        'create_hall_of_fame_html_report.py': 'temp_scripts/',
        'create_final_top100_html_report.py': 'temp_scripts/',
    }
    
    # ログファイルは investigations/results に
    log_files = [
        'checkpoint_search.log',
        'locon_search.log', 
        'lora_search.log',
        'lora_search_fixed.log',
        'lycoris_search.log'
    ]
    
    for log_file in log_files:
        if (base_dir / log_file).exists():
            file_moves[log_file] = 'investigations/results/'
    
    # ファイル移動実行
    moved_files = []
    for filename, destination in file_moves.items():
        source_path = base_dir / filename
        dest_dir = base_dir / destination
        dest_path = dest_dir / filename
        
        if source_path.exists():
            try:
                shutil.move(str(source_path), str(dest_path))
                moved_files.append(f"{filename} → {destination}")
                print(f"📄 移動: {filename} → {destination}")
            except Exception as e:
                print(f"❌ エラー: {filename} - {e}")
    
    return moved_files

def create_directory_readme():
    """各ディレクトリにREADMEを作成"""
    
    base_dir = Path('/Users/kuniaki-k/Code/civitiai')
    
    readme_contents = {
        'investigations/README.md': '''# 調査・実験ディレクトリ

CivitAI API の詳細調査と実験用スクリプトを格納

## ディレクトリ構成

- `api_tests/` - API エンドポイント・機能テスト
- `model_types/` - モデルタイプ調査
- `basemodel_analysis/` - BaseModel 分析
- `checkpoint_analysis/` - Checkpoint 詳細分析
- `results/` - 調査結果データ（JSON/CSV）
''',
        
        'investigations/api_tests/README.md': '''# API テスト

CivitAI API の機能・エンドポイント調査用スクリプト

## 主要ファイル

- `comprehensive_api_investigation.py` - API 全体調査
- `discover_hidden_endpoints.py` - 隠し機能発見
- `test_license_api.py` - ライセンス情報テスト
- `test_image_*.py` - 画像関連機能テスト
''',
        
        'investigations/model_types/README.md': '''# モデルタイプ調査

CivitAI で利用可能なモデルタイプの詳細調査

## 主要ファイル

- `final_model_types_comprehensive.py` - 最終的な全タイプリスト
- `test_web_filter_types.py` - WebUIとAPIの表記違い調査
- `test_additional_model_types.py` - 新タイプ発見調査
''',
        
        'investigations/basemodel_analysis/README.md': '''# BaseModel 分析

BaseModel（Illustrious、Pony、NoobAI等）の分析と検索戦略

## 主要ファイル

- `analyze_basemodel_distribution.py` - BaseModel 分布分析
- `test_basemodel_filtering.py` - フィルタリング手法テスト
- `test_basemodel_tags_search.py` - Tags 検索テスト
''',
        
        'investigations/checkpoint_analysis/README.md': '''# Checkpoint 詳細分析

Checkpoint の種類（Merge/Trained）とサブタイプ分析

## 主要ファイル

- `test_checkpoint_subtypes.py` - Checkpoint サブタイプ調査
- `quick_checkpoint_analysis.py` - 既存データからの分析
''',
        
        'investigations/results/README.md': '''# 調査結果データ

API 調査で得られた生データと分析結果

## データ形式

- `*.json` - 構造化された調査結果
- `*.csv` - 表形式データ（モデル分布等）
- `*.log` - 実行ログファイル
''',
        
        'reports/README.md': '''# レポート

調査結果をまとめたHTMLレポート

## 主要レポート

- `civitai_api_specification_report.html` - API仕様とダウンローダー開発方針の総合レポート
''',
        
        'temp_scripts/README.md': '''# 一時的なスクリプト

開発中や特定用途で作成されたスクリプト（将来的に削除予定）

## 注意

このディレクトリのファイルは：
- 一時的な用途で作成
- 特定の調査タスクのみで使用
- 定期的に整理・削除される予定
'''
    }
    
    for readme_path, content in readme_contents.items():
        full_path = base_dir / readme_path
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📝 作成: {readme_path}")

def clean_root_directory():
    """ルートディレクトリの最終整理"""
    
    base_dir = Path('/Users/kuniaki-k/Code/civitiai')
    
    print(f"\n🧹 ルートディレクトリの最終整理")
    print("=" * 50)
    
    # ルートに残るべきファイル
    keep_in_root = {
        'CLAUDE.md',
        'README.md', 
        'requirements.txt',
        'pytest.ini',
        '.env',
        '.gitignore'
    }
    
    # ルートに残るべきディレクトリ
    keep_dirs = {
        'src',
        'scripts', 
        'outputs',
        'tests',
        'docs',
        'investigations',
        'reports',
        'temp_scripts',
        'test_images'
    }
    
    root_files = [f for f in base_dir.iterdir() if f.is_file()]
    remaining_files = [f.name for f in root_files if f.name not in keep_in_root]
    
    if remaining_files:
        print(f"⚠️ ルートに残っているファイル:")
        for filename in remaining_files:
            print(f"  - {filename}")
    else:
        print("✅ ルートディレクトリが整理されました")
    
    return remaining_files

def main():
    print("🗂️ CivitAI ディレクトリ整理開始")
    print("=" * 50)
    
    # 1. ディレクトリ整理
    moved_files = organize_civitai_directory()
    
    print(f"\n📊 移動完了: {len(moved_files)}個のファイル")
    
    # 2. README作成
    print(f"\n📝 README ファイル作成中...")
    create_directory_readme()
    
    # 3. 最終チェック
    remaining = clean_root_directory()
    
    print(f"\n✅ ディレクトリ整理完了!")
    print(f"📁 新しい構造:")
    print(f"  ├── investigations/     # API調査・実験")
    print(f"  ├── reports/            # HTMLレポート")
    print(f"  ├── temp_scripts/       # 一時スクリプト")
    print(f"  ├── src/                # メインソースコード")
    print(f"  ├── scripts/            # 実行スクリプト")
    print(f"  ├── outputs/            # 出力データ")
    print(f"  ├── docs/               # ドキュメント")
    print(f"  └── tests/              # テストコード")

if __name__ == "__main__":
    main()