# CivitAI Downloader v2

🎯 **高性能AIモデル収集・ダウンロードシステム** - CivitAIから高品質なAIモデルを大規模収集し、カテゴリ別に整理してダウンロードするための統合ツール

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

## 📊 現在のデータベース状況

- **総モデル数**: **32,510件** (198MB SQLiteデータベース)
  - **LORA**: 32,412件
    - Style: 10,296件
    - Pose: 数千件  
    - Concept: 数千件
    - Character: 数千件
  - **Checkpoint**: 98件（Illustrious系）

## ✨ 主要機能

### 🔍 大規模データ収集システム
- **ストリーミング検索**: 数万件のモデル情報を効率的に収集
- **インテリジェントフィルタリング**: カテゴリ × タグ × モデルタイプによる高精度フィルタリング
- **Most Downloaded順ソート**: 人気度に基づいた優先度付きダウンロード
- **中間ファイル管理**: raw → filtered → processed の段階的データ処理

### ⬇️ 選択的ダウンロードシステム
- **カテゴリ別ダウンロード**: LORA（style/pose/concept/character）とCheckpoint別の管理
- **組織化されたファイル構造**: `モデルタイプ/ベースモデル/カテゴリ/[ID]モデル名/バージョン名`
- **豊富なメタデータ**: JSON形式の詳細情報と.civitai.infoファイル
- **プレビュー画像**: 各モデルの代表画像を自動ダウンロード
- **重複回避**: データベース記録による自動重複チェック機能
- **ダウンロード履歴**: 完全なダウンロード履歴とファイルパス記録

### 🛡️ Stable Diffusion WebUI連携
- **.civitai.info対応**: SD WebUI Civitai Helperとの完全互換性
- **自動プレビュー**: モデル名と同名のプレビュー画像
- **メタデータ管理**: 詳細なモデル情報をJSON形式で保存

## 🚀 クイックスタート

### 基本的な使用方法

#### 1. データ収集（検索とデータベース構築）
```bash
# LORA styleモデルを1000件収集
python -m src.cli.main search "" --types "LoRA" --categories "style" --limit 1000 --stream

# LORA poseモデルを500件収集
python -m src.cli.main search "" --types "LoRA" --categories "pose" --limit 500 --stream

# Checkpoint Illustriousモデルを100件収集
python -m src.cli.main search "" --types "Checkpoint" --base-model "Illustrious" --limit 100 --stream
```

#### 2. 選択的ダウンロード（推奨方法）
```bash
# LORA styleモデルをMost Downloaded順に100件ダウンロード
python scripts/quick_download.py --type LORA --categories style --max-models 100

# 実行前の確認（ドライラン）
python scripts/quick_download.py --type LORA --categories style --max-models 100 --dry-run

# LORA poseモデルを50件ダウンロード
python scripts/quick_download.py --type LORA --categories pose --max-models 50

# 複数カテゴリを同時に200件ダウンロード
python scripts/quick_download.py --type LORA --categories style character --max-models 200

# Checkpointモデルを20件ダウンロード
python scripts/quick_download.py --type Checkpoint --base-models Illustrious --max-models 20

# ⚡ 自動重複回避: 既にダウンロード済みのモデルは自動スキップ
# ⚡ データベース記録: 全ダウンロード履歴を自動記録・管理
```

#### 3. データベースからの一括ダウンロード
```bash
# データベース内の全モデルを一括ダウンロード
python scripts/bulk_download.py --output-dir "/path/to/download"
```

## 💻 詳細な使用方法

### 🔍 高度な検索オプション

```bash
# 複数タイプを同時検索
python -m src.cli.main search "anime" --types "LoRA" "Checkpoint" --limit 500

# NSFWコンテンツを除外
python -m src.cli.main search "character" --no-nsfw --categories "character"

# 特定のベースモデルで絞り込み
python -m src.cli.main search "" --base-model "Illustrious" --types "Checkpoint"

# 結果をJSONファイルに保存
python -m src.cli.main search "style" --output results.json --limit 100
```

### 📋 モデル情報確認

```bash
# 単一モデルのダウンロード
python -m src.cli.main download 257749 --output-dir ./models

# データベース内のモデル数確認
sqlite3 data/civitai.db "SELECT type, COUNT(*) FROM models GROUP BY type;"

# ダウンロード済みモデル確認
sqlite3 data/civitai.db "SELECT COUNT(*) FROM downloads WHERE status = 'completed';"

# 最新のダウンロード履歴確認
sqlite3 data/civitai.db "SELECT model_id, file_name, downloaded_at FROM downloads WHERE status = 'completed' ORDER BY downloaded_at DESC LIMIT 10;"
```

### ⚙️ フィルタリングとカスタマイズ

```bash
# ダウンロード間隔を調整（負荷軽減）
python scripts/quick_download.py --type LORA --categories style --max-models 10 --delay 2.0

# カスタム出力ディレクトリ
python scripts/quick_download.py --type LORA --categories style --max-models 50 --output-dir "/custom/path"

# JSONLファイルの後処理フィルタリング
python scripts/filter_jsonl.py data/intermediate/search_YYYYMMDD_HHMMSS_processed.jsonl poses
```

## 📁 出力ファイル構造

ダウンロードされたモデルは以下の構造で整理されます：

```
/Volumes/Create-Images/Civitiai-download/          # デフォルト出力ディレクトリ
├── LORA/                                         # LORAモデル
│   ├── Illustrious/                             # ベースモデル別
│   │   ├── style/                               # カテゴリ別
│   │   │   └── [11161]Cutesexyrobutts_Style/    # [ID]モデル名
│   │   │       └── v1.0/                        # バージョン別
│   │   │           ├── cutesexyrobutts_style_v1.safetensors      # モデルファイル
│   │   │           ├── cutesexyrobutts_style_v1.preview.png      # プレビュー画像
│   │   │           ├── cutesexyrobutts_style_v1.civitai.info     # SD WebUI用情報
│   │   │           └── metadata.json                             # 詳細メタデータ
│   │   ├── pose/                                # ポーズ系LORA
│   │   ├── concept/                             # コンセプト系LORA
│   │   └── character/                           # キャラクター系LORA
│   └── Pony/                                    # 他のベースモデル（将来対応）
└── Checkpoint/                                   # Checkpointモデル
    └── Illustrious/                             # ベースモデル別
        └── basemodel/                           # カテゴリ別
            └── [32022]Mistoon_Sapphire/         # [ID]モデル名
                └── v2.1/                        # バージョン別
                    ├── mistoon_sapphire_v2.1.safetensors        # モデルファイル
                    ├── mistoon_sapphire_v2.1.preview.png        # プレビュー画像
                    ├── mistoon_sapphire_v2.1.civitai.info       # SD WebUI用情報
                    └── metadata.json                             # 詳細メタデータ
```

## 📁 プロジェクト構造

```
civitai-downloader-v2/
├── src/                              # ソースコード
│   ├── cli/main.py                   # メインCLI
│   ├── core/                         # コア機能
│   │   ├── search/search_engine.py   # 検索エンジン
│   │   ├── download/manager.py       # ダウンロード管理
│   │   └── config/system_config.py  # 設定管理
│   ├── data/database.py              # データベース管理
│   ├── api/client.py                 # CivitAI API クライアント
│   └── utils/                        # ユーティリティ
├── data/                             # データファイル
│   ├── civitai.db                    # メインデータベース (32,510件)
│   └── intermediate/                 # 中間ファイル
│       ├── *_raw.jsonl              # API生データ
│       ├── *_filtered.jsonl         # フィルタリング済み
│       └── *_processed.jsonl        # 処理済みデータ
├── logs/civitai_debug.log            # デバッグログ
├── scripts/                          # ユーティリティスクリプト
│   ├── quick_download.py             # 選択的ダウンロード（推奨）
│   ├── bulk_download.py              # 一括ダウンロード
│   ├── import_to_db.py               # DBインポート
│   ├── filter_jsonl.py               # 後処理フィルタリング
│   └── README.md                     # スクリプト説明
├── archive/                          # 旧版ファイル保管
│   ├── legacy-data/                  # 古いデータファイル
│   ├── legacy-tests/                 # 古いテストファイル
│   └── README.md                     # アーカイブ説明
└── README.md                         # このファイル
```

## 🔧 設定とカスタマイズ

### 基本設定

```bash
# API設定（オプション - 高レート制限が必要な場合）
export CIVITAI_API_KEY="your_api_key_here"

# カスタム出力ディレクトリ
export DEFAULT_OUTPUT_DIR="/path/to/your/download/directory"
```

### 設定ファイル

設定は `deployment/config/app_config.yml` で管理：

```yaml
download:
  output_directory: "/Volumes/Create-Images/Civitiai-download"
  max_concurrent_downloads: 3
  delay_between_downloads: 1.0

search:
  default_limit: 100
  max_stream_limit: 50000
  enable_html_cleanup: true

api:
  timeout: 30
  max_retries: 3
```

### 検索フィルタオプション

```bash
# モデルタイプ指定
--types "LoRA"                     # LORA のみ
--types "Checkpoint"               # Checkpoint のみ
--types "LoRA" "Checkpoint"        # 複数タイプ

# カテゴリフィルタ
--categories "style"               # スタイル系のみ
--categories "pose"                # ポーズ系のみ
--categories "style" "character"   # 複数カテゴリ

# ベースモデルフィルタ
--base-model "Illustrious"         # Illustrious系のみ

# ソート・制限
--sort "Most Downloaded"           # 人気順
--limit 1000                       # 結果数制限
--stream                           # ストリーミング検索（大量データ用）

# NSFW設定
--nsfw                             # NSFWを含める
--no-nsfw                          # NSFWを除外（デフォルト）
```

## 🔄 データフロー

1. **検索・収集フェーズ**: CivitAI API → raw.jsonl → filtered.jsonl → processed.jsonl
2. **データベース格納**: processed.jsonl → SQLite DB (civitai.db) 
3. **選択的ダウンロード**: DB query → カテゴリフィルタリング → Most Downloaded順ソート → 重複チェック → ダウンロード実行 → DB記録

## 📊 パフォーマンス最適化

### 大規模ダウンロード時の推奨設定

```bash
# 並行度とレート制限の調整
python scripts/quick_download.py --type LORA --categories style --max-models 1000 --delay 1.5

# バッチサイズ調整でメモリ使用量制御
python -m src.cli.main search "" --types "LoRA" --limit 10000 --stream --batch-size 100
```

### システムリソース管理

- **メモリ使用量**: ストリーミング検索により大規模データセットでも安定動作
- **ディスク容量**: モデルファイル50MB-2GB、十分な空き容量を確保
- **ネットワーク**: 大量ダウンロード時はdelay調整で負荷分散

## 📝 ログとデバッグ

すべてのログは `logs/civitai_debug.log` に出力：

```bash
# リアルタイムログ監視
tail -f logs/civitai_debug.log

# エラーログのみ表示
grep "ERROR" logs/civitai_debug.log

# デバッグ情報付きで実行
python scripts/quick_download.py --type LORA --categories style --max-models 5 --dry-run
```

## 🗄️ データベース管理

SQLiteデータベース（`data/civitai.db`）の管理：

```bash
# データベース状況確認
sqlite3 data/civitai.db "SELECT type, COUNT(*) FROM models GROUP BY type;"

# ダウンロード状況確認
sqlite3 data/civitai.db "SELECT status, COUNT(*) FROM downloads GROUP BY status;"

# 特定カテゴリの件数確認
sqlite3 data/civitai.db "SELECT COUNT(*) FROM models WHERE type = 'LORA' AND raw_data LIKE '%style%';"

# ダウンロード履歴の詳細確認
sqlite3 data/civitai.db "SELECT d.model_id, m.name, d.file_name, d.downloaded_at FROM downloads d JOIN models m ON d.model_id = m.id WHERE d.status = 'completed' ORDER BY d.downloaded_at DESC LIMIT 20;"

# 整合性チェック
sqlite3 data/civitai.db "PRAGMA integrity_check;"

# バックアップ作成
cp data/civitai.db data/civitai_backup_$(date +%Y%m%d).db
```

## ⚡ クイックリファレンス

### よく使うコマンド集

```bash
# 【データ収集】新しいカテゴリを収集
python -m src.cli.main search "" --types "LoRA" --categories "concept" --limit 1000 --stream

# 【確認】ダウンロード対象をチェック
python scripts/quick_download.py --type LORA --categories style --max-models 20 --dry-run

# 【実行】実際のダウンロード（重複自動回避）
python scripts/quick_download.py --type LORA --categories style --max-models 100

# 【管理】データベース状況確認
sqlite3 data/civitai.db "SELECT type, COUNT(*) FROM models GROUP BY type;"

# 【履歴】ダウンロード完了状況確認
sqlite3 data/civitai.db "SELECT COUNT(*) FROM downloads WHERE status = 'completed';"
```

### 推奨ワークフロー

1. **段階的収集**: 少数でテスト → 大量収集
2. **カテゴリ別管理**: 用途に応じてカテゴリを分けて収集・ダウンロード
3. **重複回避活用**: 大量ダウンロード時も既存チェックで効率的実行
4. **定期実行**: cron等で定期的に新しいモデルを自動収集
5. **履歴管理**: データベースでダウンロード状況を継続的に追跡
6. **バックアップ**: 重要なデータベースは定期的にバックアップ

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. ダウンロードが失敗する
```bash
# ネットワーク接続確認
ping civitai.com

# ダウンロード間隔を長くして再試行
python scripts/quick_download.py --type LORA --categories style --max-models 10 --delay 3.0

# ログで詳細エラーを確認
tail -f logs/civitai_debug.log
```

#### 2. データベースの不整合
```bash
# データベース整合性チェック
sqlite3 data/civitai.db "PRAGMA integrity_check;"

# 必要に応じてバックアップから復旧
cp data/civitai_backup_20250729.db data/civitai.db

# 重複チェック
sqlite3 data/civitai.db "SELECT id, COUNT(*) FROM models GROUP BY id HAVING COUNT(*) > 1;"
```

#### 3. 検索結果が期待と異なる
```bash
# ドライランで対象を確認
python scripts/quick_download.py --type LORA --categories style --max-models 5 --dry-run

# APIパラメータが正しいかデバッグ
python -m src.cli.main search "test" --types "LoRA" --categories "style" --limit 5
```

#### 4. メモリ不足エラー
```bash
# バッチサイズを小さくする
python -m src.cli.main search "" --types "LoRA" --limit 1000 --stream --batch-size 50

# 並行ダウンロード数を減らす
python scripts/quick_download.py --type LORA --categories style --max-models 100 --delay 2.0
```

### エラーメッセージ対応

| エラー | 原因 | 解決方法 |
|-------|------|----------|
| `JSONDecodeError` | データベースのraw_data形式問題 | `ast.literal_eval`を使用（修正済み） |
| `Connection timeout` | ネットワークまたはAPI制限 | delay増加、API Key設定 |
| `File not found` | 出力ディレクトリ未作成 | 自動作成されるが、権限確認 |
| `Database locked` | 複数プロセス同時実行 | プロセスを一つずつ実行 |
| `Already downloaded, skipping` | 重複ダウンロード検出 | 正常動作、効率的な重複回避 |

## 💡 Tips & Tricks

### 効率的な使い方

1. **段階的アプローチ**: まず10-20件でテストしてから大量ダウンロード
2. **カテゴリ別収集**: 用途を明確にしてカテゴリを分けて管理
3. **Most Downloaded活用**: 人気モデルから優先的にダウンロード
4. **重複回避の活用**: 大量実行時も既存モデルは自動スキップで高速化
5. **履歴管理**: データベースクエリでダウンロード状況を定期確認
6. **定期実行**: 新しいモデルを自動で収集する仕組みを構築

### パフォーマンスチューニング

```bash
# 高速大量収集（ネットワーク帯域に注意）
python scripts/quick_download.py --type LORA --categories style --max-models 500 --delay 0.5

# 安定重視（サーバ負荷軽減）
python scripts/quick_download.py --type LORA --categories style --max-models 100 --delay 2.0

# バランス型（推奨設定）
python scripts/quick_download.py --type LORA --categories style --max-models 200 --delay 1.0
```

## 🎯 今後の拡張予定

- [ ] **NoobAI対応**: NoobAIベースモデルのサポート追加
- [ ] **WebUI**: ブラウザベースの管理インターフェース
- [ ] **自動更新**: 新規モデルの自動検出・ダウンロード
- [ ] **統計ダッシュボード**: ダウンロード統計とトレンド分析
- [ ] **カスタムフィルタ**: ユーザー定義の高度なフィルタリングルール
- [ ] **品質評価**: モデル品質の自動評価システム

## 🔗 関連リンク

- **CivitAI**: https://civitai.com/ - AIモデルプラットフォーム
- **Stable Diffusion WebUI**: https://github.com/AUTOMATIC1111/stable-diffusion-webui
- **CivitAI Helper**: https://github.com/butaixianran/Stable-Diffusion-Webui-Civitai-Helper

## 📞 サポート

問題や質問がある場合は、以下の情報とともにお問い合わせください：

1. **使用コマンド**: 実行したコマンドライン
2. **エラーログ**: `logs/civitai_debug.log` の関連部分
3. **環境情報**: OS、Python バージョン、データベースサイズ

---

**🎨 Happy AI Model Collecting! ✨**

*高品質なAIモデルの収集とダウンロードをお楽しみください！*