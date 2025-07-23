# Phase 5マイグレーションガイド

**日付**: 2025-01-21  
**対象**: Phase 4からPhase 5への移行  
**互換性**: 下位互換性保持  

## 概要

Phase 5では、既存のPhase 1-4機能を維持しながら、新しい高度な機能を追加しました。このガイドでは、Phase 5の新機能を活用するための移行手順を説明します。

## 新機能概要

### 1. Enhanced Error Handler (要件8)
- インテリジェントリトライ機能
- 多段階ログシステム  
- パフォーマンス追跡

### 2. Security & License Management (要件9,14)
- 4フィールドライセンス管理
- セキュリティスキャン
- コンプライアンス警告

### 3. Advanced Search Parameters (要件10-12)
- 高度な検索フィルタ
- トリプルフィルタリング
- 非公式API管理

## 移行手順

### ステップ 1: 依存関係の確認

既存のコードに必要な新しいインポートを追加：

```python
# Enhanced Error Handler
from core.error.enhanced_error_handler import (
    EnhancedErrorHandler, BackoffStrategy, LogLevel
)

# Security & License Management  
from core.security.license_manager import LicenseManager
from core.security.security_scanner import SecurityScanner

# Advanced Search
from core.search.advanced_search import (
    AdvancedSearchParams, BaseModelDetector, UnofficialAPIManager
)
from core.search.search_engine import AdvancedSearchEngine
```

### ステップ 2: エラーハンドリングの移行

#### 従来のエラーハンドリング
```python
# Phase 4以前
try:
    result = await api_client.download_model(model_id)
except Exception as e:
    logger.error(f"Download failed: {e}")
    raise
```

#### Phase 5のエラーハンドリング
```python
# Phase 5
enhanced_handler = EnhancedErrorHandler()

async def download_with_retry(model_id: str):
    return await enhanced_handler.execute_with_intelligent_retry(
        operation=lambda: api_client.download_model(model_id),
        context={'model_id': model_id, 'operation': 'download'},
        max_retries=3,
        backoff_strategy=BackoffStrategy.ADAPTIVE
    )

# 使用例
try:
    result = await download_with_retry("12345")
except Exception as e:
    # Enhanced handlerが詳細なログとメトリクスを自動記録
    logger.error(f"Final download failure after retries: {e}")
```

### ステップ 3: セキュリティスキャンの統合

#### 基本的なセキュリティチェック
```python
# Phase 5セキュリティ統合
security_scanner = SecurityScanner()
license_manager = LicenseManager()

async def secure_download(model_data: Dict[str, Any]) -> bool:
    # 1. ライセンス確認
    license_info = license_manager.extract_license_info(model_data)
    if not license_info.allow_commercial_use:
        logger.warning("Commercial use not allowed")
        return False
    
    # 2. セキュリティスキャン  
    for version in model_data.get('modelVersions', []):
        for file_info in version.get('files', []):
            scan_result = security_scanner.perform_security_scan(file_info)
            if not scan_result.is_safe():
                logger.warning(f"Security risk detected: {scan_result.issues}")
                return False
    
    return True

# 使用例
if await secure_download(model_data):
    result = await download_with_retry(model_data['id'])
```

### ステップ 4: 高度な検索の活用

#### 従来の検索
```python
# Phase 4以前
search_results = await api_client.search_models(
    query="anime character",
    limit=50
)
```

#### Phase 5の高度な検索
```python
# Phase 5
search_engine = AdvancedSearchEngine(api_client=api_client)

# 高度な検索パラメータ
search_params = AdvancedSearchParams(
    query="anime character",
    categories=[ModelCategory.CHARACTER],
    tags=["anime", "waifu"],
    model_types=["LORA"],
    download_range=DownloadRange(min_downloads=1000, max_downloads=50000),
    nsfw_filter=NSFWFilter.SFW_ONLY,
    quality_filter=ModelQuality.VERIFIED,
    commercial_filter=CommercialUse.COMMERCIAL_ALLOWED,
    file_format=FileFormat.SAFETENSORS_ONLY
)

# 検索実行
search_result = await search_engine.search(search_params)

# 結果にはフィルタ情報とメタデータが含まれる
print(f"Found {search_result.filtered_count} models")
print(f"Filters applied: {search_result.filter_applied}")
```

### ステップ 5: 非公式API機能の設定

#### 安全な非公式機能の有効化
```python
# リスク許容度に応じた設定
search_engine.configure_unofficial_features(
    enable_advanced=True,
    risk_tolerance='medium'  # 'low', 'medium', 'high', 'critical'
)

# 公式優先モードの制御
search_engine.unofficial_api_manager.official_priority_mode = False

# 特定機能の個別制御
search_engine.unofficial_api_manager.enable_feature('advanced_sorting', force=True)
```

## 設定ファイルの更新

### 新しい設定オプション

```yaml
# config/settings.yaml (新規追加)

error_handling:
  default_max_retries: 3
  default_backoff_strategy: "adaptive"
  log_level: "INFO"
  performance_tracking: true

security:
  enable_virus_scan: true
  enable_pickle_scan: true
  hash_algorithms: ["sha256", "sha512"]
  commercial_filter_default: "commercial_allowed"

search:
  default_limit: 50
  max_limit: 200
  enable_unofficial_features: false
  risk_tolerance: "low"
  cache_results: true
  cache_ttl: 3600  # seconds
```

## データベース移行

### 新しいテーブル

Phase 5では新しいメタデータテーブルが追加されます：

```sql
-- ライセンス情報テーブル
CREATE TABLE model_licenses (
    model_id VARCHAR(50) PRIMARY KEY,
    allow_commercial_use BOOLEAN,
    allow_derivatives BOOLEAN,
    allow_different_license BOOLEAN,
    allow_no_credit BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- セキュリティスキャン結果テーブル
CREATE TABLE security_scans (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(500),
    scan_result VARCHAR(20),
    threats_detected TEXT[],
    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- エラーメトリクステーブル
CREATE TABLE error_metrics (
    id SERIAL PRIMARY KEY,
    operation_key VARCHAR(100),
    error_type VARCHAR(50),
    retry_count INTEGER,
    success BOOLEAN,
    execution_time FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### マイグレーションスクリプト

```python
# scripts/migrate_to_phase5.py
import asyncio
from core.security.license_manager import LicenseManager

async def migrate_existing_models():
    """既存モデルのライセンス情報を抽出・保存"""
    license_manager = LicenseManager()
    
    # 既存モデルデータを取得
    existing_models = await get_all_models()
    
    for model in existing_models:
        license_info = license_manager.extract_license_info(model)
        await save_license_info(model['id'], license_info)
        
    print(f"Migrated {len(existing_models)} models")

if __name__ == "__main__":
    asyncio.run(migrate_existing_models())
```

## 互換性情報

### 下位互換性保持項目
- ✅ 既存API インターフェース
- ✅ 設定ファイル形式
- ✅ データベーススキーマ (拡張のみ)
- ✅ CLI コマンド
- ✅ ファイル構造

### 新規追加項目
- 🆕 Enhanced Error Handler API
- 🆕 Security Scanner API
- 🆕 License Manager API
- 🆕 Advanced Search API
- 🆕 Base Model Detector
- 🆕 Unofficial API Manager

### 廃止予定項目
なし (Phase 5では廃止機能なし)

## トラブルシューティング

### よくある問題

#### 1. インポートエラー
```python
# 問題
ImportError: cannot import name 'AdvancedSearchParams'

# 解決
# 正しいインポートパスを確認
from core.search.advanced_search import AdvancedSearchParams
```

#### 2. 設定ファイルエラー
```yaml
# 問題: 旧設定ファイルの形式エラー

# 解決: 新しい設定セクションを追加
error_handling:
  default_max_retries: 3
```

#### 3. データベース接続エラー
```python
# 問題: 新しいテーブルが見つからない

# 解決: マイグレーションスクリプト実行
python scripts/migrate_to_phase5.py
```

### デバッグ支援

#### ログレベルの調整
```python
# 詳細なデバッグ情報を取得
enhanced_handler = EnhancedErrorHandler(
    log_level=LogLevel.DEBUG
)

# パフォーマンスメトリクス確認
metrics = enhanced_handler.get_performance_metrics()
print(f"Average response time: {metrics['avg_response_time']}")
```

#### セキュリティスキャン詳細
```python
# スキャン統計の確認
scanner = SecurityScanner()
stats = scanner.get_scan_statistics()
print(f"Total scans: {stats['total_scans']}")
print(f"Threats detected: {stats['threats_detected']}")
```

## パフォーマンス最適化

### 推奨設定

#### 本番環境
```yaml
error_handling:
  default_max_retries: 3
  default_backoff_strategy: "adaptive"
  
security:
  enable_virus_scan: true
  enable_pickle_scan: true
  
search:
  enable_unofficial_features: false
  risk_tolerance: "low"
```

#### 開発環境
```yaml
error_handling:
  default_max_retries: 1
  log_level: "DEBUG"
  
security:
  enable_virus_scan: false  # 開発時は無効化
  
search:
  enable_unofficial_features: true
  risk_tolerance: "high"
```

### キャッシュ設定
```python
# 検索結果のキャッシュ
search_engine = AdvancedSearchEngine(
    api_client=api_client,
    cache_enabled=True,
    cache_ttl=3600  # 1時間
)
```

## 移行チェックリスト

- [ ] 依存関係の更新
- [ ] 新しいインポートの追加
- [ ] エラーハンドリングの移行
- [ ] セキュリティチェックの統合
- [ ] 高度な検索の実装
- [ ] 設定ファイルの更新
- [ ] データベースマイグレーション
- [ ] テストの実行・確認
- [ ] パフォーマンステスト
- [ ] 本番環境への適用

## サポート

Phase 5への移行でご不明な点がございましたら、以下をご確認ください：

- **技術ドキュメント**: `/docs/phase-5-technical-details.md`
- **テストレポート**: `/docs/phase-5-test-report.md`
- **実装サマリー**: `/docs/phase-5-implementation-summary.md`

移行完了後は、Phase 5の新機能を活用して、より安全で高度なCivitAIダウンロード体験をお楽しみください。