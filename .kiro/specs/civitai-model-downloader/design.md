# Design Document

## Overview

CivitAI Model Downloaderは、既存の調査ツールから独立したスタンドアロンのCLIアプリケーションとして設計されます。マルチプラットフォーム対応を重視し、シンプルなコマンドライン操作でモデルの検索・プレビュー・ダウンロードを可能にします。MVPでは核となる機能に集中し、段階的に機能を拡張できる設計とします。

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Engine    │────│  CivitAI API    │
│                 │    │                 │    │                 │
│ - Search UI     │    │ - Model Search  │    │ - Model Data    │
│ - Preview UI    │    │ - File Download │    │ - Image Data    │
│ - Download UI   │    │ - Progress Track│    │ - Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │  Local Storage  │
                       │                 │
                       │ - Downloaded    │
                       │   Models        │
                       │ - Metadata      │
                       │ - Images        │
                       └─────────────────┘
```

### Component Architecture

```
civitai-downloader/
├── src/
│   ├── cli/                    # CLI Interface Layer
│   │   ├── commands/          # Command handlers
│   │   ├── ui/                # Text-based UI components
│   │   └── main.py            # Entry point
│   ├── core/                  # Core Business Logic
│   │   ├── search.py          # Model search engine
│   │   ├── downloader.py      # File download manager
│   │   ├── preview.py         # Model preview handler
│   │   └── storage.py         # Local storage manager
│   ├── api/                   # CivitAI API Client
│   │   ├── client.py          # API communication
│   │   └── models.py          # Data models
│   └── utils/                 # Cross-platform utilities
│       ├── filesystem.py      # OS-agnostic file operations
│       ├── progress.py        # Progress tracking
│       └── config.py          # Configuration management
```

## Components and Interfaces

### 1. CLI Interface Layer

**Purpose**: ユーザーとの対話を管理し、コマンドを適切なハンドラーにルーティング

**Key Components**:
- `CommandParser`: コマンドライン引数の解析
- `SearchUI`: 検索結果の表示とナビゲーション
- `PreviewUI`: モデル詳細とサンプル画像の表示
- `DownloadUI`: ダウンロード進捗の表示

**Interface Example**:
```python
class CLIInterface:
    def search_models(self, query: SearchQuery) -> None
    def show_model_details(self, model_id: str) -> None
    def download_model(self, model_id: str, version_id: str) -> None
    def list_downloads(self) -> None
```

### 2. Core Engine

**Purpose**: ビジネスロジックの中核を担い、各機能を統合

**Key Components**:
- `ModelSearchEngine`: 検索クエリの処理とフィルタリング
- `DownloadManager`: ダウンロードの管理と進捗追跡
- `PreviewManager`: モデル詳細とサンプル画像の取得
- `StorageManager`: ローカルファイルとメタデータの管理

**Interface Example**:
```python
class ModelSearchEngine:
    def search(self, query: SearchQuery) -> List[ModelSummary]
    def get_model_details(self, model_id: str) -> ModelDetails
    def get_sample_images(self, model_id: str) -> List[ImageData]

class DownloadManager:
    def download_model(self, model: ModelDetails, version: VersionDetails) -> DownloadTask
    def resume_download(self, task_id: str) -> DownloadTask
    def get_download_status(self, task_id: str) -> DownloadStatus
```

### 3. CivitAI API Client

**Purpose**: CivitAI APIとの通信を抽象化し、レート制限やエラー処理を管理

**Key Components**:
- `APIClient`: HTTP通信とレスポンス処理
- `RateLimiter`: API呼び出し頻度の制御
- `DataModels`: APIレスポンスのデータ構造

**Interface Example**:
```python
class CivitAIClient:
    def search_models(self, params: SearchParams) -> APIResponse[List[Model]]
    def get_model(self, model_id: str) -> APIResponse[ModelDetails]
    def get_model_version(self, version_id: str) -> APIResponse[VersionDetails]
    def download_file(self, url: str, destination: Path) -> Iterator[DownloadProgress]
```

### 4. Cross-Platform Utilities

**Purpose**: OS固有の処理を抽象化し、マルチプラットフォーム対応を実現

**Key Components**:
- `FileSystemUtils`: パス処理、ディスク容量チェック
- `ProgressTracker`: ダウンロード進捗の表示
- `ConfigManager`: 設定ファイルの管理

## Data Models

### Core Data Structures

```python
@dataclass
class SearchQuery:
    model_types: List[str] = None
    tags: List[str] = None
    base_model: str = None
    sort_order: str = "Highest Rated"
    nsfw: bool = False
    limit: int = 20

@dataclass
class ModelSummary:
    id: str
    name: str
    type: str
    base_model: str
    creator: str
    stats: ModelStats
    thumbnail_url: str

@dataclass
class ModelDetails:
    id: str
    name: str
    description: str
    type: str
    tags: List[str]
    versions: List[VersionSummary]
    images: List[ImageData]
    stats: ModelStats

@dataclass
class VersionDetails:
    id: str
    name: str
    base_model: str
    files: List[FileInfo]
    download_url: str
    file_size: int
    trained_words: List[str]

@dataclass
class DownloadTask:
    id: str
    model_name: str
    version_name: str
    file_size: int
    destination: Path
    status: DownloadStatus
    progress: float
    speed: float
```

### Storage Schema

```
downloads/
├── config/
│   ├── settings.json          # User preferences
│   └── download_history.json  # Download records
├── models/
│   ├── checkpoints/
│   │   ├── illustrious/
│   │   └── pony/
│   ├── loras/
│   └── embeddings/
└── metadata/
    ├── model_info/            # JSON files with model details
    └── images/                # Sample images
```

## Error Handling

### Error Categories

1. **Network Errors**: API接続失敗、タイムアウト
2. **File System Errors**: 権限不足、容量不足
3. **Data Errors**: 不正なレスポンス、破損ファイル
4. **User Errors**: 無効な入力、存在しないモデル

### Error Handling Strategy

```python
class DownloaderError(Exception):
    """Base exception for downloader errors"""
    pass

class NetworkError(DownloaderError):
    """Network-related errors"""
    pass

class StorageError(DownloaderError):
    """File system and storage errors"""
    pass

class APIError(DownloaderError):
    """CivitAI API errors"""
    pass

# Error handling with retry logic
def with_retry(max_attempts: int = 3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except NetworkError as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
        return wrapper
    return decorator
```

## Testing Strategy

### Unit Testing

- **API Client**: モックレスポンスを使用したテスト
- **Core Logic**: ビジネスロジックの単体テスト
- **File Operations**: 一時ディレクトリを使用したテスト
- **Cross-Platform**: 各OS固有の動作テスト

### Integration Testing

- **End-to-End**: 実際のAPIを使用した統合テスト
- **Download Flow**: 小さなファイルでの完全なダウンロードテスト
- **Error Scenarios**: ネットワーク障害、容量不足のシミュレーション

### Test Structure

```
tests/
├── unit/
│   ├── test_api_client.py
│   ├── test_search_engine.py
│   ├── test_download_manager.py
│   └── test_storage_manager.py
├── integration/
│   ├── test_download_flow.py
│   └── test_api_integration.py
└── fixtures/
    ├── mock_responses.json
    └── sample_models.json
```

## MVP Feature Scope

### Phase 1: Core MVP

**Essential Features**:
1. **Basic Search**: モデルタイプとタグによる検索
2. **Model Preview**: 基本情報とサンプル画像の表示
3. **Simple Download**: 単一モデルのダウンロード
4. **Progress Tracking**: リアルタイム進捗表示
5. **Cross-Platform**: Windows/Mac/Linux対応

**CLI Commands**:
```bash
# Search models
civitai-dl search --type checkpoint --tags anime --base-model illustrious

# Show model details
civitai-dl show <model-id>

# Download model
civitai-dl download <model-id> [--version <version-id>] [--output <path>]

# List downloads
civitai-dl list
```

### Phase 2: Enhanced Features (Future)

- バッチダウンロード
- ダウンロード履歴管理
- 設定ファイルによるカスタマイズ
- 自動フォルダ整理
- ダウンロード再開機能

## Technical Considerations

### Performance

- **Streaming Downloads**: 大容量ファイル対応のためのストリーミング（Checkpoint平均6.6GB）
- **Batch Downloads**: 複数モデル同時ダウンロード（合計数百GB〜TB規模対応）
- **Concurrent Operations**: 複数の小さなファイル（画像等）の並列処理
- **Memory Management**: 大容量ファイル処理時のメモリ使用量制御
- **Disk Space Management**: 大量ダウンロード前の容量チェックと警告

### Security

- **API Key Management**: 環境変数による安全な認証情報管理
- **File Validation**: ダウンロードファイルの整合性チェック
- **Path Sanitization**: ディレクトリトラバーサル攻撃の防止

### Scalability

- **Modular Design**: 機能追加が容易な設計
- **Plugin Architecture**: 将来的な拡張機能対応
- **Configuration System**: ユーザー設定の柔軟な管理で