#!/usr/bin/env python3
"""
Import script for CivitAI model search results from CSV files to SQLite database.
Reads streaming CSV files and imports model data using the DatabaseManager.
"""

import json
import csv
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Set, Optional
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to Python path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.data.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelImporter:
    """Import model data from CSV files to database."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the importer with database manager."""
        self.db_manager = DatabaseManager(db_path)
        self.processed_models: Set[int] = set()
        self.stats = {
            'total_processed': 0,
            'total_imported': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'by_category': {}
        }
    
    async def initialize(self):
        """Initialize the database."""
        await self.db_manager.initialize()
    
    def parse_json_field(self, field_value: str) -> Any:
        """
        Parse JSON string from CSV field.
        
        Args:
            field_value: String that might contain JSON
            
        Returns:
            Parsed JSON or original string if not valid JSON
        """
        if not field_value or field_value.strip() == '':
            return None
            
        try:
            # Handle escaped quotes and clean up
            cleaned_value = field_value.strip()
            if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
                cleaned_value = cleaned_value[1:-1]
            
            # Replace escaped quotes
            cleaned_value = cleaned_value.replace('""', '"')
            
            return json.loads(cleaned_value)
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse JSON field: {field_value[:100]}... Error: {e}")
            return field_value
    
    def convert_csv_to_model_data(self, row: Dict[str, str], priority_category: str) -> Dict[str, Any]:
        """
        Convert CSV row to model data format expected by DatabaseManager.
        
        Args:
            row: CSV row data
            priority_category: Category based on source file (style, concept, pose, character)
            
        Returns:
            Model data dictionary
        """
        try:
            # Parse tags and modelVersions as JSON
            tags = self.parse_json_field(row.get('tags', '[]'))
            model_versions = self.parse_json_field(row.get('modelVersions', '[]'))
            
            # Handle boolean fields
            def safe_bool(value: str) -> bool:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes')
            
            # Handle integer fields
            def safe_int(value: str) -> Optional[int]:
                if not value or value.strip() == '':
                    return None
                try:
                    return int(float(value))  # Handle float strings like "123.0"
                except (ValueError, TypeError):
                    return None
            
            # Handle float fields
            def safe_float(value: str) -> Optional[float]:
                if not value or value.strip() == '':
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            
            # Build creator info
            creator_data = {}
            if row.get('creator_username'):
                creator_data['username'] = row['creator_username']
            if row.get('creator_image'):
                creator_data['image'] = row['creator_image']
            
            # Build model data structure
            model_data = {
                'id': safe_int(row.get('id')),
                'name': row.get('name', ''),
                'description': row.get('description', ''),
                'type': row.get('type', ''),
                'nsfw': safe_bool(row.get('nsfw', False)),
                'allowCommercialUse': row.get('allowCommercialUse', ''),
                'allowNoCredit': safe_bool(row.get('allowNoCredit', False)),
                'allowDerivatives': safe_bool(row.get('allowDerivatives', False)),
                'allowDifferentLicense': safe_bool(row.get('allowDifferentLicense', False)),
                'minor': safe_bool(row.get('minor', False)),
                'sfwOnly': safe_bool(row.get('sfwOnly', False)),
                'poi': safe_bool(row.get('poi', False)),
                'nsfwLevel': safe_int(row.get('nsfwLevel')),
                'availability': row.get('availability', 'Public'),
                'cosmetic': safe_bool(row.get('cosmetic', False)),
                'supportsGeneration': safe_bool(row.get('supportsGeneration', False)),
                'creator': creator_data,
                'tags': tags if isinstance(tags, list) else [],
                'modelVersions': model_versions if isinstance(model_versions, list) else [],
                'priority_category': priority_category,
                'stats': {
                    'downloadCount': safe_int(row.get('stats_downloadCount')),
                    'favoriteCount': safe_int(row.get('stats_favoriteCount')),
                    'thumbsUpCount': safe_int(row.get('stats_thumbsUpCount')),
                    'thumbsDownCount': safe_int(row.get('stats_thumbsDownCount')),
                    'commentCount': safe_int(row.get('stats_commentCount')),
                    'ratingCount': safe_int(row.get('stats_ratingCount')),
                    'rating': safe_float(row.get('stats_rating')),
                    'tippedAmountCount': safe_int(row.get('stats_tippedAmountCount'))
                }
            }
            
            return model_data
            
        except Exception as e:
            logger.error(f"Error converting CSV row to model data: {e}")
            logger.error(f"Row data: {row}")
            raise
    
    def process_csv_file(self, file_path: Path, priority_category: str) -> int:
        """
        Process a single CSV file and import models.
        
        Args:
            file_path: Path to CSV file
            priority_category: Category for this file's models
            
        Returns:
            Number of models imported from this file
        """
        logger.info(f"Processing {file_path.name} for category: {priority_category}")
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        try:
            # Use pandas to read CSV with proper handling of complex fields
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            
            logger.info(f"Found {len(df)} rows in {file_path.name}")
            
            for index, row in df.iterrows():
                try:
                    model_id = int(row['id']) if row['id'] else None
                    if not model_id:
                        logger.warning(f"Skipping row {index + 1}: No model ID")
                        continue
                    
                    # Skip duplicates
                    if model_id in self.processed_models:
                        skipped_count += 1
                        self.stats['duplicates_skipped'] += 1
                        continue
                    
                    # Convert to model data format
                    model_data = self.convert_csv_to_model_data(row.to_dict(), priority_category)
                    
                    # Store in database
                    if self.db_manager.store_model(model_data):
                        imported_count += 1
                        self.processed_models.add(model_id)
                        
                        if imported_count % 100 == 0:
                            logger.info(f"Processed {imported_count} models from {file_path.name}")
                    else:
                        error_count += 1
                        logger.warning(f"Failed to store model {model_id}")
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing row {index + 1} in {file_path.name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            return 0
        
        # Update stats
        self.stats['by_category'][priority_category] = {
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': error_count
        }
        self.stats['total_imported'] += imported_count
        self.stats['errors'] += error_count
        
        logger.info(f"Completed {file_path.name}: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
        return imported_count
    
    async def import_all_csv_files(self, reports_dir: Path):
        """
        Import all CSV files from the reports directory.
        
        Args:
            reports_dir: Path to reports directory containing CSV files
        """
        logger.info("Starting model import from CSV files...")
        
        # Define CSV files and their categories
        csv_files = [
            ('style_models_stream.csv', 'style'),
            ('concept_models_stream.csv', 'concept'),
            ('pose_models_stream.csv', 'pose'),
            ('character_models_stream.csv', 'character')
        ]
        
        start_time = datetime.now()
        
        for filename, category in csv_files:
            file_path = reports_dir / filename
            
            if not file_path.exists():
                logger.warning(f"CSV file not found: {file_path}")
                continue
            
            try:
                imported = self.process_csv_file(file_path, category)
                self.stats['total_processed'] += imported
                
            except Exception as e:
                logger.error(f"Failed to process {filename}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print final statistics
        self.print_import_summary(duration)
    
    def print_import_summary(self, duration):
        """Print summary of import process."""
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total models processed: {self.stats['total_processed']}")
        logger.info(f"Total models imported: {self.stats['total_imported']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        logger.info(f"Processing time: {duration}")
        logger.info("")
        logger.info("By Category:")
        
        for category, stats in self.stats['by_category'].items():
            logger.info(f"  {category.capitalize()}: {stats['imported']} imported, "
                       f"{stats['skipped']} skipped, {stats['errors']} errors")
        
        logger.info("=" * 60)


async def main():
    """Main function to run the import process."""
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / "reports"
    db_path = project_root / "data" / "civitai_downloader.db"
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Reports directory: {reports_dir}")
    logger.info(f"Database path: {db_path}")
    
    # Check if reports directory exists
    if not reports_dir.exists():
        logger.error(f"Reports directory not found: {reports_dir}")
        return 1
    
    # Initialize importer
    importer = ModelImporter(db_path)
    await importer.initialize()
    
    try:
        # Import all CSV files
        await importer.import_all_csv_files(reports_dir)
        logger.info("Import process completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Import process failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)