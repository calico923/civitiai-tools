#!/usr/bin/env python3
"""
Enhanced URL collector that includes both download URLs and model page URLs
with validation capabilities.
"""

import csv
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, NamedTuple, Optional
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Enhanced model information including both download and page URLs."""
    model_id: int
    version_id: int
    model_name: str
    model_type: str
    download_url: str
    civitai_page_url: str
    file_size: int
    file_size_mb: float
    tags: List[str]
    creator: str
    creator_url: str
    description: str
    rating: Optional[float]
    download_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    nsfw: bool
    base_model: Optional[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'model_id': self.model_id,
            'version_id': self.version_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'download_url': self.download_url,
            'civitai_page_url': self.civitai_page_url,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'tags': self.tags,
            'creator': self.creator,
            'creator_url': self.creator_url,
            'description': self.description[:200] + '...' if len(self.description) > 200 else self.description,
            'rating': self.rating,
            'download_count': self.download_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'nsfw': self.nsfw,
            'base_model': self.base_model
        }


class EnhancedURLCollector:
    """Enhanced URL collector with page URLs and validation capabilities."""
    
    def __init__(self, output_dir: Path = None, api_key: str = None):
        """
        Initialize Enhanced URL Collector.
        
        Args:
            output_dir: Output directory path
            api_key: CivitAI API key for validation requests
        """
        if output_dir is None:
            output_dir = Path("outputs/enhanced_urls")
        
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        
        # Setup session for validation requests
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def collect_enhanced_model_info(self, models: List[Dict]) -> List[ModelInfo]:
        """
        Collect enhanced model information including both URLs.
        
        Args:
            models: List of model data from API
            
        Returns:
            List of ModelInfo objects
        """
        model_infos = []
        
        for model in models:
            try:
                # Extract basic model information
                model_id = model.get('id')
                model_name = model.get('name', 'Unknown')
                model_type = model.get('type', 'Unknown')
                tags = model.get('tags', [])
                
                # Creator information
                creator_info = model.get('creator', {})
                creator_name = creator_info.get('username', 'Unknown')
                creator_url = f"https://civitai.com/user/{creator_name}" if creator_name != 'Unknown' else ''
                
                # Model statistics
                stats = model.get('stats', {})
                rating = stats.get('rating')
                download_count = stats.get('downloadCount')
                like_count = stats.get('favoriteCount')
                comment_count = stats.get('commentCount')
                
                # Model metadata
                description = model.get('description', '')
                nsfw = model.get('nsfw', False)
                created_at = model.get('createdAt')
                updated_at = model.get('updatedAt')
                
                # Process model versions
                model_versions = model.get('modelVersions', [])
                if not model_versions:
                    continue
                
                # Use the first (latest) version
                version = model_versions[0]
                version_id = version.get('id')
                base_model = version.get('baseModel')
                
                # Get file information
                files = version.get('files', [])
                if not files:
                    continue
                
                # Use the first file (usually the main model file)
                main_file = files[0]
                file_size_kb = main_file.get('sizeKB', 0)
                file_size_bytes = file_size_kb * 1024
                file_size_mb = round(file_size_kb / 1024, 2)
                
                # Generate URLs
                download_url = f"https://civitai.com/api/download/models/{version_id}"
                civitai_page_url = f"https://civitai.com/models/{model_id}"
                
                model_info = ModelInfo(
                    model_id=model_id,
                    version_id=version_id,
                    model_name=model_name,
                    model_type=model_type,
                    download_url=download_url,
                    civitai_page_url=civitai_page_url,
                    file_size=file_size_bytes,
                    file_size_mb=file_size_mb,
                    tags=tags,
                    creator=creator_name,
                    creator_url=creator_url,
                    description=description,
                    rating=rating,
                    download_count=download_count,
                    like_count=like_count,
                    comment_count=comment_count,
                    created_at=created_at,
                    updated_at=updated_at,
                    nsfw=nsfw,
                    base_model=base_model
                )
                
                model_infos.append(model_info)
                
            except (KeyError, IndexError, TypeError) as e:
                print(f"Error processing model {model.get('id', 'unknown')}: {e}")
                continue
        
        return model_infos
    
    def validate_download_urls(self, model_infos: List[ModelInfo], 
                             max_concurrent: int = 5) -> List[ModelInfo]:
        """
        Validate that download URLs are accessible.
        
        Args:
            model_infos: List of ModelInfo objects
            max_concurrent: Maximum concurrent validation requests
            
        Returns:
            List of ModelInfo objects with valid download URLs
        """
        if not self.api_key:
            print("Warning: No API key provided, skipping URL validation")
            return model_infos
        
        print(f"Validating {len(model_infos)} download URLs...")
        valid_models = []
        
        for i, model_info in enumerate(model_infos):
            try:
                # Make HEAD request to check if URL is accessible
                response = self.session.head(
                    model_info.download_url,
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    valid_models.append(model_info)
                    print(f"✓ Valid: {model_info.model_name}")
                else:
                    print(f"✗ Invalid ({response.status_code}): {model_info.model_name}")
                
                # Rate limiting
                if i % 10 == 0:
                    import time
                    time.sleep(1)
                    
            except requests.RequestException as e:
                print(f"✗ Error validating {model_info.model_name}: {e}")
                continue
        
        print(f"Validation complete: {len(valid_models)}/{len(model_infos)} URLs are valid")
        return valid_models
    
    def export_to_enhanced_csv(self, model_infos: List[ModelInfo], 
                              filename: str = None) -> Path:
        """
        Export model information to enhanced CSV format.
        
        Args:
            model_infos: List of ModelInfo objects
            filename: Output filename
            
        Returns:
            Path to the created file
        """
        if filename is None:
            filename = f"enhanced_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'model_id', 'version_id', 'model_name', 'model_type',
                'civitai_page_url', 'download_url', 'file_size_mb',
                'creator', 'creator_url', 'base_model', 'tags',
                'rating', 'download_count', 'like_count', 'nsfw',
                'description_preview', 'created_at'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for model_info in model_infos:
                writer.writerow({
                    'model_id': model_info.model_id,
                    'version_id': model_info.version_id,
                    'model_name': model_info.model_name,
                    'model_type': model_info.model_type,
                    'civitai_page_url': model_info.civitai_page_url,
                    'download_url': model_info.download_url,
                    'file_size_mb': model_info.file_size_mb,
                    'creator': model_info.creator,
                    'creator_url': model_info.creator_url,
                    'base_model': model_info.base_model,
                    'tags': ', '.join(model_info.tags),
                    'rating': model_info.rating,
                    'download_count': model_info.download_count,
                    'like_count': model_info.like_count,
                    'nsfw': model_info.nsfw,
                    'description_preview': model_info.description[:100] + '...' if len(model_info.description) > 100 else model_info.description,
                    'created_at': model_info.created_at
                })
        
        return file_path
    
    def export_to_enhanced_json(self, model_infos: List[ModelInfo], 
                               filename: str = None) -> Path:
        """
        Export model information to enhanced JSON format.
        
        Args:
            model_infos: List of ModelInfo objects
            filename: Output filename
            
        Returns:
            Path to the created file
        """
        if filename is None:
            filename = f"enhanced_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        file_path = self.output_dir / filename
        
        data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_models': len(model_infos),
                'format_version': '2.0'
            },
            'models': [model_info.to_dict() for model_info in model_infos]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def export_to_enhanced_html(self, model_infos: List[ModelInfo], 
                               filename: str = None) -> Path:
        """
        Export model information to browsable HTML format.
        
        Args:
            model_infos: List of ModelInfo objects
            filename: Output filename
            
        Returns:
            Path to the created file
        """
        if filename is None:
            filename = f"enhanced_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        file_path = self.output_dir / filename
        
        html_content = self._generate_html_content(model_infos)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return file_path
    
    def _generate_html_content(self, model_infos: List[ModelInfo]) -> str:
        """Generate HTML content for model information."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CivitAI Models Collection</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .model {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .model-title {{ font-size: 18px; font-weight: bold; color: #333; }}
                .model-meta {{ color: #666; font-size: 14px; margin: 5px 0; }}
                .tags {{ margin: 10px 0; }}
                .tag {{ background: #e0e0e0; padding: 2px 8px; border-radius: 3px; margin: 2px; display: inline-block; font-size: 12px; }}
                .urls {{ margin: 10px 0; }}
                .url-button {{ 
                    display: inline-block; margin: 5px 5px 5px 0; padding: 8px 15px; 
                    background: #007bff; color: white; text-decoration: none; 
                    border-radius: 3px; font-size: 14px;
                }}
                .url-button:hover {{ background: #0056b3; }}
                .download-btn {{ background: #28a745; }}
                .page-btn {{ background: #6f42c1; }}
                .creator-btn {{ background: #fd7e14; }}
                .stats {{ color: #555; font-size: 13px; }}
                .nsfw {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CivitAI Models Collection</h1>
                <p>Total models: {len(model_infos)}</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        for model_info in model_infos:
            html += f"""
            <div class="model">
                <div class="model-title">{model_info.model_name}</div>
                <div class="model-meta">
                    Type: {model_info.model_type} | 
                    Creator: {model_info.creator} | 
                    Size: {model_info.file_size_mb} MB
                    {' | <span class="nsfw">NSFW</span>' if model_info.nsfw else ''}
                </div>
                
                <div class="stats">
                    {f'★ {model_info.rating:.1f}' if model_info.rating else ''} |
                    {f'⬇ {model_info.download_count:,}' if model_info.download_count else ''} |
                    {f'♡ {model_info.like_count:,}' if model_info.like_count else ''}
                </div>
                
                <div class="urls">
                    <a href="{model_info.civitai_page_url}" class="url-button page-btn" target="_blank">View Page</a>
                    <a href="{model_info.download_url}" class="url-button download-btn" target="_blank">Download</a>
                    <a href="{model_info.creator_url}" class="url-button creator-btn" target="_blank">Creator</a>
                </div>
                
                <div class="tags">
                    {' '.join(f'<span class="tag">{tag}</span>' for tag in model_info.tags)}
                </div>
                
                {f'<p>{model_info.description[:200]}...</p>' if model_info.description else ''}
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def export_all_formats(self, model_infos: List[ModelInfo], 
                          base_filename: str = None) -> Dict[str, Path]:
        """
        Export model information to all available formats.
        
        Args:
            model_infos: List of ModelInfo objects
            base_filename: Base filename (without extension)
            
        Returns:
            Dictionary mapping format names to file paths
        """
        if base_filename is None:
            base_filename = f"enhanced_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {}
        
        results['csv'] = self.export_to_enhanced_csv(model_infos, f"{base_filename}.csv")
        results['json'] = self.export_to_enhanced_json(model_infos, f"{base_filename}.json")
        results['html'] = self.export_to_enhanced_html(model_infos, f"{base_filename}.html")
        
        return results