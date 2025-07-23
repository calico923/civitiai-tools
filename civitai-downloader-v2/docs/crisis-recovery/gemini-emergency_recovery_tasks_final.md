# gemini-emergency_recovery_tasks_final.md

## 1. 基本方針

**最優先事項: 全テストが100%パスするまで、新規機能開発を完全に凍結する。**

このタスクリストは、最も広範囲に影響を及ぼしている根本原因から順に解決し、テストの失敗を効率的に解消するように設計されている。各フェーズのタスクを完了するごとに `python3 -m pytest civitai-downloader-v2/tests/` を実行し、進捗を確認することを推奨する。

---

## 【フェーズ1: 緊急止血 - 広範囲エラーの一掃】

### タスク1.1: 非同期 (`async`/`await`) の不整合を修正

-   **目的:** `TypeError: 'coroutine' object is not iterable` と `RuntimeWarning` を一掃する。
-   **対象ファイル:**
    -   `tests/unit/test_analytics_*.py`
    -   `tests/unit/test_bulk_download.py`
    -   `src/core/analytics/analyzer.py`
-   **具体的な作業:**
    1.  `AnalyticsCollector.record_event`, `AnalyticsCollector.get_events`, `BulkDownloadManager.create_bulk_job`, `AnalyticsAnalyzer.generate_report` など、`async def` に変更されたメソッドの呼び出し箇所をすべて探し、先頭に `await` を追加する。
    2.  上記 `await` を追加したテストメソッドに `@pytest.mark.asyncio` デコレータを付与し、メソッド自体も `async def` に変更する。
    3.  `AnalyticsAnalyzer` のように、内部で非同期メソッドを呼び出すようになったプロダクションコードも同様に修正する。

### タスク1.2: データベーススキーマの不整合を修正

-   **目的:** `sqlite3.OperationalError: no such table: events` を一掃する。
-   **対象ファイル:**
    -   `tests/unit/test_analytics_*.py`
-   **具体的な作業:**
    1.  対象ファイル群に含まれるすべてのSQLクエリ文字列を検索する。
    2.  テーブル名 `events` を `analytics_events` に一括置換する。

---

## 【フェーズ2: 構造的回復 - 依存関係の修復】

### タスク2.1: モジュール構造の変更に追従

-   **目的:** `FileNotFoundError` や `ModuleNotFoundError` を解消する。
-   **対象��ァイル:**
    -   `tests/unit/test_logging_monitoring.py`
    -   `tests/unit/test_bulk_download.py`
-   **具体的な作業:**
    1.  `test_logging_monitoring.py`: このテストは `src/monitoring` ディレクトリを対象としているが、このディレクトリは削除された。このテストファイル自体を**削除**するか、`Analytics`機能のテストとして書き直す必要がある。まずは削除を推奨する。
    2.  `test_bulk_download.py`: `from core.download.exceptions import ...` という行を削除または修正する。カスタム例外が廃止された場合、`try...except Exception` のように汎用的な例外を捕捉するようにテストを修正する。

### タスク2.2: APIシグネチャの不整合を修正

-   **目的:** `TypeError` と `AttributeError` の大部分を解消する。
-   **対象ファイル:**
    -   `tests/integration/test_component_integration.py`
    -   `tests/cli/test_cli.py`
-   **具体的な作業:**
    1.  `AdvancedSearchEngine`, `AnalyticsCollector`, `DownloadManager`, `CredentialStore` などのクラスが呼び出されている箇所を特定��る。
    2.  各クラスの現在の `__init__` メソッドの定義を確認し、テストコードでの呼び出し方を一致させる。（例: `CredentialStore()` のように引数なしで呼び出す）
    3.  `patch.object(...)` で指定しているメソッド名（例: `download_file`）が、実際のクラスに存在するか確認し、存在しない場合は正しいメソッド名（例: `start_download`）に修正する。

---

## 【フェーズ3: 論理的回復 - 個別テストの修正】

### タスク3.1: 仕様変更に伴うテストロジックの修正

-   **目的:** 残存する `AssertionError` を解消する。
-   **対象ファイル:**
    -   `tests/unit/test_authentication.py`
    -   `tests/unit/test_config_management.py`
    -   `tests/unit/test_download_manager.py`
    -   `tests/unit/test_database_optimization.py`
-   **具体的な作業:**
    1.  **`test_authentication.py`:** `AuthManager.validate_api_key` の実装が空文字列を有効と判定しているバグを修正する (`if not self.api_key or not self.api_key.strip(): return False`)。
    2.  **`test_config_management.py`:** `config.get('api.api_key')` が返す値の仕様が変わったため、テストの期待値 (`'yaml_key'`) を現在の正しい仕様に合わせる。また、`test_config_validation_schema` が例外を送出すべきところで送出していないため、`SystemConfig` のバリデーションロジックを再確認・修正する。
    3.  **その他:** `max_concurrent` のデフォルト値の変更など、エラーメッセージに従って、テストの期待値を現在の仕様に合わせる。

---

## 【フェーズ4: 再発防止 - CI/CDの導入】

### タスク4.1: GitHub ActionsによるCIパイプラインの構築

-   **目的:** **同様の危機が二度と発生しないようにする。**
-   **対象ファイル:**
    -   `.github/workflows/ci.yml` (新規作成)
-   **具体的な作業:**
    1.  すべてのテストがパスするようになった後、リポジトリのルートに `.github/workflows/` ディレクトリを作成する。
    2.  `ci.yml` というファイル名で、以下の内容を記述する。
        ```yaml
        name: CI

        on: [push, pull_request]

        jobs:
          test:
            runs-on: ubuntu-latest
            steps:
            - uses: actions/checkout@v3
            - name: Set up Python
              uses: actions/setup-python@v4
              with:
                python-version: '3.11'
            - name: Install dependencies
              run: |
                python -m venv venv
                source venv/bin/activate
                pip install -r requirements.txt
                pip install pytest pytest-asyncio
            - name: Run tests
              run: |
                source venv/bin/activate
                python -m pytest civitai-downloader-v2/tests/
        ```
    3.  このファイルをリポジトリにプッシュし、GitHubのブランチ保護ルールを設定する。**`test`ジョブが成功しない限り、`main`ブランチへのマージを絶対に許可しないように設定する。**
