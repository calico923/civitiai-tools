# TDD実装計画 (改訂版)

## 概要

本文書は、Civitai Model Downloader v2のテスト駆動開発（TDD）による実装タスクを定義します。改善された3層アーキテクチャ設計と要件定義書に基づき、品質を確保しながら段階的に実装します。

### Minimum Viable Product (MVP) の定義
本プロジェクトのMVPは、「**基本的な検索（タグ、ベースモデル）とダウンロード機能を備え、安定して動作するCLIツール**」と定義します。
**目標**: Phase 5完了時点でのα版リリースを目指します。

## TDD実装戦略

### 開発アプローチ
1. **Red**: 失敗するテストを先に書く
2. **Green**: 最小限の実装でテストを通す
3. **Refactor**: コードの健全性メトリクスを維持しつつ、継続的にリファクタリングを行う

### テストカバレッジ目標
- **ユニットテスト**: 90%以上
- **統合��スト**: 80%以上
- **E2Eテスト**: MVPの主要フロー100%

### 3層アーキテクチャに基づく構成
- **API層**: 外部通信とキャッシュ、フォールバック管理
- **コア層**: ビジネスロジック、検索戦略、セキュリティ統合
- **データ層**: 永続化、エクスポート、履歴管理

### 実装優先順位
1. **Phase 1**: 基盤システム（インターフェース定義、メモリ管理、エラーハンドリング、DB最適化基盤）
2. **Phase 1.9**: ロギング・監視基盤
3. **Phase 2**: API層（統合クライアント、ストリーミング処理、基本監視機能）
4. **Phase 3**: コア層（検索サービス、セキュリティ管理）
5. **Phase 4**: データ層（最適化DB、エクスポート）
6. **Phase 5**: ダウンロード機能（ストリーミングダウンロード）
7. **Phase 5.4**: バックプレッシャー制御
8. **Phase 6**: 高度機能（非公式API、カテゴリ）
9. **Phase 7**: CLI・統合テスト
10. **品質向上フェーズ**: MVPリリース後の高度な品質保証（Mutation Testing, カオステスト等）

## TDDタスクリスト

### Phase 1: 基盤システム構築【P0: Critical】

#### 1.1 プロジェクト構造（3層アーキテクチャ対応）
- [ ] **実装**: 3層アーキテクチャのディレクトリ構造を作成
  ```
  civitai-downloader-v2/
  ├── src/
  │   ├── api/
  │   ├── core/
  │   └── data/
  ├── tests/
  ```
- [ ] **規約**: プロジェクト構造の規約は、リンターやカスタム静的解析スクリプトで継続的に検証する。
  - _要件: 設計書Critical Issue 1対応_

#### 1.2 抽象インターフェース定義【P0: Critical】
- [ ] **テスト**: インターフェースの**契約**を検証するテストを作成
  ```python
  test_interfaces.py:
  # 例: SearchStrategyInterface
  - test_search_strategy_must_return_async_iterator()
  - test_search_strategy_raises_specific_exception_on_failure()
  # 例: ISecurityChecker
  - test_security_checker_returns_risk_level_enum()
  ```
- [ ] **実装**: 抽象基底クラス（ABC）を定義
  ```python
  src/core/interfaces/:
  - search_strategy.py
  - export_format.py
  - security_checker.py
  - memory_manager.py
  - error_handler.py
  ```
  - _要件: 設計書Critical Issue 3, 2対応_

#### 1.3 メモリ管理システム【P0: Critical】
- [ ] **テスト**: 具体的なシナリオに基づいたメモリ管理機能テスト
  ```python
  test_memory_management.py:
  - test_memory_usage_exceeds_threshold_triggers_streaming()
  - test_adaptive_threshold_adjusts_down_on_memory_pressure()
  - test_memory_statistics_are_collected_correctly()
  ```
- [ ] **実装**: メモリ管理コンポーネント
  ```python
  src/core/memory/:
  - memory_manager_impl.py
  ```
  - _要件: 設計書Critical Issue 2, 3対応_

#### 1.4 統合エラーハンドリング基盤【P0: Critical】
- [ ] **テスト**: エラーハンドリングの具体的な振る舞いをテスト
  ```python
  test_error_handling.py:
  - test_api_error_is_wrapped_in_unified_exception()
  - test_fallback_is_triggered_on_primary_service_failure()
  - test_error_context_captures_request_details()
  ```
- [ ] **実装**: エラーハンドリングシステム
  ```python
  src/core/error/:
  - unified_error_handler.py
  ```
  - _要件: 要件8.1, 17.1_

#### 1.5 設定管理システム【P1: High】
- [ ] **テスト**: 設定管理テスト
  ```python
  test_config_management.py:
  - test_env_vars_override_yaml_config()
  - test_config_validation_raises_error_on_missing_required_field()
  ```
- [ ] **実装**: SystemConfigクラス
  - _要件: 要件7.1, 7.4_

#### 1.6 データモデル定義【P0: Critical】
- [ ] **テスト**: データモデルの検証テスト（Pydantic等を利用）
  ```python
  test_data_models.py:
  - test_model_data_parses_from_valid_api_response()
  - test_search_params_validation_rejects_invalid_combinations()
  ```
- [ ] **実装**: Pydantic等を用いたデータクラス定義
  - _要件: 要件1.2, 2.1_

#### 1.7 最適化データベース基盤【P1: High】
- [ ] **テスト**: データベース最適化テスト
  ```python
  test_database_optimization.py:
  - test_virtual_column_accelerates_common_queries()
  - test_batch_insert_is_faster_than_individual_inserts()
  - test_sqlite_handles_10k_models_within_performance_budget()
  ```
- [ ] **実装**: 最適化されたSQLiteスキーマ
  - _要件: 設計書Medium Issue 5対応_

### Phase 1.9: ロギング・監視基盤【P0: Critical】

#### 1.9.1 統合ログ・監視システム
- [ ] **テスト**: 監視機能テスト
  ```python
  test_logging_monitoring.py:
  - test_structured_log_has_correct_format_and_fields()
  - test_performance_metric_is_recorded_for_api_calls()
  - test_alert_is_triggered_when_error_rate_exceeds_threshold()
  ```
- [ ] **実装**: EnhancedMonitoringService
  - _要件: 要件8.3, 13.1, 17.1_

---
*(以降のフェーズも同様に、テストの具体化、優先順位付け、曖昧な「リファクタリング」項目の削除などを適用)*
---

### Phase 7: CLI・統合テスト【P0: Critical for MVP】

#### 7.1 CLIフレームワーク
- [ ] **テスト**: CLI機能テスト
- [ ] **実装**: Click ベースCLI
- [ ] **リファクタリング**: UX最適化

#### 7.2 統合テストスイート
- [ ] **テスト**: E2Eテスト実装 (MVPスコープ)
  ```python
  tests/e2e/:
  - test_search_and_download_happy_path.py
  - test_system_handles_api_not_found_error_gracefully.py
  ```
- [ ] **実装**: テストフィクスチャ

#### 7.3 パフォーマンス検証
- [ ] **テスト**: MVPの性能目標に対するベンチマークテスト
  ```python
  test_performance_benchmarks.py:
  - test_mvp_search_responds_within_target_time()
  - test_mvp_memory_usage_stays_within_budget()
  ```
- [ ] **実装**: ベンチマークツール

---

### 品質向上フェーズ (Post-MVP)

#### Q1. Mutation Testing導入【P2: Low】
- [ ] **ツール**: `mutmut`等の導入
- [ ] **目標**: ビジネスロジックとセキュリティ機能において80%以上の変異検出率
- [ ] **CI/CD**: 週次実行のパイプラインを構築

#### Q2. カオステスト導入【P2: Low】
- [ ] **シナリオ**: ネットワーク障害、APIの予期せぬ変更、リソース枯渇などをシミュレート
- [ ] **CI/CD**: 手動トリガーまたは月次で実行

---

## TDD実装スケジュール（20週間バージョン）

- **Week 1-4: 基盤構築 (Phase 1 & 1.9)**
- **Week 5-7: API層実装 (Phase 2)**
- **Week 8-10: コア層実装 (Phase 3)**
- **Week 11-14: データ層 & ダウンロード (Phase 4-5 & 5.4)**
- **Week 15-16: 高度機能 (Phase 6)**
- **Week 17-20: CLI, 統合テスト, 品質保�� & バッファ (Phase 7)**

## TDD完了条件

### フェーズ別完了基準
1. **テストファースト**: 全ての機能コードは、失敗するテストの後に書かれている。
2. **テスト通過**: ユニット/統合テストが100%成功する。
3. **コード品質**: **SonarQube等の静的解析ツールのQuality Gateをクリアしている。** (例: 循環的複雑度 < 10)
4. **パフォーマンス**: 主要機能の性能が目標値を満たしている。
5. **ドキュメント**: 実装に伴い、関連ドキュメントが更新されている。

### 最終完了条件 (MVP)
- [ ] MVPスコープの全タスク(P0, P1)が完了している。
- [ ] MVP要件の受入テストがすべて合格している。
- [ ] **CI/CDパイプラインが構築され、テスト、ビルド、セキュリティスキャンが自動化されている。**
  - *セキュリティスキャンには `pip-audit`, `Snyk` 等を統合し、既知の脆弱性をブロックする。*
- [ ] パフォーマンス目標を達成している。
  - メモリ使用量: 500MB以下（10,000モデル処理時）
  - JSON検索速���: 0.5秒以下
- [ ] ユーザー受入テストが完了している。

**品質保証宣言**: このTDD実装計画により、設計改善で約束された高品質なMVPを確実に構築し、その後の継続的な品質向上を目指します。