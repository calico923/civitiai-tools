#!/usr/bin/env python3
"""
Restore missing metadata JSON files by fetching from CivitAI API
using information from existing .civitai.info files
"""

import asyncio
import json
import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api.client import CivitaiAPIClient
from core.config.system_config import SystemConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def restore_metadata_files(base_dir: str = "/Volumes/Create-Images/Civitiai-download"):
    """
    Restore missing metadata JSON files from CivitAI API
    """
    base_path = Path(base_dir)
    
    # Find all .civitai.info files
    civitai_info_files = list(base_path.rglob("*.civitai.info"))
    logger.info(f"Found {len(civitai_info_files)} .civitai.info files")
    
    # Get API key
    config = SystemConfig()
    api_key = config.get('api.api_key')
    
    restored_count = 0
    skipped_count = 0
    failed_count = 0
    
    async with CivitaiAPIClient(api_key=api_key) as api_client:
        for info_file in civitai_info_files:
            try:
                # Check if corresponding JSON file exists
                # Remove .civitai.info and add .json
                base_name = str(info_file.name).replace('.civitai.info', '')
                json_file = info_file.parent / f"{base_name}.json"
                
                if json_file.exists():
                    logger.debug(f"⏭️  JSON already exists for {info_file.name}")
                    skipped_count += 1
                    continue
                
                # Read civitai.info file
                with open(info_file, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                
                model_id = info_data.get('modelId')
                if not model_id:
                    logger.warning(f"⚠️  No modelId in {info_file.name}")
                    failed_count += 1
                    continue
                
                logger.info(f"🔄 Restoring metadata for model {model_id}: {base_name}")
                
                # Fetch full model data from API
                model_response = await api_client.get_models({'ids': str(model_id), 'limit': 1})
                
                if not model_response.get('items'):
                    logger.error(f"❌ Model {model_id} not found on CivitAI")
                    failed_count += 1
                    continue
                
                model_data = model_response['items'][0]
                
                # Save as JSON metadata file
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(model_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Restored: {json_file.name}")
                restored_count += 1
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing {info_file.name}: {e}")
                failed_count += 1
    
    logger.info(f"\n🎉 Restoration completed!")
    logger.info(f"✅ Restored: {restored_count}")
    logger.info(f"⏭️  Skipped (already exists): {skipped_count}")
    logger.info(f"❌ Failed: {failed_count}")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Restore missing metadata JSON files')
    parser.add_argument(
        '--base-dir',
        type=str,
        default="/Volumes/Create-Images/Civitiai-download",
        help='Base directory to scan for missing metadata'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only show what would be restored without actually doing it'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be created")
        # TODO: Implement dry run logic
    else:
        await restore_metadata_files(args.base_dir)


if __name__ == "__main__":
    asyncio.run(main())