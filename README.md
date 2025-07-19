# CivitAI Downloader v2

CivitAI.comから効率的にAIモデルをダウンロードするための次世代Pythonアプリケーション

## 🎯 プロジェクト概要

CivitAI Downloader v2は、大規模データセット処理、セキュリティ、パフォーマンスを重視して設計された、クリーンアーキテクチャベースのダウンローダーです。

### 主な特徴

- **🏗️ 3層アーキテクチャ**: API・Core・Data層による疎結合設計
- **🔒 セキュリティファースト**: SafeTensors優先、Pickleファイル条件付き対応
- **⚡ 高パフォーマンス**: 10,000+モデル対応の高度なメモリ管理
- **🧪 TDD開発**: テスト駆動開発による高品質保証
- **📊 包括的エラー処理**: 統一エラーシステムとフォールバック機構

## 📁 プロジェクト構造

```
civitai-downloader-v2/           # メインプロジェクト
├── src/                         # ソースコード
│   ├── api/                     # API層
│   ├── core/                    # Core層（ビジネスロジック）
│   └── data/                    # Data層（データアクセス）
├── tests/                       # テストスイート
├── docs/                        # プロジェクトドキュメント
└── config/                      # 設定ファイル

1st-coding/                      # アーカイブ（旧プロトタイプ・調査資料）
```

## 🚀 開発状況

### ✅ Phase 1: 基盤システム完了 (49/49テスト合格)

- **3層アーキテクチャ**: クリーンな層分離
- **抽象インターフェース**: 拡張可能な設計パターン
- **メモリ管理**: 大規模データ対応
- **エラー処理**: 統一システム
- **設定管理**: YAML + 環境変数
- **データモデル**: Pydantic V2による型安全性

### 🔄 実装予定

- Phase 2: API層実装
- Phase 3: Core層実装
- Phase 4: Data層実装
- Phase 5: ダウンロード機能
- Phase 6: CLI実装
- Phase 7: 統合テスト

## 🛠️ 技術スタック

- **Python**: 3.11+
- **データ検証**: Pydantic V2
- **テスト**: pytest
- **設定**: YAML + 環境変数
- **アーキテクチャ**: Clean Architecture
- **開発手法**: TDD (Test-Driven Development)

## 📚 ドキュメント

詳細なドキュメントは [`civitai-downloader-v2/docs/`](./civitai-downloader-v2/docs/) をご参照ください。

- [Phase 1: 基盤システム実装レポート](./civitai-downloader-v2/docs/phase-1-foundation-systems.md)

## 🔧 開発環境セットアップ

```bash
# 1. 仮想環境の有効化
source venv/bin/activate

# 2. プロジェクトディレクトリに移動
cd civitai-downloader-v2

# 3. テスト実行
python -m pytest tests/unit/ -v
```

## 📈 テスト状況

```
Phase 1: 49/49 tests passing ✅
├── Project Structure: 8 tests ✅
├── Abstract Interfaces: 8 tests ✅
├── Memory Management: 8 tests ✅
├── Error Handling: 8 tests ✅
├── Configuration: 9 tests ✅
└── Data Models: 8 tests ✅
```

## 🔐 セキュリティ

- **ファイル形式検証**: SafeTensors優先サポート
- **セキュリティスキャン**: 全ファイル自動検証
- **ハッシュ検証**: SHA256による整合性確認
- **機密情報保護**: API Key等の安全な管理

## 📄 ライセンス

[ライセンス情報は後日追加予定]

---

**最終更新**: 2025年1月19日  
**プロジェクト状況**: Phase 1 完了 ✅  
**開発者**: Claude Code