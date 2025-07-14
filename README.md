# CivitAI モデル収集ツール

CivitAI.comからAIモデル（Checkpoint、LoRA）のURLを効率的に収集するPythonツールです。ベースモデル別の分類とカーソルベースページネーションで正確なデータ取得を実現します。

## ✨ 主要機能

- 🔍 **正確なモデル検索**: カーソルベースページネーションで取得漏れを防止
- 🎯 **ベースモデル別収集**: pony、illustrious、noobai別に分類
- 📊 **複数形式出力**: テキスト、CSV、JSON形式でURL出力
- 🚀 **高度な検索方式**: 直接タグ検索 + base model経由検索の統合
- 🏷️ **styleタグ対応**: styleタグ付きLoRAの効率的な収集
- 🌐 **レート制限遵守**: CivitAI API制限に配慮した安全な実装
- 📁 **整理された出力**: ベースモデル別・モデルタイプ別の自動分類

## 📈 取得実績

| ベースモデル | 取得チェックポイント数 | styleタグLoRA数 |
|-------------|-------------------|-----------------|
| **PONY** | 156個 | 169個 |
| **ILLUSTRIOUS** | 243個 | 97個 |
| **NOOBAI** | 51個 | 19個 |
| **合計** | **450個** | **285個** |

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/calico923/civitiai-tools.git
cd civitiai-tools

# Python仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt
```

## クイックスタート

### 1. API設定

[https://civitai.com/user/account](https://civitai.com/user/account) からCivitai APIキーを取得し、設定します：

```bash
# .envファイルを作成
cp .env.example .env

# .envを編集してAPIキーを追加
CIVITAI_API_KEY=your_api_key_here
```

### 2. URL収集モード（安全なテスト）

まず、ファイルをダウンロードせずにURLを収集することから始めます：

```python
from src.core.url_collector import URLCollector

# サンプルモデルデータ（実際のAPI呼び出しに置き換えてください）
sample_models = [
    {
        "id": 12345,
        "name": "素晴らしいLoRA",
        "type": "LORA",
        "tags": ["pony", "style"],
        "creator": {"username": "クリエイター名"},
        "modelVersions": [{
            "id": 67890,
            "files": [{"sizeKB": 1000}]
        }]
    }
]

# URL収集器を初期化
collector = URLCollector()

# モデルデータからURLを収集
urls = collector.collect_model_urls(sample_models)

# 異なる形式でエクスポート
text_file = collector.export_to_text(urls, "my_models.txt")
csv_file = collector.export_to_csv(urls, "my_models.csv") 
json_file = collector.export_to_json(urls, "my_models.json")

print(f"{len(urls)}個のURLをエクスポートしました：")
print(f"- テキスト: {text_file}")
print(f"- CSV: {csv_file}")
print(f"- JSON: {json_file}")
```

### 3. 基本的な使用例

```python
#!/usr/bin/env python3
from src.core.url_collector import URLCollector

def main():
    # Civitai APIからのモデルデータ
    models = [
        # ... API呼び出しからのモデルデータ
    ]
    
    # URL収集器を作成
    collector = URLCollector()
    
    # ダウンロードURLを収集
    urls = collector.collect_model_urls(models)
    print(f"{len(urls)}個のダウンロード可能なモデルが見つかりました")
    
    # URLをエクスポート
    csv_file = collector.export_to_csv(urls)
    print(f"URLをエクスポートしました: {csv_file}")
    
    # 詳細を表示
    for url in urls:
        print(f"- {url.model_name} ({url.model_type})")
        print(f"  サイズ: {url.file_size / (1024*1024):.1f} MB")
        print(f"  URL: {url.download_url}")

if __name__ == "__main__":
    main()
```

## URL収集の出力形式

### テキスト形式
```
# Civitai Model URLs - Generated at 2025-07-14 13:18:45
# Total models: 2

# 素晴らしいLoRA (LORA)
# Tags: pony, style
https://civitai.com/api/download/models/67890

# リアルなCheckpoint (Checkpoint)
# Tags: realistic, portrait
https://civitai.com/api/download/models/98765
```

### CSV形式
```csv
model_id,version_id,model_name,model_type,download_url,file_size_mb,tags,creator,civitai_url
12345,67890,素晴らしいLoRA,LORA,https://civitai.com/api/download/models/67890,0.98,"pony, style",クリエイター名,https://civitai.com/models/12345
```

### JSON形式
```json
{
  "generated_at": "2025-07-14T13:18:45.534447",
  "total_models": 2,
  "models": [
    {
      "model_id": 12345,
      "version_id": 67890,
      "model_name": "素晴らしいLoRA",
      "model_type": "LORA",
      "download_url": "https://civitai.com/api/download/models/67890",
      "file_size": 1024000,
      "tags": ["pony", "style"],
      "creator": "クリエイター名",
      "civitai_url": "https://civitai.com/models/12345"
    }
  ]
}
```

## テスト

すべてが正常に動作することを確認するためにテストスイートを実行します：

```bash
# 全テストを実行
python -m pytest

# カバレッジ付きで実行
python -m pytest --cov=src

# 特定のテストを実行
python -m pytest tests/test_url_collector.py -v
```

## デモ

URL収集の動作を確認するには、付属のデモを試してみてください：

```bash
python demo_url_collector.py
```

これにより以下が実行されます：
1. サンプルモデルデータの処理
2. ダウンロードURLの抽出
3. 複数形式でのエクスポート
4. 詳細な出力の表示

## プロジェクト構造

```
civitiai-tools/
├── .github/                 # GitHub設定
│   ├── workflows/          # GitHub Actions
│   └── linters/            # リンター設定
│       └── .ruff.toml      # Ruffリンター設定
├── src/                     # ソースコード
│   ├── core/               # コア機能
│   │   └── url_collector.py   # URL収集とエクスポート
│   ├── api/                # Civitai API統合
│   │   └── client.py       # APIクライアント（カーソルページネーション対応）
│   ├── utils/              # ユーティリティ
│   │   └── context_manager.py # 大量データの管理
│   └── cli/                # コマンドラインインターフェース
│       ├── flexible_search.py # 環境変数ベース検索
│       └── demo_url_collector.py
├── scripts/                 # 実行スクリプト
│   ├── collection/         # データ収集スクリプト
│   │   ├── final_summary_urls.py # 最終URL取得まとめ
│   │   ├── collect_style_lora_efficient.py
│   │   └── fix_illustrious_checkpoints.py
│   ├── analysis/           # 分析スクリプト
│   │   ├── analyze_style_lora.py
│   │   └── quick_check_base_models.py
│   ├── runners/            # 実行ランナー
│   │   ├── run_flexible_search.py
│   │   └── run_style_lora_collection.py
│   └── debug/              # デバッグ用
│       ├── debug_api_pagination.py
│       └── test_cursor_pagination.py
├── tests/                   # テストスイート
│   ├── test_url_collector.py
│   └── fixtures/           # テストデータ
├── docs/                    # ドキュメント
├── outputs/                 # 生成ファイル（.gitignoreで除外）
│   └── urls/               # URLエクスポート（各ベースモデル別）
├── .coderabbit.yaml        # CodeRabbit設定
├── .gitignore              # Git除外設定
├── .env.example            # 環境変数テンプレート
├── CLAUDE.md               # Claude Code用指示
├── pytest.ini              # テスト設定
├── requirements.txt        # Python依存関係
└── README.md               # このファイル
```

## 環境変数

`.env`ファイルを作成します：

```bash
# Civitai API設定
CIVITAI_API_KEY=your_api_key_here

# 動作モード
DOWNLOAD_ENABLED=false      # true/false（デフォルト: false）
OUTPUT_FORMAT=csv           # text, csv, json
OUTPUT_DIR=./outputs/urls

# ダウンロード設定（DOWNLOAD_ENABLED=trueの場合）
DOWNLOAD_DIR=./models
MAX_CONCURRENT_DOWNLOADS=1
DOWNLOAD_TIMEOUT=300
```

## 開発

このプロジェクトはテスト駆動開発（TDD）に従います：

1. **Red**: まず失敗するテストを書く
2. **Green**: テストをパスする最小限のコードを実装
3. **Refactor**: クリーンアップと最適化

### 開発環境のセットアップ

```bash
# 開発用依存関係をインストール
pip install -r requirements-dev.txt  # 作成予定

# pre-commitフックをセットアップ（オプション）
pre-commit install
```

### 開発時のテスト実行

```bash
# ウォッチモード（pytest-watchをインストール）
pip install pytest-watch
ptw

# 特定機能のテスト
python -m pytest tests/test_url_collector.py::TestURLCollection -v

# デバッグモード
python -m pytest -s -vv
```

### コード品質ツール

```bash
# Ruffでリント
ruff check .

# Ruffで自動修正
ruff check --fix .

# 型チェック（mypyを使用する場合）
mypy src/
```

## 🤖 CI/CD & 自動レビュー

### GitHub Actions
- **Claude Code Review**: PRに対する自動コードレビュー
- **CodeRabbit Integration**: AIによる詳細なコードレビュー

### CodeRabbit設定
このプロジェクトはCodeRabbitによる自動コードレビューが有効です：
- Pythonコードの品質チェック
- セキュリティ脆弱性の検出
- PEP 8準拠の確認
- 依存関係の脆弱性スキャン

設定ファイル：
- `.coderabbit.yaml`: メイン設定
- `.github/linters/.ruff.toml`: Pythonリンター設定

## エラーハンドリング

URL収集器は様々なエッジケースを処理します：

- **モデルバージョンの欠如**: 適切にスキップ
- **空のファイルリスト**: エラーなしで無視
- **不正な形式のデータ**: 自動的にフィルタリング
- **ネットワーク問題**: （将来: リトライロジック）
- **大きなファイルサイズ**: 適切なサイズ計算

## コントリビューション

1. リポジトリをフォーク
2. 機能ブランチを作成
3. まずテストを書く（TDDアプローチ）
4. 機能を実装
5. 全テストの通過を確認
6. プルリクエストを送信

## ライセンス

[ライセンス情報を追加予定]

## 🚀 主要なURLファイル

### チェックポイント
- `outputs/urls/pony_checkpoints_dual_method.txt` (156個)
- `outputs/urls/illustrious_checkpoints_fixed_cursor.txt` (243個)  
- `outputs/urls/noobai_checkpoints_dual_method.txt` (51個)

### styleタグLoRA
- `outputs/urls/style_lora_pony_efficient.txt` (169個)
- `outputs/urls/style_lora_illustrious_efficient.txt` (97個)
- `outputs/urls/style_lora_noobai_efficient.txt` (19個)

## 🔧 実装されたソリューション

1. **カーソルベースページネーション**: CivitAI APIの正しい使用方法
2. **デュアル検索方式**: 直接タグ検索 + base model経由検索の統合
3. **重複除去**: model_idベースの正確な重複処理
4. **効率的な分類**: ベースモデル別の自動フィルタリング
5. **コンテキスト管理**: 大量データの効率的な処理

## ⚠️ 注意事項

- **URLのみ取得**: 実際のファイルダウンロードは行いません
- **API制限遵守**: レート制限に配慮した実装
- **環境変数管理**: `.env`ファイルでAPIキーを安全に管理
