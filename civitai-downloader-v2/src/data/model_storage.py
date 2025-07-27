#!/usr/bin/env python3
"""
Model Storage - Handle saving and retrieving model data from database.
"""

import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .schema_manager import initialize_database
from ..core.category.category_classifier import CategoryClassifier

logger = logging.getLogger(__name__)


class ModelStorage:
    """Handles model data storage and retrieval from database."""
    
    def __init__(self, db_path: Path):
        """Initialize model storage with database path."""
        self.db_path = db_path
        self.category_classifier = CategoryClassifier()
        
        # Initialize database with extended schema
        initialize_database(db_path, "main")
        
    def save_models_from_jsonl(self, jsonl_path: Path) -> Tuple[int, int]:
        """
        Save models from JSONL file to database.
        
        Args:
            jsonl_path: Path to processed JSONL file
            
        Returns:
            Tuple of (saved_count, skipped_count)
        """
        logger.info(f"Saving models from {jsonl_path} to database")
        
        models = self._load_models_from_jsonl(jsonl_path)
        if not models:
            logger.warning("No models found in JSONL file")
            return 0, 0
            
        saved_count = 0
        skipped_count = 0
        
        with self._get_connection() as conn:
            for model in models:
                try:
                    if self._save_model(conn, model):
                        saved_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.error(f"Error saving model {model.get('id', 'unknown')}: {e}")
                    skipped_count += 1
                    
            conn.commit()
            
        logger.info(f"Saved {saved_count} models, skipped {skipped_count}")
        return saved_count, skipped_count
    
    def _load_models_from_jsonl(self, jsonl_path: Path) -> List[Dict[str, Any]]:
        """Load models from JSONL file."""
        models = []
        
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        model = json.loads(line)
                        models.append(model)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error at line {line_num}: {e}")
                        
        except FileNotFoundError:
            logger.error(f"JSONL file not found: {jsonl_path}")
        except Exception as e:
            logger.error(f"Error reading JSONL file: {e}")
            
        return models
    
    def _save_model(self, conn: sqlite3.Connection, model: Dict[str, Any]) -> bool:
        """
        Save a single model to database.
        
        Returns:
            True if saved, False if skipped (already exists)
        """
        cursor = conn.cursor()
        model_id = model.get('id')
        
        if not model_id:
            logger.warning("Model missing ID, skipping")
            return False
            
        # Check if model already exists
        cursor.execute("SELECT id FROM models WHERE id = ?", (model_id,))
        if cursor.fetchone():
            logger.debug(f"Model {model_id} already exists, skipping")
            return False
            
        # Extract and classify categories
        processing = model.get('_processing', {})
        primary_category = processing.get('primary_category', 'other')
        all_categories = processing.get('all_categories', [primary_category])
        
        # Extract cleaned description
        description = model.get('description', '')
        cleaned_description = self._extract_cleaned_description(description)
        
        # Save main model record
        cursor.execute("""
            INSERT INTO models (
                id, name, type, description, cleaned_description,
                creator_id, creator_username, nsfw, allowCommercialUse,
                created_at, updated_at, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id,
            model.get('name', ''),
            model.get('type', ''),
            description,
            cleaned_description,
            model.get('creator', {}).get('id'),
            model.get('creator', {}).get('username', ''),
            model.get('nsfw', False),
            json.dumps(model.get('allowCommercialUse', [])),
            model.get('createdAt', ''),
            model.get('updatedAt', ''),
            json.dumps(model)
        ))
        
        # Save categories
        self._save_model_categories(cursor, model_id, primary_category, all_categories)
        
        # Save tags
        self._save_model_tags(cursor, model_id, model.get('tags', []))
        
        # Save versions
        self._save_model_versions(cursor, model_id, model.get('modelVersions', []))
        
        # Save stats
        self._save_model_stats(cursor, model_id, model.get('stats', {}))
        
        return True
    
    def _save_model_categories(self, cursor: sqlite3.Connection, model_id: int, 
                             primary_category: str, all_categories: List[str]):
        """Save model categories to database."""
        for category_name in all_categories:
            # Get or create category
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            result = cursor.fetchone()
            
            if result:
                category_id = result[0]
            else:
                # Category should exist from schema initialization, but create if missing
                cursor.execute("""
                    INSERT INTO categories (name, display_name, priority)
                    VALUES (?, ?, ?)
                """, (category_name, category_name.title(), 999))
                category_id = cursor.lastrowid
            
            # Link model to category
            is_primary = category_name == primary_category
            cursor.execute("""
                INSERT OR IGNORE INTO model_categories (model_id, category_id, is_primary)
                VALUES (?, ?, ?)
            """, (model_id, category_id, is_primary))
    
    def _save_model_tags(self, cursor: sqlite3.Connection, model_id: int, tags: List[Any]):
        """Save model tags to database."""
        for tag in tags:
            if isinstance(tag, dict):
                tag_name = tag.get('name', '')
            else:
                tag_name = str(tag)
                
            if not tag_name:
                continue
                
            # Get or create tag
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            result = cursor.fetchone()
            
            if result:
                tag_id = result[0]
            else:
                cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                tag_id = cursor.lastrowid
            
            # Link model to tag
            cursor.execute("""
                INSERT OR IGNORE INTO model_tags (model_id, tag_id)
                VALUES (?, ?)
            """, (model_id, tag_id))
    
    def _save_model_versions(self, cursor: sqlite3.Connection, model_id: int, 
                           versions: List[Dict[str, Any]]):
        """Save model versions to database."""
        for version in versions:
            version_id = version.get('id')
            if not version_id:
                continue
                
            cursor.execute("""
                INSERT OR REPLACE INTO model_versions (
                    id, model_id, name, base_model, download_url,
                    file_size, created_at, updated_at, stats, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id,
                model_id,
                version.get('name', ''),
                version.get('baseModel', ''),
                version.get('downloadUrl', ''),
                version.get('files', [{}])[0].get('sizeKB') if version.get('files') else None,
                version.get('createdAt', ''),
                version.get('updatedAt', ''),
                json.dumps(version.get('stats', {})),
                json.dumps(version)
            ))
    
    def _save_model_stats(self, cursor: sqlite3.Connection, model_id: int, 
                         stats: Dict[str, Any]):
        """Save model statistics to database."""
        cursor.execute("""
            INSERT OR REPLACE INTO model_stats (
                model_id, download_count, likes_count, rating,
                view_count, comment_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id,
            stats.get('downloadCount', 0),
            stats.get('thumbsUpCount', 0),
            stats.get('rating', 0.0),
            stats.get('viewCount', 0),
            stats.get('commentCount', 0),
            datetime.now().isoformat()
        ))
    
    def _extract_cleaned_description(self, description: str) -> str:
        """Extract cleaned description from HTML content."""
        # Import here to avoid circular imports
        try:
            # Try to import from project root
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            from extract_description_logic import extract_useful_description
            return extract_useful_description(description)
        except ImportError:
            # Fallback: simple HTML tag removal
            import re
            cleaned = re.sub(r'<[^>]+>', '', description) if description else ''
            return cleaned[:400] + ('...' if len(cleaned) > 400 else '')
    
    def _get_connection(self):
        """Get database connection with proper configuration."""
        from contextlib import contextmanager
        
        @contextmanager
        def connection():
            conn = None
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.execute("PRAGMA foreign_keys = ON")
                conn.row_factory = sqlite3.Row
                yield conn
            except Exception as e:
                if conn:
                    conn.rollback()
                raise
            finally:
                if conn:
                    conn.close()
                    
        return connection()
    
    def get_model_count(self) -> int:
        """Get total number of models in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM models")
            return cursor.fetchone()[0]
    
    def model_exists(self, model_id: int) -> bool:
        """Check if model exists in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM models WHERE id = ?", (model_id,))
            return cursor.fetchone() is not None
    
    def get_models(self, category: Optional[str] = None, base_model: Optional[str] = None, 
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve models from database with optional filters.
        
        Args:
            category: Filter by primary category
            base_model: Filter by base model
            limit: Maximum number of models to return
            
        Returns:
            List of model dictionaries with all data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT DISTINCT
                    m.id, m.name, m.type, m.description, m.cleaned_description,
                    m.creator_id, m.creator_username, m.nsfw, m.allowCommercialUse,
                    m.created_at, m.updated_at, m.raw_data,
                    c.name as primary_category,
                    GROUP_CONCAT(DISTINCT ct.name) as all_categories,
                    GROUP_CONCAT(DISTINCT t.name) as tags,
                    ms.download_count, ms.likes_count, ms.rating,
                    ms.view_count, ms.comment_count
                FROM models m
                LEFT JOIN model_categories mc ON m.id = mc.model_id AND mc.is_primary = TRUE
                LEFT JOIN categories c ON mc.category_id = c.id
                LEFT JOIN model_categories mc2 ON m.id = mc2.model_id
                LEFT JOIN categories ct ON mc2.category_id = ct.id
                LEFT JOIN model_tags mt ON m.id = mt.model_id
                LEFT JOIN tags t ON mt.tag_id = t.id
                LEFT JOIN model_stats ms ON m.id = ms.model_id
            """
            
            params = []
            where_conditions = []
            
            if category:
                where_conditions.append("c.name = ?")
                params.append(category)
                
            if base_model:
                where_conditions.append("""
                    m.id IN (
                        SELECT DISTINCT mv.model_id 
                        FROM model_versions mv 
                        WHERE mv.base_model = ?
                    )
                """)
                params.append(base_model)
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
                
            query += " GROUP BY m.id ORDER BY m.id"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            models = []
            for row in rows:
                # Convert row to dict and reconstruct model data
                model_data = {
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'description': row['description'],
                    'cleaned_description': row['cleaned_description'],
                    'creator': {
                        'id': row['creator_id'],
                        'username': row['creator_username']
                    },
                    'nsfw': bool(row['nsfw']),
                    'allowCommercialUse': json.loads(row['allowCommercialUse']) if row['allowCommercialUse'] else [],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at'],
                    'stats': {
                        'downloadCount': row['download_count'] or 0,
                        'thumbsUpCount': row['likes_count'] or 0,
                        'rating': row['rating'] or 0.0,
                        'viewCount': row['view_count'] or 0,
                        'commentCount': row['comment_count'] or 0
                    },
                    '_processing': {
                        'primary_category': row['primary_category'] or 'other',
                        'all_categories': row['all_categories'].split(',') if row['all_categories'] else []
                    }
                }
                
                # Add tags
                if row['tags']:
                    tag_names = row['tags'].split(',')
                    model_data['tags'] = [{'name': tag.strip()} for tag in tag_names if tag.strip()]
                else:
                    model_data['tags'] = []
                
                # Get model versions for this model
                model_data['modelVersions'] = self._get_model_versions(cursor, row['id'])
                
                models.append(model_data)
            
            return models
    
    def _get_model_versions(self, cursor: sqlite3.Connection, model_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a model."""
        cursor.execute("""
            SELECT id, name, base_model, download_url, file_size, 
                   created_at, updated_at, stats, raw_data
            FROM model_versions 
            WHERE model_id = ?
            ORDER BY created_at DESC
        """, (model_id,))
        
        versions = []
        for row in cursor.fetchall():
            version_data = {
                'id': row['id'],
                'name': row['name'],
                'baseModel': row['base_model'],
                'downloadUrl': row['download_url'],
                'createdAt': row['created_at'],
                'updatedAt': row['updated_at']
            }
            
            # Add file info if available
            if row['file_size']:
                version_data['files'] = [{'sizeKB': row['file_size']}]
            
            # Add stats if available
            if row['stats']:
                try:
                    version_data['stats'] = json.loads(row['stats'])
                except json.JSONDecodeError:
                    version_data['stats'] = {}
            
            versions.append(version_data)
            
        return versions
    
    def export_to_jsonl(self, output_path: Path, category: Optional[str] = None, 
                       base_model: Optional[str] = None, limit: Optional[int] = None) -> int:
        """
        Export models from database to JSONL format.
        
        Args:
            output_path: Path to output JSONL file
            category: Filter by primary category
            base_model: Filter by base model
            limit: Maximum number of models to export
            
        Returns:
            Number of models exported
        """
        models = self.get_models(category=category, base_model=base_model, limit=limit)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for model in models:
                f.write(json.dumps(model, ensure_ascii=False, default=str) + '\n')
        
        logger.info(f"Exported {len(models)} models to {output_path}")
        return len(models)