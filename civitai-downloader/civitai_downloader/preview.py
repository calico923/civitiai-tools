"""Model preview and details display system."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import re

import aiohttp
from PIL import Image
import io

from .interfaces import (
    IPreviewManager, IAPIClient, ModelInfo, ModelVersion, ModelImage,
    ModelType, ModelFile
)
from .config import ConfigManager


class PreviewManager(IPreviewManager):
    """Manager for model previews and details display."""
    
    def __init__(self, api_client: Optional[IAPIClient] = None, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.api_client = api_client
        self._owned_client = False
        
        # If no client provided, we'll create our own
        if not self.api_client:
            from .api_client import CivitAIAPIClient
            self.api_client = CivitAIAPIClient(self.config)
            self._owned_client = True
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self._owned_client:
            await self.api_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owned_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_preview_images(self, model: ModelInfo, size: int = 512) -> List[ModelImage]:
        """Get preview images for a model with optional size filtering."""
        try:
            # Get model versions to access images
            versions = await self.api_client.get_model_versions(model.id)
            
            all_images = []
            for version in versions:
                for image in version.images:
                    # Filter by size if specified
                    if size > 0:
                        # Allow some tolerance for size matching
                        tolerance = 0.2  # 20% tolerance
                        min_size = size * (1 - tolerance)
                        max_size = size * (1 + tolerance)
                        
                        if image.width < min_size or image.width > max_size:
                            continue
                    
                    all_images.append(image)
            
            # Sort by size (largest first) and limit to reasonable number
            all_images.sort(key=lambda img: img.width * img.height, reverse=True)
            return all_images[:10]  # Limit to 10 images
            
        except Exception as e:
            print(f"Error fetching preview images: {e}")
            return []
    
    async def download_image(self, image: ModelImage, path: Path, size: Optional[int] = None) -> None:
        """Download and optionally resize preview image."""
        try:
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download image using the existing API client's session if available
            if hasattr(self.api_client, 'session') and self.api_client.session:
                response = await self.api_client.session.get(image.url)
                response.raise_for_status()
                image_data = await response.read()
            else:
                # Fallback to creating our own session
                async with aiohttp.ClientSession() as session:
                    async with session.get(image.url) as response:
                        response.raise_for_status()
                        image_data = await response.read()
            
            # Resize if requested
            if size:
                # Load image with PIL
                pil_image = Image.open(io.BytesIO(image_data))
                
                # Calculate new size maintaining aspect ratio
                width, height = pil_image.size
                if width > height:
                    new_width = size
                    new_height = int(height * (size / width))
                else:
                    new_height = size
                    new_width = int(width * (size / height))
                
                # Resize image
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                pil_image.save(path, format='PNG', optimize=True)
            else:
                # Save original image
                with open(path, 'wb') as f:
                    f.write(image_data)
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            raise
    
    def display_model_info(self, model: ModelInfo, version: Optional[ModelVersion] = None) -> None:
        """Display comprehensive model information in terminal."""
        print("=" * 80)
        print(f"📦 {model.name} (ID: {model.id})")
        print("=" * 80)
        
        # Basic information
        print(f"🏷️  Type: {model.type.value}")
        print(f"👤 Creator: {model.creator}")
        print(f"📅 Created: {model.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Updated: {model.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # NSFW indicator
        if model.nsfw:
            print("🔞 NSFW: Yes")
        else:
            print("✅ NSFW: No")
        
        # Description
        if model.description:
            print(f"\n📝 Description:")
            print(self._format_text(model.description, indent=4))
        
        # Tags
        if model.tags:
            print(f"\n🏷️  Tags: {', '.join(model.tags[:10])}")
            if len(model.tags) > 10:
                print(f"   ... and {len(model.tags) - 10} more")
        
        # Statistics
        if model.stats:
            print(f"\n📊 Statistics:")
            stats = model.stats
            if 'downloadCount' in stats:
                print(f"    📥 Downloads: {stats['downloadCount']:,}")
            if 'favoriteCount' in stats:
                print(f"    ❤️  Favorites: {stats['favoriteCount']:,}")
            if 'commentCount' in stats:
                print(f"    💬 Comments: {stats['commentCount']:,}")
            if 'rating' in stats and 'ratingCount' in stats:
                print(f"    ⭐ Rating: {stats['rating']:.1f}/5 ({stats['ratingCount']} votes)")
        
        # Version information
        if version:
            print(f"\n🔄 Version: {version.name}")
            if version.description:
                print(f"    📝 Description: {version.description}")
            if version.base_model:
                print(f"    🏗️  Base Model: {version.base_model}")
            if version.trained_words:
                print(f"    🔤 Trained Words: {', '.join(version.trained_words)}")
            
            # Files information
            if version.files:
                print(f"\n📁 Files ({len(version.files)}):")
                for i, file in enumerate(version.files, 1):
                    size_mb = file.size_bytes / (1024 * 1024)
                    print(f"    {i}. {file.name}")
                    print(f"       📏 Size: {size_mb:.1f} MB")
                    print(f"       📄 Format: {file.format}")
                    if file.fp:
                        print(f"       🎯 Precision: {file.fp}")
                    if file.hash:
                        print(f"       🔐 Hash: {file.hash[:16]}...")
            
            # Images information
            if version.images:
                print(f"\n🖼️  Sample Images ({len(version.images)}):")
                for i, img in enumerate(version.images[:5], 1):  # Show first 5
                    print(f"    {i}. {img.width}x{img.height} pixels")
                    if img.nsfw:
                        print(f"       🔞 NSFW: Yes")
                    if img.meta:
                        self._display_image_metadata(img.meta, indent=7)
                if len(version.images) > 5:
                    print(f"    ... and {len(version.images) - 5} more images")
        
        print("=" * 80)
    
    def display_model_comparison(self, models: List[Tuple[ModelInfo, Optional[ModelVersion]]]) -> None:
        """Display comparison of multiple models."""
        if not models:
            return
        
        print("=" * 120)
        print("🔍 MODEL COMPARISON")
        print("=" * 120)
        
        # Header
        print(f"{'Model':<30} {'Type':<15} {'Creator':<20} {'Downloads':<12} {'Rating':<10} {'Updated':<12}")
        print("-" * 120)
        
        for model, version in models:
            downloads = model.stats.get('downloadCount', 0) if model.stats else 0
            rating = model.stats.get('rating', 0) if model.stats else 0
            rating_str = f"{rating:.1f}" if rating > 0 else "N/A"
            updated = model.updated_at.strftime('%Y-%m-%d')
            
            print(f"{model.name[:29]:<30} {model.type.value:<15} {model.creator[:19]:<20} "
                  f"{downloads:<12,} {rating_str:<10} {updated:<12}")
        
        print("=" * 120)
    
    def display_license_info(self, model: ModelInfo, version: Optional[ModelVersion] = None) -> None:
        """Display detailed license information."""
        print("\n⚖️  LICENSE INFORMATION")
        print("-" * 40)
        
        # This is a simplified version - in practice, you'd need to fetch
        # license information from the API or model metadata
        print("📋 License Type: Check model page for details")
        print("💼 Commercial Use: Check model page for restrictions")
        print("🔄 Derivatives: Check model page for permissions")
        print("📝 Credit Requirements: Check model page for attribution")
        print("🔗 Full License: Visit CivitAI model page for complete terms")
        
        # Note: CivitAI doesn't provide structured license info in the API
        # This would need to be enhanced with actual license data
        print("\n⚠️  Note: Always verify license terms on the original model page")
    
    def _format_text(self, text: str, width: int = 76, indent: int = 0) -> str:
        """Format text with word wrapping and indentation."""
        if not text:
            return ""
        
        # Clean up text
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' ' * indent + ' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' ' * indent + ' '.join(current_line))
        
        return '\n'.join(lines)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def _display_image_metadata(self, metadata: Dict[str, Any], indent: int = 0) -> None:
        """Display image generation metadata."""
        if not metadata:
            return
        
        prefix = ' ' * indent
        
        # Common metadata fields
        if 'prompt' in metadata and metadata['prompt']:
            prompt = metadata['prompt']
            if len(prompt) > 100:
                prompt = prompt[:100] + "..."
            print(f"{prefix}📝 Prompt: {prompt}")
        
        if 'negativePrompt' in metadata and metadata['negativePrompt']:
            neg_prompt = metadata['negativePrompt']
            if len(neg_prompt) > 100:
                neg_prompt = neg_prompt[:100] + "..."
            print(f"{prefix}🚫 Negative: {neg_prompt}")
        
        if 'seed' in metadata and metadata['seed'] is not None:
            print(f"{prefix}🌱 Seed: {metadata['seed']}")
        
        if 'cfgScale' in metadata and metadata['cfgScale'] is not None:
            print(f"{prefix}⚙️  CFG Scale: {metadata['cfgScale']}")
        
        if 'steps' in metadata and metadata['steps'] is not None:
            print(f"{prefix}🔄 Steps: {metadata['steps']}")
        
        if 'sampler' in metadata and metadata['sampler']:
            print(f"{prefix}🎲 Sampler: {metadata['sampler']}")
        
        if 'model' in metadata and metadata['model']:
            print(f"{prefix}🏗️  Model: {metadata['model']}")
        
        # Extended metadata fields
        if 'clipSkip' in metadata and metadata['clipSkip'] is not None:
            print(f"{prefix}✂️  Clip Skip: {metadata['clipSkip']}")
        
        if 'denoisingStrength' in metadata and metadata['denoisingStrength'] is not None:
            print(f"{prefix}🔧 Denoising: {metadata['denoisingStrength']}")
    
    async def get_model_details_with_versions(self, model_id: int) -> Tuple[ModelInfo, List[ModelVersion]]:
        """Get comprehensive model details including all versions."""
        try:
            # Get model details and versions
            model = await self.api_client.get_model_details(model_id)
            versions = await self.api_client.get_model_versions(model_id)
            
            return model, versions
            
        except Exception as e:
            print(f"Error fetching model details: {e}")
            raise
    
    async def save_model_metadata(self, model: ModelInfo, versions: List[ModelVersion], path: Path) -> None:
        """Save model metadata to JSON file for offline access."""
        try:
            # Create metadata structure
            metadata = {
                'model': {
                    'id': model.id,
                    'name': model.name,
                    'type': model.type.value,
                    'description': model.description,
                    'tags': model.tags,
                    'creator': model.creator,
                    'stats': model.stats,
                    'nsfw': model.nsfw,
                    'created_at': model.created_at.isoformat(),
                    'updated_at': model.updated_at.isoformat()
                },
                'versions': [],
                'saved_at': datetime.now().isoformat()
            }
            
            # Add version information
            for version in versions:
                version_data = {
                    'id': version.id,
                    'name': version.name,
                    'description': version.description,
                    'base_model': version.base_model,
                    'trained_words': version.trained_words,
                    'download_url': version.download_url,
                    'created_at': version.created_at.isoformat(),
                    'files': [],
                    'images': []
                }
                
                # Add file information
                for file in version.files:
                    file_data = {
                        'id': file.id,
                        'name': file.name,
                        'size_bytes': file.size_bytes,
                        'format': file.format,
                        'fp': file.fp,
                        'hash': file.hash,
                        'download_url': file.download_url,
                        'metadata': file.metadata
                    }
                    version_data['files'].append(file_data)
                
                # Add image information
                for image in version.images:
                    image_data = {
                        'id': image.id,
                        'url': image.url,
                        'width': image.width,
                        'height': image.height,
                        'hash': image.hash,
                        'nsfw': image.nsfw,
                        'meta': image.meta
                    }
                    version_data['images'].append(image_data)
                
                metadata['versions'].append(version_data)
            
            # Save metadata
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Error saving metadata: {e}")
            raise
    
    def load_model_metadata(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load model metadata from JSON file."""
        try:
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return None