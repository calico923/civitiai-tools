#!/usr/bin/env python3
"""
Category Classifier - 複数カテゴリを持つモデルの分類機能
優先順位に基づいて主カテゴリを決定する
"""

from typing import List, Dict, Optional, Tuple, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategoryInfo:
    """カテゴリ情報"""
    name: str
    display_name: str
    priority: int


class CategoryClassifier:
    """
    複数カテゴリを持つモデルをタグの出現順序に基づいて分類
    """
    
    # 既知のカテゴリ一覧（CivitAIの15カテゴリ + 追加カテゴリ）
    KNOWN_CATEGORIES = {
        'character', 'style', 'concept', 'background', 'poses',
        'vehicle', 'clothing', 'action', 'animal', 'assets',
        'base model', 'buildings', 'celebrity', 'objects', 'tool',
        'body', 'outfit', 'base', 'workflow', 'wildcards'
    }
    
    def __init__(self):
        """カテゴリ分類器の初期化"""
        self.logger = logging.getLogger(__name__)
        
    def classify_model(self, model_data: Dict) -> Tuple[str, List[str]]:
        """
        モデルのカテゴリを分類し、主カテゴリを決定
        タグの出現順序で最初のカテゴリを主カテゴリとする
        
        Args:
            model_data: モデルデータ（tagsフィールドを含む）
            
        Returns:
            (primary_category, all_categories) のタプル
        """
        # タグから全カテゴリを抽出（順序を保持）
        all_categories = self._extract_categories_from_tags(model_data.get('tags', []))
        
        # 主カテゴリを決定（最初に出現したカテゴリ）
        primary_category = all_categories[0] if all_categories else 'other'
        
        self.logger.debug(f"Model {model_data.get('id')}: categories={all_categories}, primary={primary_category}")
        
        return primary_category, all_categories
    
    def _extract_categories_from_tags(self, tags: List[Any]) -> List[str]:
        """
        タグリストからカテゴリを抽出（出現順序を保持）
        
        Args:
            tags: タグのリスト（文字列またはdictのリスト）
            
        Returns:
            カテゴリ名のリスト（出現順）
        """
        categories = []
        seen = set()  # 重複を防ぐ
        
        for tag in tags:
            # タグが辞書形式の場合
            if isinstance(tag, dict):
                tag_name = tag.get('name', '').lower()
            else:
                tag_name = str(tag).lower()
            
            # 既知のカテゴリかチェック（重複を除く）
            if tag_name in self.KNOWN_CATEGORIES and tag_name not in seen:
                categories.append(tag_name)
                seen.add(tag_name)
        
        return categories
    
    
    def is_known_category(self, category: str) -> bool:
        """
        既知のカテゴリかどうかをチェック
        
        Args:
            category: カテゴリ名
            
        Returns:
            既知のカテゴリの場合True
        """
        return category.lower() in self.KNOWN_CATEGORIES
    
    def batch_classify(self, models: List[Dict]) -> Dict[int, Tuple[str, List[str]]]:
        """
        複数モデルを一括分類
        
        Args:
            models: モデルデータのリスト
            
        Returns:
            {model_id: (primary_category, all_categories)} の辞書
        """
        results = {}
        
        for model in models:
            model_id = model.get('id')
            if model_id:
                primary, all_cats = self.classify_model(model)
                results[model_id] = (primary, all_cats)
        
        return results
    
    def get_category_statistics(self, models: List[Dict]) -> Dict[str, int]:
        """
        モデルのカテゴリ分布統計を取得
        
        Args:
            models: モデルデータのリスト
            
        Returns:
            {category_name: count} の辞書
        """
        stats = {}
        
        for model in models:
            primary, _ = self.classify_model(model)
            if primary:
                stats[primary] = stats.get(primary, 0) + 1
        
        return stats