#!/usr/bin/env python3
"""
Category Repository - カテゴリデータのDB操作を管理
第三正規形に従ったカテゴリ管理
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CategoryRepository:
    """
    カテゴリ関連のデータベース操作を管理
    """
    
    def __init__(self, db_path: Path):
        """
        カテゴリリポジトリの初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    @contextmanager
    def get_connection(self):
        """データベース接続を取得"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()
    
    def save_model_categories(self, model_id: int, categories: List[str], 
                            primary_category: Optional[str] = None) -> bool:
        """
        モデルのカテゴリ情報を保存
        
        Args:
            model_id: モデルID
            categories: カテゴリ名のリスト
            primary_category: 主カテゴリ名
            
        Returns:
            成功時True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 既存のカテゴリ関連を削除
                cursor.execute("DELETE FROM model_categories WHERE model_id = ?", (model_id,))
                
                for category_name in categories:
                    # カテゴリIDを取得
                    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
                    row = cursor.fetchone()
                    
                    if row:
                        category_id = row['id']
                        is_primary = (category_name == primary_category)
                        
                        # model_categories に挿入
                        cursor.execute("""
                            INSERT INTO model_categories (model_id, category_id, is_primary)
                            VALUES (?, ?, ?)
                        """, (model_id, category_id, is_primary))
                    else:
                        self.logger.warning(f"Unknown category: {category_name}")
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save categories for model {model_id}: {e}")
            return False
    
    def get_model_categories(self, model_id: int) -> Tuple[Optional[str], List[str]]:
        """
        モデルのカテゴリ情報を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            (primary_category, all_categories) のタプル
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 全カテゴリを取得
                cursor.execute("""
                    SELECT c.name, mc.is_primary
                    FROM model_categories mc
                    JOIN categories c ON mc.category_id = c.id
                    WHERE mc.model_id = ?
                    ORDER BY c.priority
                """, (model_id,))
                
                all_categories = []
                primary_category = None
                
                for row in cursor.fetchall():
                    category_name = row['name']
                    all_categories.append(category_name)
                    
                    if row['is_primary']:
                        primary_category = category_name
                
                return primary_category, all_categories
                
        except Exception as e:
            self.logger.error(f"Failed to get categories for model {model_id}: {e}")
            return None, []
    
    def get_models_by_category(self, category_name: str, primary_only: bool = False) -> List[int]:
        """
        特定カテゴリに属するモデルIDを取得
        
        Args:
            category_name: カテゴリ名
            primary_only: 主カテゴリのみ検索する場合True
            
        Returns:
            モデルIDのリスト
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT DISTINCT mc.model_id
                    FROM model_categories mc
                    JOIN categories c ON mc.category_id = c.id
                    WHERE c.name = ?
                """
                
                if primary_only:
                    query += " AND mc.is_primary = TRUE"
                
                cursor.execute(query, (category_name,))
                
                return [row['model_id'] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get models for category {category_name}: {e}")
            return []
    
    def get_category_statistics(self, primary_only: bool = True) -> Dict[str, int]:
        """
        カテゴリごとのモデル数統計を取得
        
        Args:
            primary_only: 主カテゴリのみ集計する場合True
            
        Returns:
            {category_name: count} の辞書
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if primary_only:
                    query = """
                        SELECT c.name, COUNT(mc.model_id) as count
                        FROM categories c
                        LEFT JOIN model_categories mc ON c.id = mc.category_id AND mc.is_primary = TRUE
                        GROUP BY c.id, c.name
                        ORDER BY c.priority
                    """
                else:
                    query = """
                        SELECT c.name, COUNT(mc.model_id) as count
                        FROM categories c
                        LEFT JOIN model_categories mc ON c.id = mc.category_id
                        GROUP BY c.id, c.name
                        ORDER BY c.priority
                    """
                
                cursor.execute(query)
                
                return {row['name']: row['count'] for row in cursor.fetchall()}
                
        except Exception as e:
            self.logger.error(f"Failed to get category statistics: {e}")
            return {}
    
    def migrate_existing_models(self, classifier) -> int:
        """
        既存モデルのカテゴリ情報を移行
        
        Args:
            classifier: CategoryClassifierインスタンス
            
        Returns:
            処理したモデル数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # raw_dataからタグ情報を持つモデルを取得
                cursor.execute("""
                    SELECT id, raw_data
                    FROM models
                    WHERE raw_data IS NOT NULL
                """)
                
                count = 0
                for row in cursor.fetchall():
                    try:
                        import json
                        model_data = json.loads(row['raw_data'])
                        model_id = row['id']
                        
                        # カテゴリを分類
                        primary, all_cats = classifier.classify_model(model_data)
                        
                        if all_cats:
                            self.save_model_categories(model_id, all_cats, primary)
                            count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to migrate model {row['id']}: {e}")
                
                return count
                
        except Exception as e:
            self.logger.error(f"Failed to migrate models: {e}")
            return 0