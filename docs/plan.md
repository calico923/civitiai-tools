# Civitai Model Downloader 実装計画書

## 1. プロジェクト概要

### 1.1 プロジェクト名
Civitai Model Downloader

### 1.2 開発期間
約2週間（実働10日）

### 1.3 技術スタック
- **言語**: Python 3.8+
- **主要ライブラリ**:
  - requests: HTTP通信
  - click: CLI構築
  - rich: 進捗表示・ターミナルUI
  - python-dotenv: 環境変数管理
  - pydantic: データバリデーション
  - sqlite3: ダウンロード履歴管理（標準ライブラリ）

## 2. アーキテクチャ設計

### 2.1 ディレクトリ構造
```
civitiai/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py          # Civitai APIクライアント
│   │   └── models.py          # APIレスポンスモデル
│   ├── core/
│   │   ├── __init__.py
│   │   ├── downloader.py      # ダウンロード処理
│   │   ├── filter.py          # モデルフィルタリング
│   │   ├── cache.py           # キャッシュ管理
│   │   ├── history.py         # ダウンロード履歴管理
│   │   └── url_collector.py   # URL収集・出力
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py    # ファイル操作
│   │   ├── logger.py          # ロギング
│   │   └── progress.py        # 進捗表示
│   └── cli/
│       ├── __init__.py
│       └── main.py            # CLIエントリーポイント
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_downloader.py
│   └── test_filter.py
├── docs/
│   ├── installation.md
│   ├── usage.md
│   └── api_setup.md
├── models/                    # ダウンロードディレクトリ
│   ├── checkpoints/
│   └── loras/
├── cache/                     # キャッシュディレクトリ
├── data/                      # データベースディレクトリ
│   └── history.db            # ダウンロード履歴データベース
├── outputs/                   # 出力ファイルディレクトリ
│   ├── urls/                 # URLリスト出力
│   └── reports/              # レポート出力
├── logs/                      # ログディレクトリ
├── .env.example
├── requirements.txt
├── setup.py
├── README.md
└── config.yaml               # 設定ファイル
```

### 2.2 主要コンポーネント

#### 2.2.1 APIクライアント (api/client.py)
```python
class CivitaiClient:
    - __init__(api_key: str)
    - search_models(params: dict) -> List[Model]
    - get_model_details(model_id: int) -> Model
    - download_model(version_id: int) -> Response
```

#### 2.2.2 ダウンローダー (core/downloader.py)
```python
class ModelDownloader:
    - download_file(url: str, dest: Path) -> Path
    - batch_download(models: List[Model])
    - resume_download(partial_file: Path)
```

#### 2.2.3 フィルター (core/filter.py)
```python
class ModelFilter:
    - filter_lora_models(models: List[Model]) -> List[Model]
    - has_required_tags(model: Model) -> bool
    - remove_duplicates(models: List[Model]) -> List[Model]
```

#### 2.2.4 履歴管理 (core/history.py)
```python
class DownloadHistory:
    - __init__(db_path: Path)
    - add_download(model: Model, file_path: Path)
    - is_downloaded(model_id: int, version_id: int) -> bool
    - get_download_info(model_id: int) -> DownloadRecord
    - list_downloads(filter_params: dict) -> List[DownloadRecord]
    - cleanup_orphaned_records()
```

#### 2.2.5 URL収集 (core/url_collector.py)
```python
class URLCollector:
    - __init__(output_dir: Path)
    - collect_model_urls(models: List[Model]) -> List[URLInfo]
    - export_to_text(urls: List[URLInfo], filename: str)
    - export_to_csv(urls: List[URLInfo], filename: str)
    - export_to_json(urls: List[URLInfo], filename: str)
```

## 3. 実装フェーズ

### Phase 1: 基盤構築（2日）
- [x] プロジェクト構造の作成
- [ ] 開発環境のセットアップ
- [ ] 基本的な設定管理システム
- [ ] ロギングシステムの実装

### Phase 2: API統合（3日）
- [ ] Civitai APIクライアントの実装
- [ ] 認証機能の実装
- [ ] モデル検索機能の実装
- [ ] エラーハンドリングとリトライロジック

### Phase 3: コア機能実装（3日）
- [ ] モデルフィルタリング機能
- [ ] URL収集機能（URLCollector）
- [ ] ダウンロード機能（プログレス表示付き）
- [ ] キャッシュシステム
- [ ] 履歴管理システム（SQLite）
- [ ] 中断・再開機能

### Phase 4: CLI開発（1日）
- [ ] コマンドライン引数パーサー
- [ ] 対話的モードの実装
- [ ] バッチ実行モード
- [ ] 進捗表示UI

### Phase 5: テストとドキュメント（1日）
- [ ] ユニットテストの作成
- [ ] 統合テストの実施
- [ ] ドキュメントの作成
- [ ] サンプルスクリプトの作成

## 4. 詳細タスクリスト

### 4.1 Week 1
**Day 1-2: 基盤構築**
- プロジェクト初期化
- 依存関係の設定
- 基本クラス構造の実装
- 設定ファイル読み込み機能

**Day 3-5: API統合**
- APIクライアントクラスの実装
- 検索エンドポイントの統合
- レート制限対策の実装
- エラーハンドリング

### 4.2 Week 2
**Day 6-8: コア機能**
- タグベースフィルタリング
- ダウンロード管理
- ファイル整合性チェック
- SQLiteデータベース設計・実装
- 履歴管理機能の統合
- メタデータ保存

**Day 9: CLI開発**
- Click frameworkでのCLI構築
- Rich libraryでの進捗表示
- 設定ウィザード

**Day 10: 仕上げ**
- テスト実行
- ドキュメント整備
- パッケージング

## 5. 技術的実装詳細

### 5.1 API通信
```python
# レート制限対策
class RateLimiter:
    def __init__(self, calls_per_second=0.5):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
    
    def wait_if_needed(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
```

### 5.2 フィルタリング実装
```python
def filter_lora_by_tags(model: dict) -> bool:
    """LoRAモデルが必要なタグ条件を満たすかチェック"""
    required_base_tags = {'pony', 'illustrious', 'noobai'}
    required_type_tags = {'style', 'concept'}
    
    model_tags = {tag.lower() for tag in model.get('tags', [])}
    
    has_base_tag = bool(required_base_tags & model_tags)
    has_type_tag = bool(required_type_tags & model_tags)
    
    return has_base_tag and has_type_tag
```

### 5.3 ダウンロード再開機能
```python
def resume_download(url: str, partial_file: Path, headers: dict):
    """部分的にダウンロードされたファイルを再開"""
    file_size = partial_file.stat().st_size
    headers['Range'] = f'bytes={file_size}-'
    
    response = requests.get(url, headers=headers, stream=True)
    # ステータスコード206は部分的コンテンツを示す
    if response.status_code == 206:
        with open(partial_file, 'ab') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
```

### 5.4 ダウンロード履歴管理（SQLite実装）
```python
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

class DownloadHistory:
    """SQLiteを使用したダウンロード履歴管理"""
    
    def __init__(self, db_path: Path = Path("data/history.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """データベースの初期化とテーブル作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    version_id INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,  -- JSON形式で保存
                    creator TEXT,
                    civitai_url TEXT,
                    status TEXT DEFAULT 'completed',
                    UNIQUE(model_id, version_id)
                )
            ''')
            
            # インデックスの作成
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_model_id 
                ON download_history(model_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_download_date 
                ON download_history(download_date)
            ''')
            conn.commit()
    
    def add_download(self, model: dict, file_path: Path) -> int:
        """ダウンロード記録の追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO download_history 
                (model_id, version_id, model_name, model_type, 
                 file_path, file_size, tags, creator, civitai_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model['id'],
                model['modelVersions'][0]['id'],
                model['name'],
                model['type'],
                str(file_path),
                file_path.stat().st_size if file_path.exists() else None,
                json.dumps(model.get('tags', [])),
                model['creator']['username'],
                f"https://civitai.com/models/{model['id']}"
            ))
            conn.commit()
            return cursor.lastrowid
    
    def is_downloaded(self, model_id: int, version_id: int) -> bool:
        """モデルがダウンロード済みか確認"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_path FROM download_history
                WHERE model_id = ? AND version_id = ? AND status = 'completed'
            ''', (model_id, version_id))
            result = cursor.fetchone()
            
            # ファイルの実体も確認
            if result:
                file_path = Path(result[0])
                return file_path.exists()
            return False
    
    def get_download_info(self, model_id: int) -> Optional[Dict]:
        """モデルのダウンロード情報を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM download_history
                WHERE model_id = ?
                ORDER BY download_date DESC
                LIMIT 1
            ''', (model_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_downloads(self, 
                      model_type: Optional[str] = None,
                      days_ago: Optional[int] = None) -> List[Dict]:
        """ダウンロード履歴の一覧取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM download_history WHERE 1=1"
            params = []
            
            if model_type:
                query += " AND model_type = ?"
                params.append(model_type)
            
            if days_ago:
                query += " AND download_date >= datetime('now', ?)"
                params.append(f'-{days_ago} days')
            
            query += " ORDER BY download_date DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_orphaned_records(self):
        """ファイルが存在しない記録を削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path FROM download_history")
            
            orphaned_ids = []
            for row in cursor.fetchall():
                if not Path(row[1]).exists():
                    orphaned_ids.append(row[0])
            
            if orphaned_ids:
                placeholders = ','.join('?' * len(orphaned_ids))
                cursor.execute(
                    f"DELETE FROM download_history WHERE id IN ({placeholders})",
                    orphaned_ids
                )
                conn.commit()
                print(f"削除された孤立レコード: {len(orphaned_ids)}件")

# 使用例
history = DownloadHistory()

# ダウンロード前のチェック
if not history.is_downloaded(model_id=12345, version_id=67890):
    # ダウンロード処理
    file_path = download_model(model)
    history.add_download(model, file_path)

# 履歴の確認
recent_downloads = history.list_downloads(model_type="LORA", days_ago=7)
for download in recent_downloads:
    print(f"{download['model_name']} - {download['download_date']}")
```

### 5.5 履歴管理の活用方法

#### 再ダウンロード防止
```python
def should_download(model: dict, history: DownloadHistory) -> bool:
    """モデルをダウンロードすべきか判定"""
    version_id = model['modelVersions'][0]['id']
    
    # 既にダウンロード済みか確認
    if history.is_downloaded(model['id'], version_id):
        logger.info(f"スキップ: {model['name']} (既にダウンロード済み)")
        return False
    
    # ファイルサイズとディスク容量のチェック
    if not check_disk_space(model):
        return False
    
    return True
```

#### CLI統合例
```python
@click.command()
@click.option('--list-history', is_flag=True, help='ダウンロード履歴を表示')
@click.option('--cleanup', is_flag=True, help='孤立した履歴を削除')
def main(list_history, cleanup):
    history = DownloadHistory()
    
    if list_history:
        downloads = history.list_downloads()
        console = Console()
        table = Table(title="ダウンロード履歴")
        table.add_column("モデル名", style="cyan")
        table.add_column("タイプ", style="magenta")
        table.add_column("ダウンロード日", style="green")
        table.add_column("ファイルパス", style="yellow")
        
        for dl in downloads:
            table.add_row(
                dl['model_name'],
                dl['model_type'],
                dl['download_date'],
                dl['file_path']
            )
        console.print(table)
    
    elif cleanup:
        history.cleanup_orphaned_records()
```

### 5.6 URL収集とダウンロード制御

#### 環境変数による動作モード切り替え（.env）
```bash
# Civitai API設定
CIVITAI_API_KEY=your_api_key_here

# 動作モード設定
# DOWNLOAD_ENABLED: true/false（デフォルト: false）
# falseの場合、URL収集のみ実行
DOWNLOAD_ENABLED=false

# 出力設定
OUTPUT_FORMAT=csv  # text, csv, json から選択
OUTPUT_DIR=./outputs/urls

# ダウンロード設定（DOWNLOAD_ENABLED=true の場合のみ有効）
DOWNLOAD_DIR=./models
MAX_CONCURRENT_DOWNLOADS=1
DOWNLOAD_TIMEOUT=300  # 秒
```

#### URLCollector実装
```python
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, NamedTuple

class URLInfo(NamedTuple):
    """URL情報を格納するデータクラス"""
    model_id: int
    version_id: int
    model_name: str
    model_type: str
    download_url: str
    file_size: int
    tags: List[str]
    creator: str
    civitai_url: str

class URLCollector:
    """モデルURLの収集と出力を管理"""
    
    def __init__(self, output_dir: Path = Path("outputs/urls")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_model_urls(self, models: List[dict]) -> List[URLInfo]:
        """モデルリストからURL情報を収集"""
        urls = []
        
        for model in models:
            if not model.get('modelVersions'):
                continue
                
            version = model['modelVersions'][0]
            url_info = URLInfo(
                model_id=model['id'],
                version_id=version['id'],
                model_name=model['name'],
                model_type=model['type'],
                download_url=f"https://civitai.com/api/download/models/{version['id']}",
                file_size=version.get('files', [{}])[0].get('sizeKB', 0) * 1024,
                tags=model.get('tags', []),
                creator=model['creator']['username'],
                civitai_url=f"https://civitai.com/models/{model['id']}"
            )
            urls.append(url_info)
        
        return urls
    
    def export_to_text(self, urls: List[URLInfo], filename: str = None) -> Path:
        """URLリストをテキストファイルに出力"""
        if filename is None:
            filename = f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Civitai Model URLs - Generated at {datetime.now()}\n")
            f.write(f"# Total models: {len(urls)}\n\n")
            
            for url in urls:
                f.write(f"# {url.model_name} ({url.model_type})\n")
                f.write(f"# Tags: {', '.join(url.tags[:5])}\n")
                f.write(f"{url.download_url}\n\n")
        
        return file_path
    
    def export_to_csv(self, urls: List[URLInfo], filename: str = None) -> Path:
        """URLリストをCSVファイルに出力"""
        if filename is None:
            filename = f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'model_id', 'version_id', 'model_name', 'model_type',
                'download_url', 'file_size_mb', 'tags', 'creator', 'civitai_url'
            ])
            
            for url in urls:
                writer.writerow([
                    url.model_id,
                    url.version_id,
                    url.model_name,
                    url.model_type,
                    url.download_url,
                    f"{url.file_size / (1024 * 1024):.2f}",
                    ', '.join(url.tags),
                    url.creator,
                    url.civitai_url
                ])
        
        return file_path
    
    def export_to_json(self, urls: List[URLInfo], filename: str = None) -> Path:
        """URLリストをJSONファイルに出力"""
        if filename is None:
            filename = f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        file_path = self.output_dir / filename
        
        data = {
            'generated_at': datetime.now().isoformat(),
            'total_models': len(urls),
            'models': [url._asdict() for url in urls]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return file_path
```

#### メインワークフローの実装
```python
import os
from dotenv import load_dotenv

def main():
    """メインワークフロー"""
    # 環境変数の読み込み
    load_dotenv()
    
    api_key = os.getenv('CIVITAI_API_KEY')
    download_enabled = os.getenv('DOWNLOAD_ENABLED', 'false').lower() == 'true'
    output_format = os.getenv('OUTPUT_FORMAT', 'csv')
    
    # APIクライアントの初期化
    client = CivitaiClient(api_key)
    filter = ModelFilter()
    
    # モデルの検索
    print("モデルを検索中...")
    checkpoints = client.search_checkpoints()
    loras = filter.search_loras_with_filters()
    
    all_models = checkpoints + loras
    print(f"合計 {len(all_models)} 個のモデルが見つかりました")
    
    # URL収集
    collector = URLCollector()
    urls = collector.collect_model_urls(all_models)
    
    # URLリストの出力
    print(f"\nURLリストを{output_format}形式で出力中...")
    if output_format == 'text':
        output_file = collector.export_to_text(urls)
    elif output_format == 'csv':
        output_file = collector.export_to_csv(urls)
    elif output_format == 'json':
        output_file = collector.export_to_json(urls)
    else:
        print(f"不明な出力形式: {output_format}")
        return
    
    print(f"URLリストを保存しました: {output_file}")
    
    # ダウンロード処理（有効な場合のみ）
    if download_enabled:
        print("\nダウンロードモードが有効です")
        downloader = ModelDownloader()
        history = DownloadHistory()
        
        for model in all_models:
            if should_download(model, history):
                print(f"\nダウンロード中: {model['name']}")
                downloader.download_model(model)
                time.sleep(2)  # レート制限対策
    else:
        print("\nダウンロードモードは無効です（URL収集のみ）")
        print("ダウンロードを有効にするには、.envファイルで DOWNLOAD_ENABLED=true を設定してください")

if __name__ == "__main__":
    main()
```

## 6. リスク管理

### 6.1 技術的リスク
| リスク | 影響度 | 対策 |
|--------|--------|------|
| API仕様変更 | 高 | バージョニング対応、エラー通知 |
| レート制限 | 中 | 適応的な待機時間、リトライロジック |
| 大容量ファイル | 中 | チャンク転送、再開機能 |

### 6.2 運用リスク
| リスク | 影響度 | 対策 |
|--------|--------|------|
| ディスク容量不足 | 高 | 事前チェック、警告表示 |
| ネットワーク断絶 | 中 | 自動再試行、状態保存 |

## 7. 成果物

### 7.1 プログラム
- Pythonパッケージ（pip installable）
- スタンドアロン実行ファイル（PyInstaller）

### 7.2 ドキュメント
- インストールガイド（日本語）
- 使用方法マニュアル
- APIキー取得手順書
- トラブルシューティングガイド

### 7.3 サンプル
- 基本的な使用例
- バッチダウンロードスクリプト
- カスタムフィルター例

## 8. 今後の拡張計画

### Version 2.0
- Web UI の追加
- スケジュール実行機能
- モデル更新通知
- 複数APIキー対応

### Version 3.0
- クラウドストレージ連携
- モデル管理データベース
- 自動バックアップ機能
- プラグインシステム