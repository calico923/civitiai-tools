# CivitAI Downloader v2

🎯 **エンタープライズグレード AIモデルダウンローダー** - CivitAIから高品質なAIモデルを効率的にダウンロード・管理するための統合CLIツール

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

## ✨ 主要機能

### 🔍 高度な検索システム
- **AdvancedSearchParams**: 複雑な検索条件とフィルタリング
- **リアルタイムAPI統合**: CivitAI公式APIとの完全統合
- **Triple Filtering**: カテゴリ × タグ × モデルタイプによる三重フィルタリング
- **複数出力フォーマット**: JSON、CSV、テーブル形式での結果出力

### ⬇️ 堅牢なダウンロードシステム
- **非同期ダウンロード**: 高速な並行ダウンロード機能
- **レジューム機能**: 中断されたダウンロードの自動再開
- **整合性検証**: SHA256ハッシュによるファイル検証
- **進捗追跡**: リアルタイムダウンロード進捗表示

### 🛡️ セキュリティ機能
- **セキュリティスキャン**: ダウンロードファイルの脅威検知
- **SafeTensors優先**: 安全なファイル形式の自動選択
- **アクセス制御**: 設定情報の安全な管理とマスキング

### 📊 情報管理
- **詳細モデル情報**: バージョン、ファイル、メタデータの完全表示
- **設定管理**: YAML設定と環境変数のハイブリッド管理
- **構造化ログ**: 詳細なログ記録とデバッグ情報

## 🚀 クイックスタート

### 1. 環境設定

```bash
# リポジトリのクローン
git clone <repository-url>
cd civitai-downloader-v2

# 環境設定ファイルの作成
cp .env.example .env
```

### 2. API キーの設定

`.env` ファイルを編集してCivitAI APIキーを設定：

```bash
CIVITAI_API_KEY=your_actual_civitai_api_key_here
CIVITAI_BASE_URL=https://civitai.com/api/v1
CIVITAI_TIMEOUT=30
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 💻 CLI使用方法

### 🔍 モデル検索

```bash
# 基本検索
python -m src.cli.main search "anime character"

# 詳細検索（JSON出力）
python -m src.cli.main search --limit 10 --format json "LoRA"

# 結果をファイルに保存
python -m src.cli.main search --output results.json "stable diffusion"
```

### 📋 モデル情報表示

```bash
# 基本情報
python -m src.cli.main info 257749

# バージョン情報付き
python -m src.cli.main info 257749 --versions

# ファイル情報付き
python -m src.cli.main info 257749 --versions --files
```

### ⬇️ ダウンロード

```bash
# モデルIDでダウンロード
python -m src.cli.main download 257749

# カスタムディレクトリに保存
python -m src.cli.main download 257749 --output-dir ./models

# セキュリティスキャン付き
python -m src.cli.main download 257749 --scan-security
```

### 🛡️ セキュリティスキャン

```bash
# ファイルスキャン
python -m src.cli.main scan ./model.safetensors

# 詳細レポート
python -m src.cli.main scan ./model.safetensors --detailed
```

### ⚙️ 設定管理

```bash
# 設定一覧
python -m src.cli.main config --list

# 設定値取得
python -m src.cli.main config --get api.timeout

# 設定値変更
python -m src.cli.main config --set api.timeout=60
```

## 📁 プロジェクト構造

```
civitai-downloader-v2/
├── src/
│   ├── cli/                    # CLI インターフェース
│   │   └── main.py            # メインCLI実装
│   ├── api/                   # API クライアント
│   │   ├── client.py          # CivitAI API クライアント
│   │   ├── auth.py            # 認証管理
│   │   └── params.py          # パラメータ定義
│   ├── core/                  # コア機能
│   │   ├── config/            # 設定管理
│   │   ├── download/          # ダウンロード管理
│   │   ├── search/            # 検索エンジン
│   │   ├── security/          # セキュリティ機能
│   │   └── bulk/              # バルクダウンロード
│   ├── data/                  # データ管理
│   │   └── schema_manager.py  # データベーススキーマ
│   └── monitoring/            # ログ・監視
├── tests/                     # テストスイート
├── reports/                   # レポート出力
├── .env.example              # 環境設定テンプレート
└── README.md                 # このファイル
```

## 🔧 設定オプション

### 環境変数

| 変数名 | 説明 | デフォルト値 | 必須 |
|--------|------|-------------|------|
| `CIVITAI_API_KEY` | CivitAI APIキー | なし | ✅ |
| `CIVITAI_BASE_URL` | API ベースURL | `https://civitai.com/api/v1` | ❌ |
| `CIVITAI_TIMEOUT` | APIタイムアウト(秒) | `30` | ❌ |
| `CIVITAI_MAX_RETRIES` | 最大リトライ回数 | `3` | ❌ |
| `CIVITAI_CONCURRENT_DOWNLOADS` | 並行ダウンロード数 | `3` | ❌ |
| `CIVITAI_CHUNK_SIZE` | チャンクサイズ(バイト) | `8192` | ❌ |
| `CIVITAI_VERIFY_SSL` | SSL検証有効化 | `true` | ❌ |
| `CIVITAI_LOG_LEVEL` | ログレベル | `INFO` | ❌ |

### 検索フィルタオプション

```bash
# NSFWフィルタ
--nsfw                    # NSFW コンテンツを含める

# モデルタイプフィルタ  
--types LORA,Checkpoint   # 特定タイプのみ

# ソート
--sort "Most Downloaded"  # ダウンロード数順

# 出力制限
--limit 50               # 結果数制限
```

## 🧪 テスト

```bash
# 全テスト実行
python -m pytest tests/

# 特定モジュール
python -m pytest tests/unit/test_search_engine.py

# カバレッジ付き
python -m pytest tests/ --cov=src --cov-report=html
```

## 🛠️ 開発ステータス

### ✅ Phase 1-4: 完了済み
- [x] **基盤システム**: データベース、ログ、設定管理
- [x] **API統合**: CivitAI API クライアント実装
- [x] **検索エンジン**: 高度な検索・フィルタリング機能
- [x] **ダウンロード**: 並行ダウンロード・レジューム機能
- [x] **セキュリティ**: ファイルスキャン・検証機能
- [x] **CLI インターフェース**: 完全なコマンドライン操作
- [x] **バルクダウンロード**: 大量ダウンロード管理
- [x] **パフォーマンス最適化**: 適応的リソース管理

### 🔄 現在の状況
すべてのコア機能が実装済みで、本番環境での使用準備完了。全CLIコマンドが正常動作し、リアルAPIデータによる完全統合が実現されています。

## 📝 使用例

### 基本的なワークフロー

```bash
# 1. アニメ系LoRAを検索
python -m src.cli.main search --types LORA "anime character" --limit 10

# 2. 特定モデルの詳細確認
python -m src.cli.main info 257749 --versions --files

# 3. 安全にダウンロード
python -m src.cli.main download 257749 --scan-security --output-dir ./anime_models

# 4. ダウンロードファイルをスキャン
python -m src.cli.main scan ./anime_models/model.safetensors --detailed
```

### 高度な検索

```bash
# 複数条件での検索
python -m src.cli.main search --types "LORA,Checkpoint" --nsfw "realistic portrait" --format json --output results.json

# 設定確認とカスタマイズ
python -m src.cli.main config --list
python -m src.cli.main config --set download.concurrent_downloads=5
```

## 🔧 トラブルシューティング

### よくある問題

1. **API エラー 404**: モデルIDが存在しない、または非公開
2. **ダウンロード失敗**: ネットワーク接続またはアクセス権限の問題
3. **設定エラー**: `.env`ファイルの設定確認

### デバッグ

```bash
# 詳細ログ出力
python -m src.cli.main --verbose search "test"

# 設定確認
python -m src.cli.main config --list
```

## 🤝 コントリビューション

1. リポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/new-feature`)
3. 変更をコミット (`git commit -am 'Add new feature'`)
4. ブランチにプッシュ (`git push origin feature/new-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- [CivitAI](https://civitai.com/) - 素晴らしいAIモデルプラットフォームの提供
- Python コミュニティ - 優秀なライブラリとツールの開発

---

## 🆘 サポート

問題が発生した場合は、以下の手順でサポートを受けてください：

1. **ドキュメント確認**: README とヘルプコマンドを確認
2. **ログ確認**: `--verbose` フラグで詳細ログを取得
3. **Issue作成**: バグレポートや機能要求をGitHub Issuesに投稿

**Happy Downloading!** 🎉