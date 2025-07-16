# CivitAI Tools

CivitAIのAPIを活用したモデル分析・収集ツールセットです。モデルの検索、詳細情報取得、ランキング生成などの機能を提供します。

## 🎯 プロジェクト概要

CivitAI Toolsは、CivitAI.comのAIモデルを効率的に検索・分析するためのPythonツールセットです。主に以下の機能を提供します：

- **モデル検索**: タグ、タイプ、ソート順での包括的検索
- **詳細メトリクス収集**: 個別モデルAPIからの詳細情報取得
- **ランキングシステム**: 重み付きスコアによる品質評価
- **データ分析**: 統計情報の生成とビジュアルレポート作成

## ✨ 主要機能

### 1. 包括的モデル検索
- カーソルベースページネーションで完全なデータ取得
- タイプ別検索（Checkpoint、LoRA、LyCORIS）
- タグベース検索（style、anime、nsfw等）
- 複数ソート順対応（人気順、ダウンロード数順等）

### 2. 詳細メトリクス収集
- いいね数、コメント数、お気に入り数
- エンゲージメントスコアの計算
- ベースモデルタグの検証

### 3. ランキングシステム
- 重み付きスコアリング（いいね40%、DL30%、エンゲージメント20%、コメント10%）
- 殿堂入りシステム（突出したモデルの別枠表彰）
- HTMLビジュアルレポート生成

### 4. データエクスポート
- CSV、JSON、HTML形式での出力
- タグベースNSFW分類
- 統計情報の自動生成

## 📦 インストール

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

## 🚀 クイックスタート

### 1. API設定
[CivitAI](https://civitai.com/user/account)からAPIキーを取得し、環境変数に設定：

```bash
# .envファイルを作成
cp .env.example .env

# APIキーを設定
CIVITAI_API_KEY=your_api_key_here
```

### 2. 基本的な使用例

#### モデル検索
```python
from src.api.client import CivitAIClient

client = CivitAIClient()
models = client.search_models(
    types="Checkpoint",
    tags="anime",
    sort="Highest Rated",
    limit=100
)
```

#### ランキング生成
```bash
# Illustriousモデルのランキングを生成
python scripts/collection/illustrious_type_search.py
```

## 📊 主要スクリプト

### データ収集
- `scripts/collection/illustrious_type_search.py` - タイプ別モデル検索
- `scripts/collection/comprehensive_collection.py` - 包括的データ収集
- `scripts/collection/enhanced_collection.py` - 詳細メトリクス収集

### 分析・ランキング
- `create_top100_excluding_hall_of_fame.py` - Top100ランキング生成
- `scripts/analysis/comprehensive_search.py` - データ分析

### ユーティリティ
- `src/api/client.py` - CivitAI APIクライアント（カーソルページネーション対応）
- `src/core/enhanced_url_collector.py` - URL収集・エクスポート

## 📁 プロジェクト構造

```
civitiai-tools/
├── src/                     # ソースコード
│   ├── api/                # API関連
│   │   ├── client.py       # APIクライアント
│   │   └── tag_discovery.py # タグ検索
│   └── core/               # コア機能
├── scripts/                 # 実行スクリプト
│   ├── collection/         # データ収集
│   └── analysis/           # 分析スクリプト
├── docs/                    # ドキュメント
│   ├── civitai.md          # API仕様
│   ├── ranking-rules.md    # ランキング方法
│   └── searchplan.md       # 検索計画
├── outputs/                 # 出力ディレクトリ（.gitignore）
├── tests/                   # テストスイート
└── requirements.txt        # 依存関係
```

## 📋 API仕様の注意点

CivitAI APIには以下の制約があります（詳細は`docs/civitai.md`参照）：

- **カーソルベースページネーション**: nextCursorを使用した順次取得が必要
- **タイプ名の正規化**: LyCORISは内部的に"LoCon"として送信
- **レート制限**: 適切なインターバル（2秒）の設定
- **最大取得数**: 1リクエストあたり最大100件

## 🏆 実績例

### Illustrious Checkpointランキング（Top 10）
1. Hassaku XL (Illustrious) - スコア100.0
2. Mistoon_Anime - スコア84.3
3. PerfectDeliberate - スコア57.6
4. Illustrious-XL - スコア56.5
5. NTR MIX - スコア55.9

※ WAI-NSFW-illustrious-SDXLは殿堂入り（いいね47,373、DL639,550）

## 🛠️ 開発

### テスト実行
```bash
# 全テストを実行
python -m pytest

# カバレッジ付き
python -m pytest --cov=src

# 特定のテスト
python -m pytest tests/test_api_client.py -v
```

### コード品質
```bash
# Ruffでリント
ruff check .

# 自動修正
ruff check --fix .
```

## 📝 ライセンス

[ライセンス情報を追加予定]

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ⚠️ 注意事項

- APIキーは必ず環境変数で管理してください
- 出力ファイル（outputs/）はGitにコミットされません
- レート制限を遵守し、過度なリクエストは避けてください

## 📞 サポート

問題や提案がある場合は、[Issues](https://github.com/calico923/civitiai-tools/issues)でお知らせください。