# Developer Guide

CivitAI Downloader v2 の開発者向けガイド

## プロジェクト概要

- **言語**: Python 3.8+
- **アーキテクチャ**: モジュラー設計
- **API**: CivitAI API v1
- **データベース**: SQLite
- **テスト**: pytest

## ディレクトリ構造

```
src/
├── api/           # API クライアント層
├── cli/           # コマンドライン インターフェース
├── core/          # コアビジネスロジック
│   ├── search/    # 検索エンジン
│   ├── download/  # ダウンロード管理
│   ├── security/  # セキュリティ機能
│   └── analytics/ # 分析機能
├── data/          # データ層
└── ui/            # ユーザーインターフェース
```

## 主要コンポーネント

### 1. 検索システム (`src/core/search/`)

- `advanced_search.py`: 高度検索パラメータとロジック
- `search_engine.py`: 検索エンジンの実装
- `strategy.py`: 検索戦略の定義

### 2. API クライアント (`src/api/`)

- `client.py`: メインAPIクライアント
- `params.py`: APIパラメータ処理
- `rate_limiter.py`: レート制限管理

### 3. CLI インターフェース (`src/cli/`)

- `main.py`: 全CLIコマンドの実装

## 実装済み機能

### Phase A
- 商用利用配列対応
- sortBy高度ソート
- ページネーション修正

### Phase B  
- 日付フィルタリング
- 評価フィルタリング
- ハッシュ検証
- バージョン管理

### Phase C
- カテゴリフィルタリング（15種類）
- NSFWレベル制御
- 完全機能テスト完了

## 開発環境セットアップ

```bash
# リポジトリクローン
git clone <repository-url>
cd civitai-downloader-v2

# 依存関係インストール
pip install -r requirements.txt

# テスト実行
python -m pytest tests/

# CLI テスト
python -m src.cli.main search "test" --limit 1
```

## テスト

```bash
# 全テスト実行
python -m pytest tests/ -v

# 単体テスト
python -m pytest tests/unit/ -v

# 統合テスト
python -m pytest tests/integration/ -v

# 特定モジュールテスト
python -m pytest tests/unit/test_advanced_search.py -v
```

## 新機能追加ガイド

### 1. 検索フィルタの追加

1. `advanced_search.py` にパラメータ追加
2. `client.py` でAPI変換ロジック追加
3. `main.py` にCLIオプション追加
4. テストケース作成

### 2. CLIコマンドの追加

1. `main.py` に新しい `@cli.command()` 追加
2. オプションパラメータ定義
3. 処理ロジック実装
4. ヘルプ文書更新

## コード規約

- PEP 8 準拠
- Type hints 使用
- Docstring 記述
- エラーハンドリング必須

## デバッグ

```bash
# デバッグモードで実行
python -m src.cli.main search "test" --format simple --limit 1

# ログレベル変更
export CIVITAI_LOG_LEVEL=DEBUG
```

## API制限

- レート制限: 2秒間隔推奨
- 同時リクエスト: 3まで
- タイムアウト: 30秒

## 既知の制限

1. 複数モデルタイプの同時指定不可
2. 一部フィルタ組み合わせでAPI 400エラー
3. 大量データの処理でメモリ使用量増加

## アーキテクチャ

- **レイヤード アーキテクチャ**: UI → Core → API → Data
- **依存性注入**: インターフェースベース設計
- **エラーハンドリング**: 統一されたエラー処理
- **設定管理**: YAML ベース設定

## パフォーマンス

- 非同期処理対応
- SQLite 最適化
- メモリ効率的な大量データ処理
- キャッシュシステム