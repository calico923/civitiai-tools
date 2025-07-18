# CivitAI Model Downloader

CivitAI.comからAIモデルを検索・ダウンロードするためのクロスプラットフォーム対応コマンドラインツールです。

## 機能

- 🔍 **高度な検索機能** - モデルタイプ、タグ、ベースモデルによる詳細フィルタリング
- 📥 **進捗追跡ダウンロード** - リアルタイム進捗表示とレジューム機能
- 🖼️ **プレビュー機能** - ダウンロード前にモデル画像とメタデータを確認
- 📁 **自動整理** - モデルタイプとベースモデル別の自動フォルダ分け
- 💾 **メタデータ保存** - ダウンロード履歴とモデル情報の永続化
- 🌍 **クロスプラットフォーム** - Windows、macOS、Linux対応
- ⚡ **非同期処理** - 高速なダウンロードとAPI通信
- 🏷️ **ライセンス情報** - 商用利用可否などの詳細なライセンス表示
- 🗄️ **ローカル管理** - SQLiteベースのメタデータ管理とバックアップ機能

## システム要件

- Python 3.8以上
- 対応OS: Windows、macOS、Linux

## インストール

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 開発版の場合
pip install -e .
```

## 基本的な使い方

### 1. モデル検索

```bash
# 基本検索
./civitai search "anime"

# 詳細フィルタリング
./civitai search "anime" --type LORA --base-model "Illustrious" --sort "Most Downloaded"

# 複数条件での検索（タグとカテゴリで絞り込み）
./civitai search --tag anime --tag style --category character --limit 50

# 注: もしタグの値がコマンドライン引数として正しく認識されない場合は、
# クエリパラメータとして検索することもできます
./civitai search "anime style character" --limit 50
```

### 2. モデル詳細表示

```bash
# 基本情報表示
./civitai show 123456

# プレビュー画像付き表示
./civitai show 123456 --images

# ライセンス情報表示
./civitai show 123456 --license

# プレビュー画像をダウンロード
./civitai show 123456 --download-images --image-size 1024
```

### 3. モデル比較

```bash
# 複数モデルの比較
./civitai compare 123456 789012 345678

# 特定バージョンでの比較
./civitai compare 123456 789012 --version 123456:v2.0 --version 789012:v1.5
```

### 4. モデルダウンロード

```bash
# 基本ダウンロード
./civitai download 123456

# 特定バージョンをダウンロード
./civitai download 123456 --version "v2.0"

# ダウンロード先を指定
./civitai download 123456 --path "/path/to/models"

# 全ファイルをダウンロード
./civitai download 123456 --all-files

# 特定ファイルのみダウンロード
./civitai download 123456 --file-index 0
```

### 5. ダウンロード履歴の表示

```bash
# 最近のダウンロード履歴を表示
./civitai list

# 表示件数を指定
./civitai list --limit 20

# モデルタイプでフィルター
./civitai list --type LORA

# ソート順を指定（date/name/size）
./civitai list --sort name
```

### 6. 設定管理

```bash
# 現在の設定を表示
./civitai config show

# ダウンロードパスを設定
./civitai config set download_path "/path/to/models"

# APIキーを設定
./civitai config set api_key "your-api-key"

# 設定をリセット
./civitai config reset
```

### 7. ローカルストレージ管理

```bash
# ストレージ統計表示
./civitai storage stats

# モデル検索（ローカル）
./civitai storage find 123456
./civitai storage search-local "anime"

# 最近ダウンロードしたモデル
./civitai storage recent --limit 10

# ストレージクリーンアップ
./civitai storage cleanup

# メタデータのエクスポート/インポート
./civitai storage export backup.json
./civitai storage import-metadata backup.json

# バックアップ管理
./civitai storage backup --name "my-backup"
./civitai storage backups
./civitai storage restore backup_20250117_120000.json
```

## 高度な検索オプション

### モデルタイプ（大文字小文字は区別されません）
- `CHECKPOINT` - メインモデル
- `LORA` - 軽量アダプター
- `LOCON` - LoCon (LyCORIS系)
- `LYCORIS` - LyCORIS
- `TEXTUAL_INVERSION` - テキスト埋め込み（Embedding）
- `HYPERNETWORK` - ハイパーネットワーク
- `AESTHETIC_GRADIENT` - Aesthetic Gradient
- `CONTROLNET` - コントロールネット
- `POSES` - ポーズモデル
- `WILDCARDS` - ワイルドカード
- `OTHER` - その他

### ベースモデル
- `Illustrious` - 最新アニメモデル
- `Pony` - Pony Diffusion V6 XL
- `SDXL 1.0` - Stable Diffusion XL
- `NoobAI` - Illustrious派生
- `SD 1.5` - Stable Diffusion 1.5
- `Animagine` - アニメ特化モデル

### ソート順序
- `Highest Rated` - 評価順
- `Most Downloaded` - ダウンロード数順
- `Most Liked` - いいね数順
- `Newest` - 新しい順
- `Most Discussed` - 議論が活発な順
- `Most Collected` - コレクション数順
- `Most Buzz` - 話題性順
- `Most Images` - 画像数順
- `Oldest` - 古い順

### カテゴリ（大文字小文字は区別されません）
- `CHARACTER` - キャラクター
- `STYLE` - スタイル
- `CONCEPT` - コンセプト
- `CLOTHING` - 服装
- `TOOL` - ツール
- `BUILDING` - 建物
- `VEHICLE` - 乗り物
- `ANIMAL` - 動物
- `BACKGROUND` - 背景

### 期間フィルタ
- `AllTime` - 全期間
- `Year` - 年間
- `Month` - 月間
- `Week` - 週間
- `Day` - 日間

## 設定ファイル

設定はプラットフォーム固有の場所に保存されます：

- **Windows**: `%APPDATA%\civitai-downloader\config.json`
- **macOS**: `~/Library/Application Support/civitai-downloader/config.json`
- **Linux**: `~/.config/civitai-downloader/config.json`

### 主要設定項目

```json
{
  "api_key": null,
  "api_base_url": "https://civitai.com/api/v1",
  "download_path": "~/CivitAI-Models",
  "concurrent_downloads": 1,
  "max_concurrent_downloads": 3,
  "resume_downloads": true,
  "verify_checksums": true,
  "default_limit": 20,
  "default_sort": "Highest Rated",
  "show_nsfw": false,
  "organize_by_type": true,
  "organize_by_base_model": true,
  "save_metadata": true
}
```

## 使用例

### アニメ系LoRAの検索とダウンロード

```bash
# アニメスタイルのLoRAを検索（大文字小文字は自由）
./civitai search --type lora --tag anime --tag style --base-model Illustrious --limit 20

# 特定モデルの詳細確認
./civitai show 123456 --images --license

# ダウンロード
./civitai download 123456 --path "~/Models/LORA/Anime"

# ダウンロード履歴を確認
./civitai list --type LORA --limit 10
```

### 商用利用可能なモデルの検索

```bash
# 商用利用可能なCheckpointを検索
./civitai search --type Checkpoint --commercial --sort "Most Downloaded"

# ライセンス詳細を確認
./civitai show 123456 --license
```

### バッチダウンロードワークフロー

```bash
# 複数モデルを比較
./civitai compare 123456 789012 345678

# 選択したモデルをダウンロード
./civitai download 123456 --all-files
./civitai download 789012 --version "v2.0"

# ダウンロード履歴確認
./civitai storage recent
```

## 注意事項

### 大文字小文字の扱い
- モデルタイプ、カテゴリ、期間フィルターは大文字小文字を区別しません
- 例：`--type lora`、`--type LORA`、`--type LoRa` はすべて同じ

### エラーメッセージ
- 無効な値を入力した場合、有効な選択肢の一覧が表示されます
- 例：
  ```
  ❌ Error: 'embedding' is not a valid model type
  Valid types: CHECKPOINT, TEXTUAL_INVERSION, HYPERNETWORK, AESTHETIC_GRADIENT, LORA, LOCON, LYCORIS, CONTROLNET, POSES, WILDCARDS, OTHER
  ```

### APIキーの設定
- CivitAIのAPIキーが必要です（無料で取得可能）
- 環境変数 `CIVITAI_API_KEY` に設定するか、`config set` コマンドで設定してください

## トラブルシューティング

### よくある問題

1. **ダウンロードが失敗する**
   ```bash
   # 設定確認
   ./civitai config show
   
   # ディスク容量確認
   ./civitai storage stats
   
   # 再試行
   ./civitai download 123456 --no-progress
   ```

2. **検索結果が表示されない**
   ```bash
   # APIキー設定確認
   ./civitai config set api_key "your-api-key"
   
   # ネットワーク接続確認
   ./civitai search --limit 5
   ```

3. **設定がおかしくなった**
   ```bash
   # 設定リセット
   ./civitai config reset
   ```

### ログとデバッグ

```bash
# 詳細なエラー情報を表示
python -m civitai_downloader.cli search "test" --verbose

# テスト実行
python -m pytest tests/ -v
```

## 開発者向け情報

### プロジェクト構造

```
civitai-downloader/
├── src/
│   ├── __init__.py
│   ├── interfaces.py      # コアインターフェース
│   ├── config.py          # 設定管理
│   ├── utils.py           # ユーティリティ
│   ├── cli.py             # CLIインターフェース
│   ├── api_client.py      # CivitAI APIクライアント
│   ├── search.py          # 検索エンジン
│   ├── preview.py         # プレビュー管理
│   ├── download.py        # ダウンロード管理
│   └── storage.py         # ストレージ管理
├── tests/                 # テストスイート
├── docs/                  # ドキュメント
├── requirements.txt       # Python依存関係
└── pyproject.toml        # プロジェクト設定
```

### テスト実行

```bash
# 全テスト実行
python -m pytest tests/

# 特定テスト実行
python -m pytest tests/test_api_client.py -v

# カバレッジ付きテスト
python -m pytest tests/ --cov=src --cov-report=html
```

### 依存関係

- **click**: CLIフレームワーク
- **aiohttp**: 非同期HTTP通信
- **aiofiles**: 非同期ファイル操作
- **tqdm**: 進捗バー表示
- **Pillow**: 画像処理
- **rich**: リッチテキスト表示
- **platformdirs**: プラットフォーム固有ディレクトリ

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## サポート

- GitHub Issues: バグレポートや機能要望
- ドキュメント: `docs/` ディレクトリ内
- テスト: `tests/` ディレクトリ内

---

**注意**: このツールはCivitAI.comの非公式ツールです。利用規約を遵守してご使用ください。