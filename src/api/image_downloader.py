"""CivitAI画像ダウンロード機能"""

import os
import requests
import time
from typing import List, Dict, Optional, Union
from urllib.parse import urlparse
import concurrent.futures
from pathlib import Path


class ImageDownloader:
    """CivitAI画像ダウンローダー"""
    
    def __init__(self, output_dir: str = "downloaded_images", max_workers: int = 3):
        """
        Args:
            output_dir: 画像保存先ディレクトリ
            max_workers: 並列ダウンロード数
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CivitaiModelDownloader/1.0'
        })
    
    def extract_image_info(self, image_url: str) -> Dict[str, str]:
        """
        画像URLから情報を抽出
        
        Args:
            image_url: CivitAI画像URL
            
        Returns:
            URLの構成要素
        """
        # URL例: https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/1c65dc07-2e32-4e76-a0b7-458c450ff1ae/width=1024/12221824.jpeg
        parts = image_url.split('/')
        
        info = {
            'url': image_url,
            'domain': parts[2] if len(parts) > 2 else '',
            'hash1': parts[3] if len(parts) > 3 else '',
            'hash2': parts[4] if len(parts) > 4 else '',
            'width': None,
            'filename': parts[-1] if len(parts) > 0 else '',
            'base_url': None
        }
        
        # 幅を抽出
        if 'width=' in image_url:
            info['width'] = image_url.split('width=')[1].split('/')[0]
            info['base_url'] = image_url.split('/width=')[0]
        
        return info
    
    def generate_sized_url(self, image_url: str, width: int) -> str:
        """
        指定した幅の画像URLを生成
        
        Args:
            image_url: オリジナル画像URL
            width: 希望する画像幅
            
        Returns:
            サイズ調整後のURL
        """
        info = self.extract_image_info(image_url)
        
        if info['base_url']:
            return f"{info['base_url']}/width={width}/{info['filename']}"
        
        return image_url
    
    def download_image(self, 
                      image_url: str, 
                      filename: Optional[str] = None,
                      width: Optional[int] = None,
                      subfolder: Optional[str] = None) -> Optional[str]:
        """
        単一画像をダウンロード
        
        Args:
            image_url: 画像URL
            filename: 保存ファイル名（Noneの場合は自動生成）
            width: 画像幅（Noneの場合はオリジナルサイズ）
            subfolder: サブフォルダ名
            
        Returns:
            保存先パス（失敗時はNone）
        """
        try:
            # サイズ調整
            if width:
                image_url = self.generate_sized_url(image_url, width)
            
            # ファイル名決定
            if not filename:
                info = self.extract_image_info(image_url)
                filename = info['filename']
                if not filename:
                    filename = f"image_{int(time.time())}.jpeg"
            
            # 保存先決定
            if subfolder:
                save_dir = self.output_dir / subfolder
                save_dir.mkdir(exist_ok=True)
            else:
                save_dir = self.output_dir
            
            filepath = save_dir / filename
            
            # 既存ファイルチェック
            if filepath.exists():
                print(f"スキップ: {filename} (既存)")
                return str(filepath)
            
            # ダウンロード
            print(f"ダウンロード中: {filename}")
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 保存
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"保存完了: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"ダウンロードエラー: {image_url} - {e}")
            return None
    
    def download_model_images(self, 
                            model_data: Dict,
                            max_images_per_version: int = 5,
                            width: Optional[int] = None) -> List[str]:
        """
        モデルの画像をダウンロード
        
        Args:
            model_data: モデルAPIレスポンスデータ
            max_images_per_version: 各バージョンの最大画像数
            width: 画像幅
            
        Returns:
            ダウンロードしたファイルパスのリスト
        """
        downloaded_files = []
        model_name = model_data.get('name', 'unknown').replace('/', '_')
        model_id = model_data.get('id', 'unknown')
        
        # モデル用サブフォルダ
        subfolder = f"{model_id}_{model_name}"
        
        # 各バージョンの画像を処理
        for version in model_data.get('modelVersions', []):
            version_name = version.get('name', 'unknown').replace('/', '_')
            images = version.get('images', [])[:max_images_per_version]
            
            for i, image in enumerate(images):
                image_url = image.get('url')
                if not image_url:
                    continue
                
                # ファイル名生成
                image_id = image.get('id', f"img_{i}")
                filename = f"{version_name}_{image_id}.jpeg"
                
                # ダウンロード
                filepath = self.download_image(
                    image_url=image_url,
                    filename=filename,
                    width=width,
                    subfolder=subfolder
                )
                
                if filepath:
                    downloaded_files.append(filepath)
                
                # レート制限
                time.sleep(0.5)
        
        return downloaded_files
    
    def download_images_batch(self,
                            image_urls: List[Union[str, Dict]],
                            width: Optional[int] = None,
                            subfolder: Optional[str] = None) -> List[str]:
        """
        複数画像を並列ダウンロード
        
        Args:
            image_urls: 画像URLのリスト（文字列または辞書）
            width: 画像幅
            subfolder: サブフォルダ名
            
        Returns:
            ダウンロードしたファイルパスのリスト
        """
        downloaded_files = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for item in image_urls:
                if isinstance(item, str):
                    url = item
                    filename = None
                elif isinstance(item, dict):
                    url = item.get('url')
                    filename = item.get('filename')
                else:
                    continue
                
                if url:
                    future = executor.submit(
                        self.download_image,
                        url,
                        filename,
                        width,
                        subfolder
                    )
                    futures.append(future)
            
            # 結果を収集
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    downloaded_files.append(result)
        
        return downloaded_files
    
    def download_from_images_api(self,
                               images_data: List[Dict],
                               width: Optional[int] = None,
                               include_meta: bool = True) -> List[Dict]:
        """
        /api/v1/imagesエンドポイントからの画像をダウンロード
        
        Args:
            images_data: 画像APIレスポンスのitemsリスト
            width: 画像幅
            include_meta: メタデータを保存するか
            
        Returns:
            ダウンロード結果のリスト
        """
        results = []
        
        for image in images_data:
            image_id = image.get('id')
            image_url = image.get('url')
            username = image.get('username', 'unknown')
            
            if not image_url:
                continue
            
            # ファイル名とサブフォルダ
            filename = f"{image_id}.jpeg"
            subfolder = f"user_{username}"
            
            # ダウンロード
            filepath = self.download_image(
                image_url=image_url,
                filename=filename,
                width=width,
                subfolder=subfolder
            )
            
            if filepath:
                result = {
                    'filepath': filepath,
                    'image_id': image_id,
                    'username': username,
                    'original_url': image_url
                }
                
                # メタデータ保存
                if include_meta and 'meta' in image:
                    meta_path = Path(filepath).with_suffix('.json')
                    import json
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(image['meta'], f, ensure_ascii=False, indent=2)
                    result['meta_path'] = str(meta_path)
                
                results.append(result)
            
            # レート制限
            time.sleep(0.5)
        
        return results


# 使用例
if __name__ == "__main__":
    # ダウンローダー初期化
    downloader = ImageDownloader(output_dir="test_downloads")
    
    # 単一画像のダウンロード
    image_url = "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/1c65dc07-2e32-4e76-a0b7-458c450ff1ae/width=1024/12221824.jpeg"
    
    # オリジナルサイズ
    downloader.download_image(image_url)
    
    # サムネイルサイズ
    downloader.download_image(image_url, filename="thumbnail.jpeg", width=256)
    
    # バッチダウンロード
    urls = [
        image_url,
        {"url": image_url, "filename": "custom_name.jpeg"}
    ]
    downloader.download_images_batch(urls, width=512)