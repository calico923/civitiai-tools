# CivitAI Downloader v2

CivitAI からモデルを検索・ダウンロードするためのコマンドラインツール

## 機能

- モデル検索とフィルタリング（15カテゴリ対応）
- 単体・一括ダウンロード
- ハッシュ検証とセキュリティスキャン
- バージョン管理
- 複数出力形式（table/simple/json）

## インストール

```bash
git clone https://github.com/your-org/civitai-downloader-v2.git
cd civitai-downloader-v2
pip install -r requirements.txt
```

## 基本的な使い方

### モデル検索

```bash
# 基本検索
python -m src.cli.main search "anime"

# フィルタリング
python -m src.cli.main search "character" --types Checkpoint --limit 10
python -m src.cli.main search "style" --category style --nsfw-level sfw
python -m src.cli.main search "realistic" --published-after 2024-01-01

# 複数カテゴリ
python -m src.cli.main search "anime" --category character,style

# 出力形式
python -m src.cli.main search "landscape" --format json --output results.json
```

### ダウンロード

```bash
# 単体ダウンロード
python -m src.cli.main download --model-id 12345

# 一括ダウンロード（JSON形式のファイルから）
python -m src.cli.main bulk-download --input model_ids.json

# ハッシュ検証付きダウンロード
python -m src.cli.main download --model-id 12345 --verify-hashes
```

### その他の機能

```bash
# モデル情報表示
python -m src.cli.main info 12345

# ハッシュ検証
python -m src.cli.main hash-verify /path/to/model.safetensors

# バージョン管理
python -m src.cli.main model-versions 12345

# セキュリティスキャン
python -m src.cli.main scan /path/to/directory
```

## 検索オプション

### フィルタリング

| オプション | 説明 | 例 |
|------------|------|-----|
| `--types` | モデルタイプ | `Checkpoint`, `LORA`, `LoCon` |
| `--category` | カテゴリ | `character`, `style`, `concept` |
| `--base-model` | ベースモデル | `SDXL 1.0`, `Pony` |
| `--nsfw-level` | NSFW制御 | `sfw`, `nsfw`, `all` |

### 日付フィルタ

| オプション | 説明 | 例 |
|------------|------|-----|
| `--published-after` | 公開日以降 | `2024-01-01` |
| `--published-before` | 公開日以前 | `2024-12-31` |
| `--published-within` | 公開期間内 | `30days`, `3months` |

### 評価フィルタ

| オプション | 説明 | 例 |
|------------|------|-----|
| `--min-likes` | 最小いいね数 | `1000` |
| `--min-like-ratio` | 最小いいね率 | `0.8` |
| `--min-interactions` | 最小インタラクション数 | `100` |

### ソート

| オプション | 説明 | 例 |
|------------|------|-----|
| `--sort` | 基本ソート | `Newest`, `Most Downloaded`, `Most Liked` |
| `--sort-by` | 高度ソート | `download_count`, `thumbs_up_count` |
| `--sort-direction` | ソート方向 | `desc`, `asc` |

## カテゴリ一覧

使用可能な15カテゴリ：

- `character` - キャラクター
- `style` - スタイル・画風
- `concept` - コンセプト・概念
- `background` - 背景・環境
- `poses` - ポーズ・姿勢
- `vehicle` - 乗り物・車両
- `clothing` - 衣装・服装
- `action` - アクション
- `animal` - 動物
- `assets` - アセット・素材
- `base model` - ベースモデル
- `buildings` - 建物・建築
- `celebrity` - 有名人・セレブリティ
- `objects` - オブジェクト・物体
- `tool` - ツール・道具

## 使用例

### よく使うパターン

```bash
# アニメキャラクターのLoRAを最新順で検索
python -m src.cli.main search "anime" --category character --types LORA --sort Newest

# SFWなスタイル系モデルを高評価順で検索
python -m src.cli.main search "style" --category style --nsfw-level sfw --sort "Most Liked"

# 2024年に公開された人気のCheckpointを検索
python -m src.cli.main search "realistic" --types Checkpoint --published-after 2024-01-01 --min-likes 500

# 検索結果をJSONファイルに保存
python -m src.cli.main search "landscape" --category background --format json --output landscapes.json

# 保存した検索結果から一括ダウンロード
python -m src.cli.main bulk-download --input landscapes.json --batch-size 3
```

### 高度な使用例

```bash
# 複数条件を組み合わせた詳細検索
python -m src.cli.main search "cyberpunk" \
  --category style,concept \
  --types LORA \
  --published-within 30days \
  --min-like-ratio 0.9 \
  --sort-by thumbs_up_count \
  --sort-direction desc \
  --limit 20

# ハッシュ検証とセキュリティスキャン付きダウンロード
python -m src.cli.main download --model-id 12345 --verify-hashes --scan-security

# モデルのバージョン情報を詳細表示
python -m src.cli.main model-versions 12345 --stats --output table
```

## 設定

設定ファイル：`config/app_config.yml`

```yaml
api:
  base_url: "https://civitai.com/api/v1"
  rate_limit: 0.5

download:
  base_directory: "./downloads"
  concurrent_downloads: 3
  verify_checksums: true

security:
  enable_scanning: true
  require_confirmation: true
```

## トラブルシューティング

### よくある問題

1. **400 Bad Request エラー**
   - 無効なフィルタの組み合わせが原因
   - 単純な検索条件で試してください

2. **検索結果が少ない**
   - フィルタが厳しすぎる可能性
   - 条件を緩めて再検索してください

3. **ダウンロードが失敗する**
   - ネットワーク接続を確認
   - `--verify-hashes` オプションでファイル整合性を確認

### デバッグ

```bash
# 詳細ログで実行
python -m src.cli.main search "test" --format ids --limit 1

# バージョン確認
python -m src.cli.main version

# 設定確認
python -m src.cli.main config
```

## ライセンス

MIT License

## 更新履歴

- v2.0: Phase A-C機能実装完了
  - カテゴリフィルタリング（15種類）
  - NSFWレベル制御
  - 日付・評価フィルタリング
  - 高度ソート機能
  - ハッシュ検証
  - バージョン管理