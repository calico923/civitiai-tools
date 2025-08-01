#!/usr/bin/env python3
"""
Quick Download Script - Bypass complex initialization for simple filtering and download
"""

import asyncio
import sys
import logging
import json
import sqlite3
from pathlib import Path
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
log_file = Path(__file__).parent / 'logs' / 'civitai_debug.log'
log_file.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def quick_selective_download(
    output_dir: str = "/Volumes/Create-Images/Civitiai-download",
    model_type: str = "LORA",
    categories: Optional[List[str]] = None,
    base_models: Optional[List[str]] = None,
    max_models: int = 100,
    dry_run: bool = False,
    delay: float = 1.0
):
    """Quick selective download bypassing complex initialization."""
    
    logger.info(f"🚀 Starting quick selective download")
    logger.info(f"📁 Output directory: {output_dir}")
    logger.info(f"🎯 Model type: {model_type}")
    
    if model_type == "LORA" and categories:
        logger.info(f"🏷️  Categories: {', '.join(categories)}")
    elif model_type == "Checkpoint" and base_models:
        logger.info(f"🎨 Base models: {', '.join(base_models)}")
    
    logger.info(f"📊 Max models: {max_models}")
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be downloaded")
    
    # Direct database query
    try:
        db_path = Path(__file__).parent.parent / 'data' / 'civitai.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
        SELECT id, name, description, type, nsfw, creator_username, raw_data, created_at, updated_at
        FROM models
        WHERE type = ?
        """
        params = [model_type]
        
        # Add filtering
        if model_type == "LORA" and categories:
            tag_conditions = []
            for category in categories:
                tag_conditions.append("raw_data LIKE ?")
                params.append(f'%{category}%')
            
            if tag_conditions:
                query += f" AND ({' OR '.join(tag_conditions)})"
        
        elif model_type == "Checkpoint" and base_models:
            base_conditions = []
            for base_model in base_models:
                base_conditions.append("raw_data LIKE ?")
                params.append(f'%{base_model}%')
            
            if base_conditions:
                query += f" AND ({' OR '.join(base_conditions)})"
        
        query += """
        ORDER BY created_at DESC
        LIMIT ?
        """
        params.append(max_models)
        
        logger.info(f"📊 Executing query...")
        cursor.execute(query, params)
        models = cursor.fetchall()
        conn.close()
        
        logger.info(f"✅ Found {len(models)} models")
        
        if not models:
            logger.error("❌ No models found matching criteria")
            return
        
        # Sort by download count (Most Downloaded first)
        def get_download_count(model):
            try:
                import ast
                raw_data = ast.literal_eval(model[6]) if model[6] else {}
                return raw_data.get('stats', {}).get('downloadCount', 0)
            except:
                return 0
        
        models.sort(key=get_download_count, reverse=True)
        logger.info(f"📊 Sorted by download count (Most Downloaded first)")
        
    except Exception as e:
        logger.error(f"❌ Failed to query database: {e}")
        return
    
    # Display results for dry run
    if dry_run:
        logger.info("\n🔍 DRY RUN - Models that would be downloaded:")
        for i, model in enumerate(models[:10], 1):
            model_id = model[0]
            model_name = model[1]
            
            # Safely parse Python dict data (raw_data uses single quotes)
            try:
                import ast
                raw_data = ast.literal_eval(model[6]) if model[6] else {}
            except (ValueError, SyntaxError, TypeError):
                # Fallback to empty dict if parsing fails
                raw_data = {}
            
            # Extract stats
            download_count = raw_data.get('stats', {}).get('downloadCount', 0)
            
            # Extract category/base model info
            if model_type == "LORA":
                tags = raw_data.get('tags', [])
                if isinstance(tags, str):
                    tags = [tags]
                relevant_tags = [t for t in tags if t in (categories or [])]
                info = f"Tags: {', '.join(relevant_tags)}" if relevant_tags else "Tags: Unknown"
            else:
                base_model = raw_data.get('baseModel', 'Unknown')
                info = f"Base: {base_model}"
            
            logger.info(f"  {i}. [{model_id}] {model_name} - Downloads: {download_count:,} - {info}")
        
        if len(models) > 10:
            logger.info(f"  ... and {len(models) - 10} more models")
        return
    
    # Start actual downloads
    logger.info("📥 Starting downloads...")
    
    try:
        # Import download modules
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from api.client import CivitaiAPIClient
        from core.config.system_config import SystemConfig
        from core.download.manager import DownloadManager
        from utils.download_organizer import DownloadOrganizer
        
        config = SystemConfig()
        api_key = config.get('api.api_key')
        
        # Initialize download manager
        download_manager = DownloadManager()
        
        downloaded_count = 0
        failed_count = 0
        
        for i, model in enumerate(models, 1):
            model_id = model[0]
            model_name = model[1]
            
            logger.info(f"📥 [{i}/{len(models)}] Downloading: {model_name}")
            
            try:
                # Check if already downloaded
                cursor.execute("SELECT COUNT(*) FROM downloads WHERE model_id = ? AND status = 'completed'", (model_id,))
                if cursor.fetchone()[0] > 0:
                    logger.info(f"⏭️  Already downloaded, skipping: {model_name}")
                    continue
                
                async with CivitaiAPIClient(api_key=api_key) as api_client:
                    # Get model information from CivitAI API
                    model_response = await api_client.get_models({'ids': str(model_id), 'limit': 1})
                    
                    if not model_response.get('items'):
                        logger.error(f"❌ Model {model_id} not found on CivitAI")
                        failed_count += 1
                        continue
                    
                    model_data = model_response['items'][0]
                    versions = model_data.get('modelVersions', [])
                    
                    if not versions:
                        logger.error(f"❌ No versions found for model {model_id}")
                        failed_count += 1
                        continue
                    
                    # Use the latest version
                    latest_version = versions[0]
                    version_id = latest_version['id']
                    download_url = latest_version.get('downloadUrl')
                    
                    if not download_url:
                        download_url = f"https://civitai.com/api/download/models/{version_id}"
                    
                    # Get filename from primary file
                    files = latest_version.get('files', [])
                    primary_file = next((f for f in files if f.get('primary', False)), None)
                    filename = primary_file['name'] if primary_file else f"model_{model_id}.safetensors"
                    
                    logger.info(f"📦 Version: {latest_version['name']}")
                    logger.info(f"📄 Filename: {filename}")
                    
                    # Set up organized folder structure
                    organizer = DownloadOrganizer(Path(output_dir))
                    organization_info = await organizer.organize_download(model_data, latest_version)
                    
                    logger.info(f"📁 Folder: {organization_info['folder_path']}")
                    
                    # Perform actual download
                    result = await download_manager.download_file(
                        url=download_url,
                        output_dir=organization_info['folder_path'],
                        filename=filename
                    )
                    
                    if result.success:
                        logger.info(f"✅ Download completed: {result.file_path}")
                        
                        # Update metadata with download completion info
                        try:
                            organizer.update_download_metadata(
                                organization_info['metadata_path'],
                                [result.file_path],
                                organization_info['preview_paths']
                            )
                        except Exception as e:
                            logger.warning(f"⚠️  Failed to update metadata: {e}")
                        
                        # Record download in database
                        try:
                            import datetime
                            download_data = {
                                'model_id': model_id,
                                'file_id': None,
                                'file_name': result.file_path.name if hasattr(result.file_path, 'name') else filename,
                                'file_path': str(result.file_path),
                                'download_url': download_url,
                                'file_size': getattr(result, 'file_size', None),
                                'hash_sha256': getattr(result, 'hash_sha256', None),
                                'status': 'completed',
                                'downloaded_at': datetime.datetime.now().isoformat()
                            }
                            
                            # Insert into database
                            conn_db = sqlite3.connect(db_path)
                            cursor_db = conn_db.cursor()
                            
                            cursor_db.execute('''
                                INSERT OR REPLACE INTO downloads 
                                (model_id, file_id, file_name, file_path, download_url, file_size, hash_sha256, status, downloaded_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                download_data['model_id'],
                                download_data['file_id'],
                                download_data['file_name'],
                                download_data['file_path'],
                                download_data['download_url'],
                                download_data['file_size'],
                                download_data['hash_sha256'],
                                download_data['status'],
                                download_data['downloaded_at']
                            ))
                            
                            conn_db.commit()
                            conn_db.close()
                            
                            logger.info(f"📝 Recorded download in database: {model_id}")
                            
                        except Exception as e:
                            logger.warning(f"⚠️  Failed to record download in database: {e}")
                        
                        downloaded_count += 1
                    else:
                        logger.error(f"❌ Download failed: {result.error_message}")
                        failed_count += 1
                        
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error downloading {model_name}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            # Add delay between downloads
            if i < len(models):
                await asyncio.sleep(delay)
        
        logger.info(f"🎉 Download completed! ✅ {downloaded_count} successful, ❌ {failed_count} failed")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import download modules: {e}")
        logger.info("💡 Please run from project root or ensure all dependencies are installed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick selective model download")
    parser.add_argument("--output-dir", "-o", default="/Volumes/Create-Images/Civitiai-download",
                        help="Output directory for downloads")
    parser.add_argument("--type", choices=["LORA", "Checkpoint"], required=True,
                        help="Model type to download")
    parser.add_argument("--categories", nargs='+', 
                        choices=["style", "pose", "concept", "character"],
                        help="Categories for LORA models")
    parser.add_argument("--base-models", nargs='+',
                        choices=["Illustrious", "NoobAI"],
                        help="Base models for Checkpoint models")
    parser.add_argument("--max-models", "-m", type=int, default=100,
                        help="Maximum number of models to download (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading")
    parser.add_argument("--delay", "-d", type=float, default=1.0,
                        help="Delay between downloads in seconds")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.type == "LORA" and not args.categories:
        parser.error("--categories is required when type is LORA")
    if args.type == "Checkpoint" and not args.base_models:
        parser.error("--base-models is required when type is Checkpoint")
    
    # Run quick download
    asyncio.run(quick_selective_download(
        output_dir=args.output_dir,
        model_type=args.type,
        categories=args.categories,
        base_models=args.base_models,
        max_models=args.max_models,
        dry_run=args.dry_run,
        delay=args.delay
    ))