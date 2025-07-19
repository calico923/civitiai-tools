"""Context management utilities for large data processing"""

import json
from typing import List, Dict, Any
from pathlib import Path


class ContextManager:
    """大量データのコンテキスト管理"""
    
    def __init__(self, max_items_per_chunk: int = 50):
        """
        Args:
            max_items_per_chunk: 1つのチャンクあたりの最大アイテム数
        """
        self.max_items_per_chunk = max_items_per_chunk
    
    def chunk_models(self, models: List[Dict]) -> List[List[Dict]]:
        """モデルリストをチャンクに分割"""
        chunks = []
        for i in range(0, len(models), self.max_items_per_chunk):
            chunk = models[i:i + self.max_items_per_chunk]
            chunks.append(chunk)
        return chunks
    
    def save_chunks(self, chunks: List[List[Dict]], output_dir: Path, base_filename: str):
        """チャンクを個別ファイルに保存"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            chunk_filename = f"{base_filename}_chunk_{i+1}.json"
            chunk_path = output_dir / chunk_filename
            
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            
            chunk_paths.append(chunk_path)
            print(f"チャンク {i+1}/{len(chunks)} 保存: {chunk_path} ({len(chunk)} items)")
        
        return chunk_paths
    
    def load_chunks(self, chunk_paths: List[Path]) -> List[Dict]:
        """チャンクファイルからデータを読み込み"""
        all_models = []
        for chunk_path in chunk_paths:
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
                all_models.extend(chunk)
        return all_models
    
    def create_summary(self, models: List[Dict], base_models: List[str] = None) -> Dict[str, Any]:
        """モデルリストのサマリーを作成"""
        if base_models is None:
            base_models = ['illustrious', 'pony', 'noobai']
        
        summary = {
            'total_count': len(models),
            'by_base_model': {},
            'by_type': {},
            'top_creators': {},
            'sample_models': models[:5] if models else []
        }
        
        # ベースモデル別カウント
        for base_model in base_models:
            count = sum(1 for model in models 
                       if any(base_model.lower() in tag.lower() 
                             for tag in model.get('tags', [])) or
                          base_model.lower() in model.get('model_name', model.get('name', '')).lower())
            summary['by_base_model'][base_model] = count
        
        # タイプ別カウント
        for model in models:
            model_type = model.get('model_type', model.get('type', 'Unknown'))
            summary['by_type'][model_type] = summary['by_type'].get(model_type, 0) + 1
        
        # 作成者別カウント（トップ10）
        creator_counts = {}
        for model in models:
            creator = model.get('creator', 'Unknown')
            if isinstance(creator, dict):
                creator = creator.get('username', 'Unknown')
            creator_counts[creator] = creator_counts.get(creator, 0) + 1
        
        summary['top_creators'] = dict(sorted(creator_counts.items(), 
                                            key=lambda x: x[1], reverse=True)[:10])
        
        return summary