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
    
    def __init__(self, output_dir: Path = None):
        """
        URLCollectorを初期化
        
        Args:
            output_dir: 出力ディレクトリのパス。Noneの場合はデフォルト値を使用
        """
        if output_dir is None:
            output_dir = Path("outputs/urls")
        
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_model_urls(self, models: List[dict]) -> List[URLInfo]:
        """
        モデルリストからURL情報を収集
        
        Args:
            models: モデル情報のリスト
            
        Returns:
            URLInfo のリスト
        """
        urls = []
        
        for model in models:
            try:
                # modelVersionsの存在確認
                if not model.get('modelVersions'):
                    continue
                
                version = model['modelVersions'][0]
                
                # filesの存在確認
                files = version.get('files', [])
                if not files:
                    continue
                
                # ファイルサイズの計算 (KB to bytes)
                file_size_kb = files[0].get('sizeKB', 0)
                file_size_bytes = file_size_kb * 1024
                
                url_info = URLInfo(
                    model_id=model['id'],
                    version_id=version['id'],
                    model_name=model['name'],
                    model_type=model['type'],
                    download_url=f"https://civitai.com/api/download/models/{version['id']}",
                    file_size=file_size_bytes,
                    tags=model.get('tags', []),
                    creator=model['creator']['username'],
                    civitai_url=f"https://civitai.com/models/{model['id']}"
                )
                urls.append(url_info)
                
            except (KeyError, IndexError, TypeError):
                # 不正なデータは無視して続行
                continue
        
        return urls
    
    def export_to_text(self, urls: List[URLInfo], filename: str = None) -> Path:
        """
        URLリストをテキストファイルに出力
        
        Args:
            urls: URLInfoのリスト
            filename: 出力ファイル名。Noneの場合は自動生成
            
        Returns:
            出力ファイルのパス
        """
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
        """
        URLリストをCSVファイルに出力
        
        Args:
            urls: URLInfoのリスト
            filename: 出力ファイル名。Noneの場合は自動生成
            
        Returns:
            出力ファイルのパス
        """
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
        """
        URLリストをJSONファイルに出力
        
        Args:
            urls: URLInfoのリスト
            filename: 出力ファイル名。Noneの場合は自動生成
            
        Returns:
            出力ファイルのパス
        """
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