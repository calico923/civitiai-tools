# 📁 CivitAI プロジェクト ディレクトリ構造

## 🗂️ 概要
CivitAI API調査とモデルダウンローダー開発プロジェクトの整理されたディレクトリ構造

## 📋 ディレクトリ構成

```
civitiai/
├── 📄 CLAUDE.md                    # Claude向けプロジェクト説明
├── 📄 README.md                    # プロジェクトメインドキュメント
├── 📄 requirements.txt             # Python依存関係
├── 📄 pytest.ini                   # テスト設定
├── 📄 DIRECTORY_STRUCTURE.md       # このファイル
│
├── 📁 src/                         # メインソースコード
│   ├── api/                        # API クライアント
│   │   ├── client.py               # CivitAI API クライアント
│   │   ├── image_downloader.py     # 画像ダウンロード機能
│   │   └── tag_discovery.py        # タグ発見機能
│   ├── cli/                        # コマンドライン インターフェース
│   ├── core/                       # コア機能
│   └── utils/                      # ユーティリティ
│
├── 📁 scripts/                     # 実行スクリプト
│   ├── analysis/                   # 分析スクリプト
│   ├── collection/                 # データ収集スクリプト
│   ├── debug/                      # デバッグ用
│   └── runners/                    # 実行ランナー
│
├── 📁 investigations/              # 🔬 API調査・実験
│   ├── api_tests/                  # API機能テスト
│   │   ├── comprehensive_api_investigation.py
│   │   ├── discover_hidden_endpoints.py
│   │   ├── test_license_api.py
│   │   └── ...
│   ├── model_types/                # モデルタイプ調査
│   │   ├── final_model_types_comprehensive.py
│   │   ├── test_web_filter_types.py
│   │   └── ...
│   ├── basemodel_analysis/         # BaseModel分析
│   │   ├── analyze_basemodel_distribution.py
│   │   ├── test_basemodel_filtering.py
│   │   └── ...
│   ├── checkpoint_analysis/        # Checkpoint詳細分析
│   │   ├── test_checkpoint_subtypes.py
│   │   └── ...
│   └── results/                    # 調査結果データ
│       ├── *.json                  # 構造化結果
│       ├── *.csv                   # 表形式データ
│       └── *.log                   # 実行ログ
│
├── 📁 reports/                     # 📊 HTMLレポート
│   └── civitai_api_specification_report.html
│
├── 📁 docs/                        # 📚 ドキュメント
│   ├── civitai.md                  # CivitAI仕様書
│   ├── plan.md                     # 開発計画
│   ├── requirements.md             # 要件定義
│   └── ...
│
├── 📁 outputs/                     # 🗃️ 出力データ
│   ├── enhanced/                   # 拡張データ
│   ├── analysis/                   # 分析結果
│   ├── checkpoints/                # Checkpointデータ
│   └── loras/                      # LoRAデータ
│
├── 📁 tests/                       # 🧪 テストコード
│   ├── fixtures/                   # テストフィクスチャ
│   └── test_*.py                   # テストファイル
│
└── 📁 temp_scripts/                # 🗑️ 一時スクリプト
    ├── organize_directory.py       # ディレクトリ整理スクリプト
    └── ...                         # 開発中/一時的なスクリプト
```

## 🎯 各ディレクトリの役割

### 📁 src/ - メインソースコード
プロジェクトの核となる実装コード
- **api/**: CivitAI API とのやり取り
- **cli/**: コマンドラインインターフェース
- **core/**: コア機能・ビジネスロジック
- **utils/**: 共通ユーティリティ

### 📁 scripts/ - 実行スクリプト
データ収集・分析用の実行可能スクリプト
- **collection/**: モデルデータ収集
- **analysis/**: データ分析・統計
- **runners/**: 各種タスク実行

### 📁 investigations/ - API調査・実験
CivitAI API の詳細調査と実験用コード
- **api_tests/**: API エンドポイント・機能テスト
- **model_types/**: 17種類のモデルタイプ調査
- **basemodel_analysis/**: BaseModel分布・フィルタリング
- **checkpoint_analysis/**: Checkpoint詳細分析
- **results/**: 調査で得られた生データ

### 📁 reports/ - HTMLレポート
調査結果をまとめた見やすいHTMLレポート

### 📁 outputs/ - 出力データ
実際の収集データ・分析結果
- **enhanced/**: Top100ランキング等の拡張データ
- **checkpoints/**: Checkpointモデル情報
- **loras/**: LoRAモデル情報

### 📁 temp_scripts/ - 一時スクリプト
開発中や特定用途で作成されたスクリプト（定期的に整理）

## 🚀 使用方法

### 基本的なワークフロー
1. **調査**: `investigations/` でAPI機能を調査
2. **実装**: `src/` でメイン機能を実装
3. **実行**: `scripts/` でデータ収集・分析
4. **出力**: `outputs/` に結果を保存
5. **報告**: `reports/` でHTMLレポート生成

### 開発時の注意点
- **新しい調査**: `investigations/` に配置
- **メイン機能**: `src/` に配置
- **一時的なもの**: `temp_scripts/` に配置（後で整理）

## 📊 プロジェクトの成果

### ✅ 完了した調査
- **17種類のモデルタイプ** 完全特定
- **BaseModel分布分析** (17,099モデル)
- **API仕様完全調査** (4エンドポイント、85フィールド)
- **画像取得機能** 完全対応
- **フィルタリング戦略** 確立

### 🎯 次のステップ
1. モデルダウンローダー本体の実装
2. UI/UX の設計
3. パフォーマンス最適化
4. テストカバレッジ向上

---

**📅 最終更新**: 2025年7月17日  
**📋 整理対象**: 42ファイルを適切なディレクトリに移動  
**🎯 目的**: 開発効率向上とプロジェクト構造の明確化