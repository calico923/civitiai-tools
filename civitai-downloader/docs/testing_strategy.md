# テスト戦略とQA計画

最終更新日: 2025-07-18

## 🎯 テスト戦略の概要

### 現在の問題
- 非同期モックの設定が不適切（12個のテスト失敗）
- 実APIテストがタイムアウトで失敗
- 型の不一致による偽陽性・偽陰性
- テストの意図が不明確

### 目標
- 信頼性の高い自動化テストスイート
- 実環境での動作保証
- 開発効率の向上
- リグレッションの防止

## 🏗️ テストピラミッド

```
     E2E Tests (5%)
    ┌─────────────────┐
   │ 実際のAPI使用    │
   │ 完全なワークフロー │
   └─────────────────┘
        ↑
    Integration Tests (25%)
   ┌─────────────────────────┐
  │ コンポーネント間の連携     │
  │ モックAPIサーバー使用     │
  └─────────────────────────┘
        ↑
       Unit Tests (70%)
   ┌─────────────────────────────────┐
  │ 個別の関数・クラスの動作         │
  │ 完全にモック化された依存関係     │
  └─────────────────────────────────┘
```

## 📊 テストカテゴリー

### 1. 単体テスト（Unit Tests）

#### 1.1 Pure Functions Tests
```python
# test_utils.py
def test_format_file_size():
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(0) == "0 B"

def test_sanitize_filename():
    assert sanitize_filename("test<file>.txt") == "test_file_.txt"
    assert sanitize_filename("very/long/path") == "very_long_path"
```

#### 1.2 Data Model Tests
```python
# test_interfaces.py
def test_model_info_creation():
    model = ModelInfo(
        id=123,
        name="Test Model",
        type=ModelType.LORA,
        description="Test",
        tags=["test"],
        creator="test_user",
        stats={"downloadCount": 100},
        nsfw=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    assert model.id == 123
    assert model.type == ModelType.LORA
    assert model.download_count == 100
```

#### 1.3 Business Logic Tests
```python
# test_search_logic.py
def test_filter_models_by_type():
    models = [
        create_test_model(ModelType.LORA),
        create_test_model(ModelType.CHECKPOINT),
        create_test_model(ModelType.LORA)
    ]
    
    filtered = filter_models_by_type(models, ModelType.LORA)
    assert len(filtered) == 2
    assert all(m.type == ModelType.LORA for m in filtered)
```

### 2. 統合テスト（Integration Tests）

#### 2.1 API Client Integration
```python
# test_api_integration.py
import aioresponses

@pytest.mark.asyncio
async def test_api_client_search_integration():
    """APIクライアントの検索機能統合テスト"""
    with aioresponses.aioresponses() as mock:
        # モックレスポンスを設定
        mock.get(
            "https://civitai.com/api/v1/models",
            payload={
                "items": [
                    {
                        "id": 1,
                        "name": "Test Model",
                        "type": "LoRA",
                        "description": "Test",
                        "tags": ["test"],
                        "creator": {"username": "test_user"},
                        "stats": {"downloadCount": 100},
                        "nsfw": False,
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-01-01T00:00:00Z"
                    }
                ],
                "metadata": {"nextCursor": "next123"}
            }
        )
        
        config = ConfigManager()
        async with CivitAIAPIClient(config) as client:
            params = SearchParams(query="test", limit=1)
            models, cursor = await client.search_models(params)
            
            assert len(models) == 1
            assert models[0].name == "Test Model"
            assert cursor == "next123"
```

#### 2.2 Storage Integration
```python
# test_storage_integration.py
def test_storage_with_search_integration():
    """ストレージと検索の統合テスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ConfigManager()
        config.config.download_path = temp_dir
        
        storage = StorageManager(config)
        
        # テストデータを保存
        model = create_test_model()
        version = create_test_version(model.id)
        
        path = storage.get_model_path(model, version)
        path.mkdir(parents=True, exist_ok=True)
        
        storage.save_metadata(model, version, path)
        
        # 検索機能をテスト
        found = storage.find_model_by_id(model.id)
        assert found is not None
        assert found['name'] == model.name
        
        # 複雑な検索をテスト
        lora_models = storage.get_models_by_type('LORA')
        assert len(lora_models) == 1
```

### 3. E2Eテスト（End-to-End Tests）

#### 3.1 CLI Integration Tests
```python
# test_cli_e2e.py
@pytest.mark.e2e
def test_full_search_workflow():
    """完全な検索ワークフローのE2Eテスト"""
    runner = CliRunner()
    
    # 環境変数にテスト用APIキーを設定
    env = {'CIVITAI_API_KEY': 'test_key'}
    
    # 検索実行
    result = runner.invoke(
        cli, 
        ['search', 'anime', '--type', 'LoRA', '--limit', '3'],
        env=env
    )
    
    assert result.exit_code == 0
    assert 'Found' in result.output
    assert 'anime' in result.output.lower()
```

#### 3.2 Real API Tests (Optional)
```python
# test_real_api.py
@pytest.mark.slow
@pytest.mark.skipif(not os.getenv('CIVITAI_API_KEY'), reason="No API key")
@pytest.mark.asyncio
async def test_real_api_connection():
    """実際のAPIとの接続テスト（オプション）"""
    config = ConfigManager()
    
    async with CivitAIAPIClient(config) as client:
        # 最小限の検索を実行
        params = SearchParams(limit=1)
        models, cursor = await client.search_models(params)
        
        # 基本的な検証のみ
        assert isinstance(models, list)
        if models:
            assert hasattr(models[0], 'id')
            assert hasattr(models[0], 'name')
```

## 🛠️ モックとテストダブル戦略

### 1. aioresponsesを使用した HTTP モック

```python
# conftest.py
import pytest
import aioresponses

@pytest.fixture
def mock_aiohttp():
    """aiohttp リクエストのモック"""
    with aioresponses.aioresponses() as m:
        yield m

@pytest.fixture
def mock_civitai_api(mock_aiohttp):
    """CivitAI API のモック"""
    base_url = "https://civitai.com/api/v1"
    
    def _mock_models_response(items=None, cursor=None):
        items = items or []
        response = {
            "items": items,
            "metadata": {"nextCursor": cursor} if cursor else {}
        }
        mock_aiohttp.get(f"{base_url}/models", payload=response)
    
    def _mock_model_detail(model_id, model_data=None):
        model_data = model_data or create_test_model_data(model_id)
        mock_aiohttp.get(f"{base_url}/models/{model_id}", payload=model_data)
    
    return type('MockAPI', (), {
        'mock_models_response': _mock_models_response,
        'mock_model_detail': _mock_model_detail
    })()
```

### 2. ストレージのモック

```python
# test_mocks.py
class MockStorageManager:
    """テスト用のストレージマネージャー"""
    def __init__(self):
        self.models = {}
        self.history = []
    
    def save_metadata(self, model, version, path):
        self.models[model.id] = {
            'model': model,
            'version': version,
            'path': path
        }
    
    def find_model_by_id(self, model_id):
        if model_id in self.models:
            return self.models[model_id]['model']
        return None
    
    def get_storage_stats(self):
        return {
            'total_models': len(self.models),
            'total_size_human': '1.0 GB'
        }
```

## 🔧 テスト設定とツール

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    e2e: marks tests as end-to-end tests
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    asyncio: marks tests as asyncio tests
asyncio_mode = auto
```

### conftest.py
```python
# conftest.py
import pytest
import tempfile
import asyncio
from pathlib import Path

@pytest.fixture
def temp_dir():
    """一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def mock_config(temp_dir):
    """テスト用の設定"""
    config = ConfigManager()
    config.config.download_path = str(temp_dir)
    config.config.api_key = "test_key"
    config.config.api_timeout = 5
    return config

@pytest.fixture
def event_loop():
    """イベントループ"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

## 📊 テストメトリクス

### カバレッジ目標
- **単体テスト**: 90%以上
- **統合テスト**: 80%以上
- **E2Eテスト**: 主要ワークフロー100%

### パフォーマンス目標
- **単体テスト**: 全体で30秒以内
- **統合テスト**: 全体で2分以内
- **E2Eテスト**: 全体で5分以内

## 🚀 実行計画

### Phase 1: 基礎修正（今週）
1. aioresponsesライブラリの導入
2. 失敗している12個のテストの修正
3. 基本的なモック戦略の実装

### Phase 2: 統合テスト強化（来週）
1. API統合テストの実装
2. ストレージ統合テストの拡充
3. エラーハンドリングテストの追加

### Phase 3: E2Eテスト（再来週）
1. CLI E2Eテストの実装
2. 実APIテストの整備
3. パフォーマンステストの追加

### Phase 4: 自動化（継続）
1. CI/CDパイプラインの設定
2. テストレポートの自動化
3. 品質ゲートの設定

## 🎯 成功指標

1. **テスト成功率**: 95%以上
2. **テスト実行時間**: 目標値以内
3. **コードカバレッジ**: 目標値以上
4. **リグレッション**: 0件
5. **開発者満足度**: フィードバック収集

この戦略に従って、段階的に信頼性の高いテストスイートを構築し、品質の高いソフトウェアを開発していきます。