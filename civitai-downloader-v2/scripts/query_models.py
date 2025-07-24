#!/usr/bin/env python3
"""
Query script for exploring imported model data in the SQLite database.
Provides various query functions for the CivitAI model database.
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# Add parent directory to Python path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.data.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelQueryTool:
    """Tool for querying and exploring model data."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the query tool with database manager."""
        self.db_manager = DatabaseManager(db_path)
    
    async def initialize(self):
        """Initialize the database connection."""
        await self.db_manager.initialize()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total counts
            cursor.execute('SELECT COUNT(*) FROM models')
            stats['total_models'] = cursor.fetchone()[0]
            
            # By category
            cursor.execute('SELECT priority_category, COUNT(*) FROM models GROUP BY priority_category ORDER BY COUNT(*) DESC')
            stats['by_category'] = dict(cursor.fetchall())
            
            # By type
            cursor.execute('SELECT type, COUNT(*) FROM models GROUP BY type ORDER BY COUNT(*) DESC')
            stats['by_type'] = dict(cursor.fetchall())
            
            # NSFW distribution
            cursor.execute('SELECT nsfw, COUNT(*) FROM models GROUP BY nsfw')
            stats['nsfw_distribution'] = dict(cursor.fetchall())
            
            # Commercial use distribution
            cursor.execute('SELECT allowCommercialUse, COUNT(*) FROM models GROUP BY allowCommercialUse ORDER BY COUNT(*) DESC')
            stats['commercial_use'] = dict(cursor.fetchall())
            
            return stats
    
    def search_models(self, query: str, category: Optional[str] = None, model_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for models by name or description.
        
        Args:
            query: Search query string
            category: Optional category filter (style, concept, pose, character)
            model_type: Optional model type filter (LORA, Checkpoint, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching models
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = """
                SELECT id, name, type, description, creator_username, priority_category, nsfw, allowCommercialUse
                FROM models 
                WHERE (name LIKE ? OR description LIKE ?)
            """
            params = [f'%{query}%', f'%{query}%']
            
            if category:
                base_query += " AND priority_category = ?"
                params.append(category)
            
            if model_type:
                base_query += " AND type = ?"
                params.append(model_type)
            
            base_query += " ORDER BY name LIMIT ?"
            params.append(limit)
            
            cursor.execute(base_query, params)
            columns = [description[0] for description in cursor.description]
            
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_models_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get models from a specific category."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, type, description, creator_username, nsfw, allowCommercialUse
                FROM models 
                WHERE priority_category = ?
                ORDER BY name
                LIMIT ?
            """, (category, limit))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_popular_models(self, category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get popular models based on raw_data stats.
        Note: This requires parsing JSON from raw_data.
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = "SELECT id, name, type, priority_category, creator_username, raw_data FROM models"
            params = []
            
            if category:
                base_query += " WHERE priority_category = ?"
                params.append(category)
            
            cursor.execute(base_query, params)
            
            models_with_stats = []
            for row in cursor.fetchall():
                try:
                    raw_data = json.loads(row[5]) if row[5] else {}
                    stats = raw_data.get('stats', {})
                    download_count = stats.get('downloadCount', 0) or 0
                    
                    models_with_stats.append({
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'priority_category': row[3],
                        'creator_username': row[4],
                        'download_count': download_count,
                        'favorite_count': stats.get('favoriteCount', 0) or 0,
                        'thumbs_up_count': stats.get('thumbsUpCount', 0) or 0,
                        'rating': stats.get('rating', 0) or 0
                    })
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Sort by download count
            models_with_stats.sort(key=lambda x: x['download_count'], reverse=True)
            return models_with_stats[:limit]
    
    def get_creators_stats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get statistics about model creators."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT creator_username, COUNT(*) as model_count,
                       GROUP_CONCAT(DISTINCT priority_category) as categories,
                       GROUP_CONCAT(DISTINCT type) as types
                FROM models 
                WHERE creator_username IS NOT NULL AND creator_username != ''
                GROUP BY creator_username
                ORDER BY model_count DESC
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


async def main():
    """Main function for interactive model querying."""
    # Set up paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "civitai_downloader.db"
    
    # Initialize query tool
    query_tool = ModelQueryTool(db_path)
    await query_tool.initialize()
    
    print("CivitAI Model Database Query Tool")
    print("=" * 50)
    
    # Show statistics
    stats = query_tool.get_statistics()
    print(f"Total models: {stats['total_models']}")
    print(f"\nBy category: {stats['by_category']}")
    print(f"\nBy type: {dict(list(stats['by_type'].items())[:5])}")  # Top 5 types
    
    print("\nPopular models (by downloads):")
    popular = query_tool.get_popular_models(limit=10)
    for i, model in enumerate(popular, 1):
        print(f"  {i}. {model['name'][:50]}... ({model['type']}, {model['download_count']} downloads)")
    
    print("\nTop creators:")
    creators = query_tool.get_creators_stats(limit=10)
    for i, creator in enumerate(creators, 1):
        print(f"  {i}. {creator['creator_username']}: {creator['model_count']} models")
    
    # Interactive search
    print("\n" + "=" * 50)
    print("Interactive Search (type 'quit' to exit)")
    
    while True:
        try:
            query = input("\nEnter search query: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            # Ask for category filter
            category = input("Filter by category (style/concept/pose/character, or press Enter for all): ").strip()
            if category and category not in ['style', 'concept', 'pose', 'character']:
                category = None
            
            results = query_tool.search_models(query, category=category, limit=10)
            
            if results:
                print(f"\nFound {len(results)} results:")
                for i, result in enumerate(results, 1):
                    nsfw_marker = " [NSFW]" if result['nsfw'] else ""
                    print(f"  {i}. {result['name'][:60]}... ({result['type']}, {result['priority_category']}){nsfw_marker}")
                    if result['creator_username']:
                        print(f"     Creator: {result['creator_username']}")
            else:
                print("No results found.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())