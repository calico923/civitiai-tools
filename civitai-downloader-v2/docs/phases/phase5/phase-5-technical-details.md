# Phase 5技術詳細

**日付**: 2025-01-21  
**フェーズ**: Phase 5 最終実装  
**要件**: 8-14  

## Enhanced Error Handler (要件8)

### アーキテクチャ詳細

#### インテリジェントバックオフ戦略
```python
class BackoffStrategy(Enum):
    EXPONENTIAL = "exponential"    # 2^n * base_delay
    LINEAR = "linear"             # n * base_delay  
    FIBONACCI = "fibonacci"       # fib(n) * base_delay
    ADAPTIVE = "adaptive"         # 動的調整
    JITTERED = "jittered"         # ランダム要素追加
```

#### 実装例
```python
# src/core/error/enhanced_error_handler.py:45
async def execute_with_intelligent_retry(self,
                                       operation: Callable,
                                       context: Dict[str, Any],
                                       max_retries: Optional[int] = None,
                                       backoff_strategy: BackoffStrategy = BackoffStrategy.ADAPTIVE) -> Any:
    """インテリジェントリトライ実行"""
    effective_max_retries = max_retries or self.default_max_retries
    
    for attempt in range(effective_max_retries + 1):
        try:
            result = await self._execute_operation(operation, context)
            # 成功時のメトリクス記録
            self._record_success_metrics(context, attempt)
            return result
            
        except Exception as e:
            if attempt > effective_max_retries:
                # 最終試行後の処理
                await self._handle_final_failure(e, context, attempt)
                raise
            
            # バックオフ計算と待機
            delay = self._calculate_backoff_delay(attempt, backoff_strategy)
            await asyncio.sleep(delay)
            
            # リトライメトリクス記録
            self._record_retry_metrics(context, attempt, str(e))
```

#### 多段階ログシステム
```python
class LogLevel(Enum):
    TRACE = "TRACE"       # 詳細なトレース情報
    DEBUG = "DEBUG"       # デバッグ情報  
    INFO = "INFO"         # 一般情報
    WARNING = "WARNING"   # 警告
    ERROR = "ERROR"       # エラー
    CRITICAL = "CRITICAL" # 致命的エラー
```

### パフォーマンス追跡
- **リトライ履歴**: 操作ごとの試行回数追跡
- **応答時間測定**: マイクロ秒精度の計測
- **エラーパターン分析**: 頻発エラーの自動検出

## Security & License Management (要件9,14)

### ライセンス管理システム

#### 4フィールドライセンス構造
```python
@dataclass
class LicenseInfo:
    allow_commercial_use: Optional[bool] = None      # 商用利用許可
    allow_derivatives: Optional[bool] = None         # 派生作品許可
    allow_different_license: Optional[bool] = None   # 異なるライセンス許可
    allow_no_credit: Optional[bool] = None          # クレジット不要許可
```

#### ライセンス抽出ロジック
```python
# src/core/security/license_manager.py:25
def extract_license_info(self, model_data: Dict[str, Any]) -> LicenseInfo:
    """モデルデータから4つのライセンスフィールドを抽出"""
    
    def parse_license_value(value: Any) -> Optional[bool]:
        """ライセンス値をbooleanに正規化"""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '1', 'allowed']
        if isinstance(value, (int, float)):
            return bool(value)
        return None
    
    license_info = LicenseInfo(
        allow_commercial_use=parse_license_value(model_data.get('allowCommercialUse')),
        allow_derivatives=parse_license_value(model_data.get('allowDerivatives')),
        allow_different_license=parse_license_value(model_data.get('allowDifferentLicense')),
        allow_no_credit=parse_license_value(model_data.get('allowNoCredit'))
    )
    
    return license_info
```

### セキュリティスキャンシステム

#### マルチハッシュ整合性確認
```python
class HashAlgorithm(Enum):
    MD5 = "md5"
    SHA1 = "sha1" 
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
```

#### セキュリティスキャン実装
```python
# src/core/security/security_scanner.py:120
def perform_security_scan(self, file_info: Dict[str, Any]) -> 'ScanReport':
    """総合セキュリティスキャン実行"""
    
    issues = []
    
    # 1. ウイルススキャン
    virus_result = self.scan_for_viruses(file_info)
    if virus_result != ScanResult.SAFE:
        issues.append(SecurityIssue(
            threat_type=ThreatType.VIRUS,
            severity='HIGH',
            description='Potential virus detected'
        ))
    
    # 2. Pickleスキャン 
    pickle_result = self.scan_for_pickle_threats(file_info)
    if pickle_result != ScanResult.SAFE:
        issues.append(SecurityIssue(
            threat_type=ThreatType.PICKLE_THREAT,
            severity='MEDIUM',
            description='Unsafe pickle content detected'
        ))
    
    # 3. ファイル整合性確認
    integrity_result = self.verify_file_integrity(file_info)
    if not integrity_result.is_valid:
        issues.append(SecurityIssue(
            threat_type=ThreatType.INTEGRITY_VIOLATION,
            severity='HIGH',
            description='File integrity check failed'
        ))
    
    # 4. プライバシーリスク評価
    privacy_result = self.assess_privacy_risks(file_info)
    if privacy_result.risk_level > 0.7:
        issues.append(SecurityIssue(
            threat_type=ThreatType.PRIVACY_RISK,
            severity='MEDIUM',
            description='High privacy risk detected'
        ))
    
    # 結果判定
    if not issues:
        overall_result = ScanResult.SAFE
    elif any(issue.severity == 'HIGH' for issue in issues):
        overall_result = ScanResult.MALICIOUS
    else:
        overall_result = ScanResult.SUSPICIOUS
    
    return ScanReport(
        scan_result=overall_result,
        issues=issues,
        scan_metadata={'timestamp': time.time(), 'scanner_version': '1.0'}
    )
```

## Advanced Search Parameters (要件10-12)

### トリプルフィルタリングシステム

#### Category × Tag × Model Type フィルタリング
```python
# src/core/search/search_engine.py:53
def apply_triple_filter(self, models: List[Dict[str, Any]], 
                      search_params: AdvancedSearchParams) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """3次元フィルタリング実行"""
    
    self.filter_stats['total_processed'] = len(models)
    filtered_models = models.copy()
    
    # Step 1: カテゴリフィルタリング
    if search_params.categories:
        before_count = len(filtered_models)
        filtered_models = self._filter_by_categories(filtered_models, search_params.categories)
        self.filter_stats['category_filtered'] = before_count - len(filtered_models)
    
    # Step 2: タグフィルタリング  
    if search_params.tags:
        before_count = len(filtered_models)
        filtered_models = self._filter_by_tags(filtered_models, search_params.tags)
        self.filter_stats['tag_filtered'] = before_count - len(filtered_models)
    
    # Step 3: モデルタイプフィルタリング
    if search_params.model_types:
        before_count = len(filtered_models)
        filtered_models = self._filter_by_types(filtered_models, search_params.model_types)
        self.filter_stats['type_filtered'] = before_count - len(filtered_models)
    
    # Step 4: セキュリティフィルタリング
    if search_params.file_format != FileFormat.ALL_FORMATS:
        before_count = len(filtered_models)
        filtered_models = self._filter_by_security(filtered_models, search_params.file_format)
        self.filter_stats['security_filtered'] = before_count - len(filtered_models)
    
    return filtered_models, dict(self.filter_stats)
```

### ベースモデル検出システム

#### 50+ベースモデル対応
```python
# src/core/search/advanced_search.py:350
class BaseModelDetector:
    def __init__(self):
        self.known_models = [
            # SD 1.x系
            'SD 1.4', 'SD 1.5', 'SD 1.5 Inpainting',
            
            # SDXL系  
            'SDXL 1.0', 'SDXL 1.0 LCM', 'SDXL Turbo', 'SDXL Lightning',
            
            # アニメ特化
            'Illustrious', 'NoobAI XL', 'Pony Diffusion V6 XL',
            'AnythingV3', 'AnythingV4', 'AnythingV5',
            
            # リアリスティック
            'Realistic Vision', 'DreamShaper', 'Deliberate',
            
            # 特殊用途
            'ControlNet', 'IP-Adapter', 'T2I-Adapter',
            
            # ... 50+のベースモデル
        ]
```

### 非公式API管理

#### リスクレベル管理
```python
class RiskLevel(Enum):
    LOW = "low"           # 公式に近い機能
    MEDIUM = "medium"     # 軽微な拡張
    HIGH = "high"         # 未文書化機能
    CRITICAL = "critical" # 高リスク機能
```

#### フォールバック機構
```python
# src/core/search/search_engine.py:263
async def _execute_search_with_fallback(self, search_params: AdvancedSearchParams) -> SearchResult:
    """フォールバック付き検索実行"""
    fallback_used = None
    
    # 高度な検索を試行
    try:
        if self.unofficial_api_manager.features['advanced_sorting'].enabled:
            result = await self._advanced_search(search_params)
            self.unofficial_api_manager.record_feature_usage('advanced_sorting', True)
            return result
    except Exception as e:
        logger.warning(f"Advanced search failed: {e}")
        self.unofficial_api_manager.record_feature_usage('advanced_sorting', False)
        fallback_used = 'official_search'
    
    # 公式検索にフォールバック
    try:
        result = await self._official_search(search_params)
        self.unofficial_api_manager.record_feature_usage('basic_search', True)
        if fallback_used:
            result.fallback_used = fallback_used
            self.search_stats['fallback_used'] += 1
        return result
    except Exception as e:
        logger.error(f"Official search failed: {e}")
        self.unofficial_api_manager.record_feature_usage('basic_search', False)
        raise
```

## パフォーマンス最適化

### 非同期処理
- **asyncio活用**: I/O集約処理の並列化
- **バッチ処理**: 複数モデルの一括処理
- **接続プール**: HTTPクライアント最適化

### メモリ管理
- **ストリーミング処理**: 大容量ファイル対応
- **ガベージコレクション**: メモリリーク防止
- **キャッシュ制御**: LRUキャッシュ実装

### 監視・メトリクス
- **リアルタイム統計**: 処理状況の可視化
- **エラー率追跡**: 品質指標管理
- **パフォーマンスプロファイリング**: ボトルネック特定

## セキュリティ考慮事項

### 入力検証
- **パラメータサニタイゼーション**: インジェクション攻撃防止
- **型安全性**: TypeHint活用
- **範囲チェック**: 境界値検証

### アクセス制御
- **認証システム**: API キー管理
- **レート制限**: DDoS攻撃緩和
- **監査ログ**: セキュリティイベント記録

### データ保護
- **暗号化**: 機密データ保護
- **ハッシュ化**: パスワード管理
- **安全な削除**: 一時ファイル処理

## 今後の拡張性

### プラグイン システム
- **モジュラー設計**: 機能追加容易
- **フック機構**: カスタマイゼーション対応
- **設定駆動**: 外部設定ファイル

### スケーラビリティ
- **水平スケーリング**: 複数インスタンス対応
- **負荷分散**: トラフィック分散
- **データベース最適化**: クエリ性能向上

### 運用支援
- **ヘルスチェック**: システム状態監視
- **メトリクス収集**: Prometheus連携
- **アラート機能**: 異常検知通知