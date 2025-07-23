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

### 🔑 APIキーの設定

**推奨方法（環境変数）**：
```bash
# 環境変数でAPIキーを設定（最もセキュア）
export CIVITAI_API_KEY="your_actual_api_key_here"
```

**代替方法（設定ファイル）**：
```bash
# 設定ファイルを編集
nano config/app_config.yml
```

**設定の優先順位**：
1. **環境変数** `CIVITAI_API_KEY` （推奨・最優先）
2. **設定ファイル** `config/app_config.yml` の `civitai_api_key`
3. **.env ファイル** `.env` の `CIVITAI_API_KEY`

**セキュリティ上の理由から環境変数での設定を強く推奨します**

### 3. 基本的な使用方法

```bash
# モデルを検索して表示（検索語は英語で）
python -m src.cli.main search "anime character" --limit 10

# 特定のモデルをダウンロード
python -m src.cli.main download --model-id 12345

# モデル情報を表示
python -m src.cli.main info 12345

# ローカルファイルをスキャン
python -m src.cli.main scan path/to/model.safetensors

# 設定を表示
python -m src.cli.main config --list
```

## 📖 完全使用ガイド

> **📝 重要な注意事項**:
> - **検索キーワード**: 英語で入力してください（CivitAI APIは英語検索に最適化）
> - **ページネーション対応**: `--limit`で指定した件数まで複数ページから自動取得します（例：250件指定で4回のAPIリクエスト）
> - **API制限**: 1ページあたり最大100件、レート制限に自動適応します

### 🔍 検索操作

#### 出力フォーマット説明

| フォーマット | 説明 | 用途 | 出力例 |
|-------------|------|------|--------|
| **table** | テーブル形式（デフォルト） | 人間が読みやすい形式 | `12345    Model Name                 LoRA      1234` |
| **simple** | ID:名前の最小形式 | スクリプト処理や簡単な一覧 | `12345: Model Name` |
| **json** | 完全なJSONデータ | プログラム処理や詳細分析 | `{"id": 12345, "name": "...", ...}` |

#### 利用可能なモデルタイプ (`--types`)

| タイプ名 | 説明 | 用途 | 例 |
|---------|------|------|-----|
| **Checkpoint** | 大容量ベースモデル | メイン生成モデル | Stable Diffusion基盤 |
| **LORA** | 軽量追加学習モデル | スタイル・キャラ追加 | アニメスタイル、特定キャラ |
| **LoCon** | LoRA系軽量モデル | スタイル調整 | 新しいLoRA形式 |
| **TextualInversion** | Embeddingモデル | プロンプト拡張 | 顔・表情の微調整 |
| **VAE** | 画像エンコーダー | 品質向上 | 色彩・詳細改善 |
| **Upscaler** | 高解像度化 | 画像拡大 | 解像度向上ツール |
| **Other** | その他モデル | 特殊用途 | カスタムツール |
| **Workflows** | 作業手順 | 生成手順共有 | ComfyUIワークフロー |

**注意**: 
- モデルタイプ名は**大文字小文字を区別**します（`LORA` ○、`lora` ×）
- 複数タイプは`"Checkpoint,LORA"`のようにカンマ区切りで指定可能

#### 利用可能なソートオプション (`--sort`)

| ソートオプション | 説明 | 用途 |
|----------------|------|------|
| **Most Downloaded** | ダウンロード数順（デフォルト） | 人気の高いモデルを探す |
| **Highest Rated** | 評価の高い順 | 品質の高いモデルを探す |
| **Newest** | 新着順 | 最新のモデルを探す |
| **Oldest** | 古い順 | クラシックなモデルを探す |
| **Most Liked** | いいね数順 | コミュニティに評価されたモデル |
| **Most Discussed** | 議論数順 | 話題になっているモデル |
| **Most Collected** | コレクション数順 | よく保存されているモデル |
| **Most Images** | 画像数順 | サンプル画像が豊富なモデル |

#### 基本検索
```bash
# クエリで検索（検索語は英語）
python -m src.cli.main search "cyberpunk style" --limit 20

# モデルタイプでフィルタ（カンマ区切りまたは複数回指定で複数指定可能）
python -m src.cli.main search "character" --types "Checkpoint,LORA" --limit 20

# 利用可能なモデルタイプ一覧（大文字小文字区別あり）
python -m src.cli.main search "anime" --types LORA --limit 10              # LoRAモデルのみ
python -m src.cli.main search "style" --types Checkpoint --limit 10         # Checkpointのみ  
python -m src.cli.main search "face" --types TextualInversion --limit 5     # Embeddingのみ
python -m src.cli.main search "character" --types "LORA,LoCon" --limit 15     # 複数タイプ指定
python -m src.cli.main search "model" --types "Checkpoint,VAE,LORA" --limit 20  # 3つのタイプ

# ベースモデルで絞り込み（Checkpoint向け）
python -m src.cli.main search "anime" --types Checkpoint --base-model "Pony Diffusion XL" --limit 10
python -m src.cli.main search "realistic" --types Checkpoint --base-model "SDXL 1.0" --limit 10

# 複数キーワードで検索
python -m src.cli.main search "anime portrait" --limit 15

# 検索結果をテーブル形式で表示（デフォルト）
python -m src.cli.main search "landscape" --limit 15 --format table

# シンプル形式で表示（ID: 名前のみ）
python -m src.cli.main search "portrait" --limit 5 --format simple

# NSFW含む検索
python -m src.cli.main search "style" --nsfw --limit 20

# 大量件数での検索（ページネーション対応）
python -m src.cli.main search "anime" --limit 250 --format table

# ソート順を指定して検索
python -m src.cli.main search "anime" --sort "Highest Rated" --limit 20       # 評価の高い順
python -m src.cli.main search "character" --sort "Newest" --limit 15          # 新着順
python -m src.cli.main search "style" --sort "Most Liked" --limit 10          # いいね数順
python -m src.cli.main search "portrait" --sort "Most Images" --limit 12      # 画像数順
```

#### 検索結果のエクスポート
```bash
# ファイルに保存（--outputでフォーマット指定可能）
python -m src.cli.main search "mecha" --limit 20 --output mecha_models.json          # JSON形式（デフォルト）
python -m src.cli.main search "anime" --limit 50 --format simple --output anime_list.txt  # シンプル形式
python -m src.cli.main search "style" --limit 30 --format table --output style_table.txt  # テーブル形式

# 自動的にdownloads/フォルダに保存される（ディレクトリ指定なしの場合）
python -m src.cli.main search "" --types Checkpoint --base-model "Pony Diffusion XL" --limit 100 --format simple --output pony_checkpoints.txt
# → downloads/pony_checkpoints.txt に保存

# カスタムパスを指定
python -m src.cli.main search "character" --limit 50 --format simple --output ./results/characters.txt

# 出力形式の比較例（画面表示）
python -m src.cli.main search "mecha" --limit 3 --format simple   # 12345: Mecha Robot LoRA
python -m src.cli.main search "mecha" --limit 3 --format table    # テーブル形式（ID、名前、タイプ、DL数）
python -m src.cli.main search "mecha" --limit 3 --format json     # 完全なJSON（全フィールド）
```

### 📥 ダウンロード操作

#### 単体ダウンロード
```bash
# モデルIDでダウンロード（デフォルト：./downloads）
python -m src.cli.main download 123456

# カスタムディレクトリにダウンロード
python -m src.cli.main download 123456 --output-dir ./my_models

# ファイル名も指定
python -m src.cli.main download 123456 --output-dir ./checkpoints --filename "my_anime_model.safetensors"

# セキュリティチェック付きでダウンロード
python -m src.cli.main download 123456 --output-dir ./safe_models --verify --scan-security

# モデル情報を詳しく表示
python -m src.cli.main info 123456

# モデル情報を詳細表示してからダウンロード
python -m src.cli.main info 123456 --detailed
python -m src.cli.main download 123456 --output-dir ./downloads/anime
```

#### バルクダウンロード（大量モデル一括処理）

```bash
# 検索結果をJSONで保存してからバルクダウンロード
python -m src.cli.main search "anime style" --limit 50 --output anime_models.json
python -m src.cli.main bulk-download --input anime_models.json

# シンプル形式（ID: Name）のテキストファイルからもダウンロード可能
python -m src.cli.main search "" --types Checkpoint --base-model "Pony Diffusion XL" --limit 30 --format simple --output pony_list.txt
python -m src.cli.main bulk-download --input pony_list.txt

# カスタムディレクトリへバルクダウンロード
python -m src.cli.main bulk-download --input anime_models.json --output-dir ./bulk_downloads/anime

# バルクダウンロードの詳細オプション
python -m src.cli.main bulk-download \
  --input models.json \
  --output-dir ./organized_downloads \
  --batch-size 5 \
  --priority HIGH \
  --verify-hashes \
  --scan-security \
  --job-name "アニメモデル収集"

# 対応する入力形式
# 1. JSON形式（searchコマンドの出力）
# 2. シンプル形式（ID: Name）
# 3. IDのみのテキスト（1行1ID）

# 失敗したダウンロードを再実行
python -m src.cli.main bulk-retry --job-id bulk_001

# バルクジョブ一覧表示
python -m src.cli.main bulk-list

# 特定ジョブの詳細情報
python -m src.cli.main bulk-info --job-id bulk_001
```

#### フォルダ整理パターン例
```bash
# タイプ別フォルダ整理（--organize-by-type使用時）
downloads/
├── Checkpoint/        # Checkpointモデル
├── LORA/             # LoRAファイル
├── LoCon/            # LoConファイル
├── Textual_Inversion/ # Embeddingファイル
└── VAE/              # VAEファイル

# 手動でのプロジェクト別整理例
python -m src.cli.main bulk-download --input anime_chars.json --output-dir "./projects/anime_characters"
python -m src.cli.main bulk-download --input landscapes.json --output-dir "./projects/landscapes"  
python -m src.cli.main bulk-download --input portraits.json --output-dir "./projects/portraits"

# 日付別整理
python -m src.cli.main bulk-download --input daily_picks.json --output-dir "./downloads/$(date +%Y%m%d)"
```

#### ファイル管理・セキュリティ
```bash
# ローカルファイルをスキャン
python -m src.cli.main scan ./downloads/model.safetensors

# 詳細なスキャン結果を表示
python -m src.cli.main scan ./downloads/model.safetensors --detailed

# ダウンロードディレクトリの全ファイルをスキャン
find ./downloads -name "*.safetensors" -exec python -m src.cli.main scan {} \;
```

#### 設定管理
```bash
# 現在の設定を表示
python -m src.cli.main config --list

# 特定の設定値を取得
python -m src.cli.main config --get api.base_url

# 設定値を変更
python -m src.cli.main config --set "download.max_concurrent=5"

# 設定ファイルを編集
python -m src.cli.main config --edit
```

### 🔧 システム管理

#### バージョン・システム情報
```bash
# バージョン情報を表示
python -m src.cli.main version

# システム情報（詳細）
python -m src.cli.main version --detailed

# 利用可能なコマンド一覧
python -m src.cli.main --help
```

#### 実用的な使用例
```bash
# 人気のアニメスタイルモデルを検索
python -m src.cli.main search "anime style" --sort "Most Downloaded" --limit 10 --format table

# ポートレート用モデルを探す
python -m src.cli.main search "portrait" --types LORA --sort "Highest Rated" --limit 5

# 特定モデルの詳細情報を取得
python -m src.cli.main info 1800398

# 検索結果をJSONで保存
python -m src.cli.main search "cyberpunk" --limit 20 --output cyberpunk_models.json
```

### 📚 実践的なワークフロー例

#### 1. 新しいプロジェクト用にモデルを探す
```bash
# 1. まずアニメスタイルのCheckpointモデルを検索
python -m src.cli.main search "anime checkpoint" --types Checkpoint --limit 10 --format table

# 2. 気になるモデルの詳細を確認
python -m src.cli.main info 1800398

# 3. モデルをダウンロード
python -m src.cli.main download 1800398

# 4. ダウンロードしたファイルをスキャン
python -m src.cli.main scan downloads/model_name.safetensors
```

#### 2. 特定スタイル用のLoRAを収集（バルク処理）
```bash
# 1. ポートレート用のLoRAを検索
python -m src.cli.main search "portrait style" --types LORA --limit 30 --format table

# 2. 結果をJSONで保存
python -m src.cli.main search "portrait style" --types LORA --limit 30 --output portrait_loras.json

# 3. バルクダウンロードで一括取得（JSON形式）
python -m src.cli.main bulk-download --input portrait_loras.json --batch-size 5

# または、シンプル形式で保存してから
python -m src.cli.main search "portrait style" --types LORA --limit 30 --format simple --output portrait_simple.txt
python -m src.cli.main bulk-download --input portrait_simple.txt
```

#### 3. システムメンテナンス
```bash
# 1. 設定の確認
python -m src.cli.main config --list

# 2. ダウンロードディレクトリの確認
ls -la downloads/

# 3. ファイルの整合性チェック
find downloads/ -name "*.safetensors" | head -5 | while read file; do 
    echo "Scanning: $file"
    python -m src.cli.main scan "$file"
done

# 4. 設定の調整
python -m src.cli.main config --set "download.max_concurrent=3"

# 5. データベースのバックアップ
cp -r data/ data_backup_$(date +%Y%m%d)/

# 6. ログファイルのクリーンアップ（30日以上前のログを削除）
find logs/ -name "*.log" -mtime +30 -delete
```

#### 4. 特定ベースモデルのCheckpoint検索

**新機能**: `--base-model`オプションが追加されました！特定のベースモデルに基づくCheckpointを絞り込めます：

```bash
# ベースモデル指定での検索（--base-modelオプション使用）
python -m src.cli.main search "" --types Checkpoint --base-model "Pony" --limit 20
python -m src.cli.main search "" --types Checkpoint --base-model "SDXL 1.0" --limit 20
python -m src.cli.main search "" --types Checkpoint --base-model "SD 1.5" --limit 20

# 注意：ベースモデルフィルターは結果を大幅に制限します
# まずbaseModelなしで検索し、興味のあるモデルのbaseModel値を確認することを推奨
python -m src.cli.main search "" --types Checkpoint --limit 20  # すべてのCheckpoint
python -m src.cli.main search "realistic" --types Checkpoint --limit 15  # realistic系Checkpoint

# 主要なベースモデル名の例（APIから実際に確認されたもの）
# - "Pony" (Pony Diffusion XL系)
# - "SDXL 1.0" (SDXL系)
# - "SD 1.5" (Stable Diffusion 1.5系)  
# - "Illustrious" (IllustriousXL系)
# - "Flux.1 D" / "Flux.1 S" (Flux系)

# 実用例：まず一般検索でbaseModel値を確認
python -m src.cli.main search "" --types Checkpoint --limit 5 --format table
# 興味のあるモデルのbaseModel値を確認してから絞り込み検索
```

**注意**: 
- `--base-model`フィルターは結果を大幅に制限するため、まず一般検索でbaseModel値を確認することを推奨
- ベースモデル名はCivitAI APIの正確な名称と一致する必要があります（"Pony"、"SDXL 1.0"、"SD 1.5"など）
- 検索クエリとベースモデルフィルターの組み合わせは結果がゼロになる場合があります

#### 5. 大量モデル収集プロジェクト
```bash
# 1. テーマ別に大量検索（複数回実行）
python -m src.cli.main search "anime character" --limit 100 --output anime_chars.json
python -m src.cli.main search "fantasy style" --limit 100 --output fantasy_styles.json  
python -m src.cli.main search "cyberpunk" --limit 100 --output cyberpunk.json

# 2. 各テーマをバルクダウンロード
python -m src.cli.main bulk-download --input anime_chars.json --priority HIGH --batch-size 10
python -m src.cli.main bulk-download --input fantasy_styles.json --priority MEDIUM
python -m src.cli.main bulk-download --input cyberpunk.json --priority LOW

# 3. 全バルクジョブの状況確認
python -m src.cli.main bulk-list

# 4. 失敗したジョブがあれば再実行
python -m src.cli.main bulk-retry --job-id bulk_002
python -m src.cli.main bulk-retry --job-id bulk_003

# 5. 完了したファイル一覧とセキュリティチェック
find downloads/ -name "*.safetensors" | wc -l  # ダウンロード済みファイル数
python -m src.cli.main bulk-info --job-id bulk_001  # 詳細レポート
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
│   ├── app_config.yml           # メイン設定ファイル
│   └── app_config.yml.example   # 設定ファイルテンプレート
├── data/                        # データベースファイル（自動作成）
│   ├── civitai.db              # メインデータベース（履歴・キャッシュ）
│   ├── analytics.db            # 分析データ・統計情報
│   └── civitai_downloader.db   # システム設定・状態管理
├── downloads/                   # ダウンロードされたモデル（自動作成）
│   ├── models/                  # モデルファイル保存先
│   └── temp/                    # 一時ファイル
├── logs/                        # ログファイル（自動作成）
│   └── civitai-downloader.log  # アプリケーションログ
└── docs/                        # ドキュメント
```

### 📂 各ディレクトリの役割

| ディレクトリ | 説明 | 自動作成 | 内容例 |
|------------|------|----------|--------|
| **config/** | 設定ファイル | ❌ | app_config.yml（手動作成必要） |
| **data/** | データベース | ✅ | 検索履歴、ダウンロード記録、分析データ |
| **downloads/** | モデル保存先 | ✅ | .safetensors、.ckpt等のモデルファイル |
| **logs/** | ログファイル | ✅ | エラーログ、アクセスログ、デバッグ情報 |

**注意**: `data/`、`downloads/`、`logs/`ディレクトリは初回実行時に自動作成されます。

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