# 🚀 CivitAI Downloader v2

**エンタープライズ級AIモデル管理プラットフォーム**

バルク操作、セキュリティスキャン、分析機能、エンタープライズレベルの信頼性を備えた、CivitAIからAIモデルを発見、ダウンロード、管理するための包括的な高性能ツールです。

[![Tests](https://img.shields.io/badge/tests-112%20passed-brightgreen)]() [![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]() [![Quality](https://img.shields.io/badge/quality-production%20ready-blue)]()

## ✨ 主要機能

### 🔍 **高度な検索・発見機能**
- **デュアル検索戦略**: 直接タグ検索 + ベースモデルフィルタリング
- **85以上のAPIフィールド**: 完全なモデルメタデータ収集  
- **15カテゴリ**: 包括的なモデル分類
- **スマート重複除去**: インテリジェントな重複排除

### 📥 **エンタープライズダウンロード管理**
- **バルク操作**: 数百のモデルを効率的に処理
- **再開機能**: 自動ダウンロード再開
- **セキュリティスキャン**: マルウェア検出とファイル検証
- **パフォーマンス最適化**: 適応的リソース管理

### 🛡️ **セキュリティ・コンプライアンス**
- **多層セキュリティ**: 暗号化、アクセス制御、監査証跡
- **ライセンス管理**: 自動ライセンス準拠チェック
- **サンドボックス実行**: 安全なファイル処理環境
- **プライバシー保護**: 有名人コンテンツフィルタリング

### 📊 **分析・インテリジェンス**
- **使用状況分析**: 包括的なダウンロードと使用状況の洞察
- **パフォーマンス指標**: システム最適化推奨事項
- **インタラクティブレポート**: HTML/JSON/CSVエクスポート形式
- **予測分析**: リソース使用量予測

### 🔧 **信頼性・拡張性**  
- **サーキットブレーカー**: 自動障害分離
- **ヘルス監視**: リアルタイムシステムステータス
- **プラグインアーキテクチャ**: カスタム機能拡張
- **API変更検知**: API更新への自動適応

## 🚀 クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-org/civitai-downloader-v2.git
cd civitai-downloader-v2

# 依存関係をインストール
pip install -r requirements.txt

# 環境をセットアップ
cp config/app_config.yml.example config/app_config.yml
```

### 2. 設定

設定ファイルを作成します：

```bash
# 設定を編集
nano config/app_config.yml
```

**必須設定:**
```yaml
api:
  civitai_api_key: "YOUR_API_KEY_HERE"
  base_url: "https://civitai.com/api/v1"
  rate_limit: 0.5  # 1秒あたりのリクエスト数

download:
  base_directory: "./downloads"
  concurrent_downloads: 3
  verify_checksums: true
  
security:
  enable_scanning: true
  require_confirmation: true
  allow_nsfw: false
```

### 3. 基本的な使用方法

```bash
# モデルを検索して表示
python -m src.cli.main search "アニメキャラクター" --limit 10

# 特定のモデルをダウンロード
python -m src.cli.main download --model-id 12345

# 検索結果からバルクダウンロード
python -m src.cli.main bulk-download "スタイルLORA" --limit 50 --format safetensors

# 分析レポートを生成
python -m src.cli.main analytics --period 7d --format html
```

## 📖 完全使用ガイド

### 🔍 検索操作

#### 基本検索
```bash
# クエリで検索
python -m src.cli.main search "サイバーパンクスタイル"

# モデルタイプでフィルタ  
python -m src.cli.main search "キャラクター" --types Checkpoint,LORA

# ベースモデルでフィルタ
python -m src.cli.main search "アニメ" --base-models "Illustrious,NoobAI"

# 高度なフィルタリング
python -m src.cli.main search "ポートレート" \
    --categories character,style \
    --min-downloads 1000 \
    --period Month \
    --sort "Most Downloaded"
```

#### 検索結果のエクスポート
```bash
# さまざまな形式でエクスポート
python -m src.cli.main search "メカ" --export json --output mecha_models.json
python -m src.cli.main search "風景" --export csv --output landscapes.csv
python -m src.cli.main search "ファンタジー" --export html --output fantasy_report.html
```

### 📥 ダウンロード操作

#### シングルダウンロード
```bash
# モデルIDでダウンロード
python -m src.cli.main download --model-id 123456

# 特定のバージョンをダウンロード
python -m src.cli.main download --model-id 123456 --version-id 789

# カスタムディレクトリにダウンロード
python -m src.cli.main download --model-id 123456 --output-dir ./custom_models/
```

#### バルクダウンロード
```bash
# 検索からバルクダウンロード
python -m src.cli.main bulk-download "アニメキャラクター" \
    --limit 100 \
    --batch-size 10 \
    --priority HIGH

# 失敗したバルクダウンロードを再開
python -m src.cli.main bulk-resume --job-id bulk_20250122_001

# バルクダウンロードの進行状況を監視
python -m src.cli.main bulk-status --job-id bulk_20250122_001
```

#### 高度なダウンロードオプション
```bash
# セキュリティ重視のダウンロード
python -m src.cli.main download --model-id 123456 \
    --scan-before-download \
    --verify-hashes \
    --require-safetensors

# パフォーマンス最適化されたダウンロード
python -m src.cli.main download --model-id 123456 \
    --optimization-mode adaptive \
    --concurrent-chunks 8
```

### 📊 分析・レポート機能

#### レポート生成
```bash
# クイック分析サマリー
python -m src.cli.main analytics

# 特定期間の詳細レポート
python -m src.cli.main analytics --period 30d --format html --output monthly_report.html

# パフォーマンス分析
python -m src.cli.main analytics --type performance --show-recommendations

# 使用統計
python -m src.cli.main analytics --type usage --group-by model_type,base_model
```

#### システム監視
```bash
# システムヘルスチェック
python -m src.cli.main health-check

# パフォーマンス指標
python -m src.cli.main metrics --live

# ログを表示
python -m src.cli.main logs --level ERROR --tail 100
```

### 🔧 管理操作

#### データベース管理
```bash
# データベース状況
python -m src.cli.main db-status

# 孤立レコードのクリーンアップ
python -m src.cli.main db-cleanup

# データベースをエクスポート/バックアップ
python -m src.cli.main db-export --output backup_20250122.sql
```

#### セキュリティ操作
```bash
# ダウンロードファイルをスキャン
python -m src.cli.main security-scan --directory ./downloads/

# 最近のダウンロードを監査
python -m src.cli.main security-audit --days 7

# セキュリティシグネチャを更新
python -m src.cli.main security-update
```

### ⚙️ 設定管理

#### 設定表示
```bash
# 現在の設定を表示
python -m src.cli.main config show

# 設定を検証
python -m src.cli.main config validate

# API接続をテスト
python -m src.cli.main config test-connection
```

#### 設定更新
```bash
# ダウンロードディレクトリを更新
python -m src.cli.main config set download.base_directory ./new_downloads/

# デバッグロギングを有効化
python -m src.cli.main config set logging.level DEBUG

# レート制限を設定
python -m src.cli.main config set api.rate_limit 0.2
```

## 🏗️ 高度な使用方法

### Python API

#### プログラマティック検索
```python
from src.core.search.advanced_search import AdvancedSearchEngine
from src.api.client import CivitAIClient
from src.data.database import DatabaseManager

# コンポーネントを初期化
client = CivitAIClient()
db = DatabaseManager()
search_engine = AdvancedSearchEngine(client, db)

# 高度な検索を実行
results = await search_engine.search(
    query="サイバーパンクスタイル",
    filters={
        "types": ["LORA", "LoCon"],
        "base_models": ["SDXL 1.0", "Pony"],
        "min_downloads": 500,
        "categories": ["style", "concept"]
    },
    limit=100
)

print(f"{len(results)}個のモデルが見つかりました")
```

#### バルク操作
```python
from src.core.bulk.download_manager import BulkDownloadManager
from src.core.performance.optimizer import PerformanceOptimizer

# 最適化されたバルクダウンローダーを作成
optimizer = PerformanceOptimizer()
bulk_manager = BulkDownloadManager(
    download_manager=download_manager,
    optimizer=optimizer,
    db_manager=db
)

# バルクジョブを作成して開始
job = await bulk_manager.create_bulk_job(
    name="スタイルコレクション",
    items=search_results,
    options={
        "batch_size": 10,
        "priority": "HIGH",
        "verify_hashes": True
    }
)

# 進行状況を監視
async for progress in bulk_manager.monitor_job(job.id):
    print(f"進行状況: {progress.completed}/{progress.total}")
```

#### 分析統合
```python
from src.core.analytics import AnalyticsCollector, AnalyticsAnalyzer

# 分析を初期化
collector = AnalyticsCollector(db_manager)
analyzer = AnalyticsAnalyzer(collector)

# カスタムレポートを生成
report = await analyzer.generate_report(
    start_time=time.time() - 2592000,  # 30日前
    end_time=time.time(),
    metrics=['downloads', 'performance', 'usage']
)

print(f"総ダウンロード数: {report.summary['downloads']['total']}")
print(f"成功率: {report.summary['downloads']['success_rate']:.1f}%")
```

## 📁 プロジェクト構成

```
civitai-downloader-v2/
├── src/                          # ソースコード
│   ├── api/                      # APIクライアント層
│   │   ├── client.py            # メインCivitAI APIクライアント
│   │   ├── auth.py              # 認証管理
│   │   └── cache.py             # レスポンスキャッシュ
│   ├── core/                    # コアビジネスロジック
│   │   ├── search/              # 検索エンジン
│   │   ├── download/            # ダウンロード管理
│   │   ├── bulk/                # バルク操作
│   │   ├── analytics/           # 分析システム
│   │   ├── security/            # セキュリティ機能
│   │   ├── performance/         # パフォーマンス最適化
│   │   └── config/              # 設定管理
│   ├── cli/                     # コマンドラインインターフェース
│   │   └── main.py              # CLIエントリーポイント
│   ├── data/                    # データ層
│   │   ├── database.py          # データベース管理
│   │   └── models/              # データモデル
│   └── ui/                      # ユーザーインターフェース
│       ├── dashboard.py         # Webダッシュボード
│       └── progress.py          # 進行状況表示
├── tests/                       # テストスイート（112テスト）
├── config/                      # 設定ファイル
├── data/                        # データベースファイル
├── docs/                        # ドキュメント
├── downloads/                   # ダウンロードされたモデル
└── logs/                        # ログファイル
```

## 🧪 テスト

### 完全テストスイートの実行
```bash
# 全テスト（112テスト）
python -m pytest tests/ -v

# 統合テストのみ
python -m pytest tests/integration/ -v

# 特定コンポーネントのテスト
python -m pytest tests/unit/test_advanced_search.py -v
python -m pytest tests/unit/test_bulk_download.py -v
python -m pytest tests/unit/test_analytics_comprehensive.py -v
```

### テストカバレッジ
```bash
# カバレッジレポートを生成
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# HTMLカバレッジレポートを表示
open htmlcov/index.html
```

## ⚙️ 設定リファレンス

### メイン設定ファイル (`config/app_config.yml`)

```yaml
# API設定
api:
  civitai_api_key: "${CIVITAI_API_KEY}"
  base_url: "https://civitai.com/api/v1"
  timeout: 30
  max_retries: 3
  rate_limit: 0.5  # 1秒あたりのリクエスト数

# ダウンロード設定  
download:
  base_directory: "./downloads"
  concurrent_downloads: 3
  chunk_size: 8192
  verify_checksums: true
  organize_by_type: true

# セキュリティ設定
security:
  enable_scanning: true
  max_file_size: 10737418240  # 10GB
  scan_timeout: 300
  require_confirmation: true
  allow_nsfw: false
  
# データベース設定
database:
  url: "sqlite:///data/civitai.db"
  connection_pool_size: 5
  enable_optimization: true

# ロギング設定
logging:
  level: "INFO"
  file: "logs/civitai-downloader.log"
  max_size_mb: 100
  backup_count: 5

# 分析設定
analytics:
  enable_collection: true
  retention_days: 90
  report_formats: ["html", "json"]
```

### 環境変数

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `CIVITAI_API_KEY` | CivitAI APIキー | *必須* |
| `CIVITAI_DOWNLOAD_DIR` | ダウンロードディレクトリ | `./downloads` |
| `CIVITAI_LOG_LEVEL` | ログレベル | `INFO` |
| `CIVITAI_DATABASE_URL` | データベースURL | `sqlite:///data/civitai.db` |

## 🔧 トラブルシューティング

### よくある問題

#### API接続問題
```bash
# API接続をテスト
python -m src.cli.main config test-connection

# APIキーの有効性をチェック
python -m src.cli.main config validate
```

#### ダウンロード問題
```bash
# ディスク容量をチェック
python -m src.cli.main health-check

# 失敗したダウンロードを再開
python -m src.cli.main download --model-id 123456 --resume

# ダウンロードキャッシュをクリア
python -m src.cli.main cache clear
```

#### パフォーマンス問題
```bash
# パフォーマンス推奨事項を取得
python -m src.cli.main analytics --type performance --show-recommendations

# データベースを最適化
python -m src.cli.main db-optimize

# 古いログをクリア
python -m src.cli.main logs clean --older-than 30d
```

### デバッグモード
```bash
# デバッグロギングを有効化
python -m src.cli.main config set logging.level DEBUG

# 詳細出力で実行
python -m src.cli.main search "テスト" --verbose --debug
```

## 🔒 セキュリティ

### セキュリティ機能
- **ファイルスキャン**: 自動マルウェア検出
- **ハッシュ検証**: SHA256/BLAKE3整合性チェック  
- **アクセス制御**: ロールベース権限
- **監査ログ**: 完全な活動追跡
- **暗号化**: 多レベルデータ保護

### セキュリティのベストプラクティス
```bash
# すべてのセキュリティ機能を有効化
python -m src.cli.main config set security.enable_scanning true
python -m src.cli.main config set security.verify_checksums true
python -m src.cli.main config set security.require_confirmation true

# セキュリティ監査を実行
python -m src.cli.main security-audit

# セキュリティ定義を更新
python -m src.cli.main security-update
```

## 📊 パフォーマンス最適化

### 自動最適化
```bash
# 適応最適化を有効化
python -m src.cli.main config set performance.optimization_mode adaptive

# パフォーマンスを監視
python -m src.cli.main metrics --component download --live
```

### 手動調整
```bash
# システムに基づいて同時ダウンロード数を調整
python -m src.cli.main config set download.concurrent_downloads 5

# 帯域幅向けに最適化
python -m src.cli.main config set download.chunk_size 16384

# データベース最適化
python -m src.cli.main db-optimize
```

## 🚀 エンタープライズ機能

### デプロイメント
```bash
# Dockerデプロイメント
docker-compose up -d

# Kubernetesデプロイメント  
kubectl apply -f deployment/k8s/
```

### 監視
```bash
# ヘルスチェックエンドポイント
curl http://localhost:8080/health

# メトリクスエンドポイント
curl http://localhost:8080/metrics
```

### バックアップ・復旧
```bash
# データベースをバックアップ
python -m src.cli.main backup --output civitai_backup_20250122.tar.gz

# バックアップから復元
python -m src.cli.main restore --input civitai_backup_20250122.tar.gz
```

## 🤝 貢献

1. **フォーク** リポジトリをフォークする
2. **作成** 機能ブランチを作成: `git checkout -b feature/amazing-feature`
3. **コミット** 変更をコミット: `git commit -m 'Add amazing feature'`
4. **プッシュ** ブランチにプッシュ: `git push origin feature/amazing-feature`
5. **提出** プルリクエストを提出

### 開発環境セットアップ
```bash
# 開発依存関係をインストール
pip install -r requirements-dev.txt

# プリコミットフックを設定
pre-commit install

# コミット前にテストを実行
python -m pytest tests/
```

## 📄 ライセンス

このプロジェクトはMITライセンスのもとでライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- 包括的なAPIを提供してくれたCivitAI
- インスピレーションとツールを提供してくれたオープンソースコミュニティ
- このプロジェクトをより良くするために貢献してくれたすべての貢献者

## 📞 サポート

- **ドキュメント**: [完全ドキュメント](docs/README.md)
- **Issue**: [GitHub Issues](https://github.com/your-org/civitai-downloader-v2/issues)
- **Discord**: [コミュニティDiscord](https://discord.gg/your-server)

---

**AI Art コミュニティのために ❤️ を込めて作成**

*最終更新: 2025年1月*