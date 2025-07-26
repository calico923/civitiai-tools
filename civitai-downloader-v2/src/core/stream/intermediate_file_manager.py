#!/usr/bin/env python3
"""
Intermediate File Manager - 中間ファイル管理とストリーム処理
API結果の中間保存とエラーリカバリ機能を提供
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, Tuple
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class IntermediateFileManager:
    """
    中間ファイル管理とストリーム処理を担当
    """
    
    def __init__(self, cache_dir: str = "data/intermediate"):
        """
        初期化
        
        Args:
            cache_dir: 中間ファイル保存ディレクトリ
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def generate_session_id(self, search_params: Dict[str, Any]) -> str:
        """
        検索パラメータから一意のセッションIDを生成
        
        Args:
            search_params: 検索パラメータ
            
        Returns:
            セッションID
        """
        # パラメータをJSON化してハッシュ生成
        params_str = json.dumps(search_params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        # タイムスタンプと組み合わせ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"search_{timestamp}_{params_hash}"
    
    def get_intermediate_file_path(self, session_id: str, suffix: str = "raw") -> Path:
        """
        中間ファイルのパスを取得
        
        Args:
            session_id: セッションID
            suffix: ファイル接尾辞（raw/filtered/processed）
            
        Returns:
            ファイルパス
        """
        return self.cache_dir / f"{session_id}_{suffix}.jsonl"
    
    def get_progress_file_path(self, session_id: str) -> Path:
        """
        プログレスファイルのパスを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            プログレスファイルパス
        """
        return self.cache_dir / f"{session_id}_progress.json"
    
    def save_progress(self, session_id: str, progress_data: Dict[str, Any]) -> None:
        """
        プログレス情報を保存
        
        Args:
            session_id: セッションID
            progress_data: プログレスデータ
        """
        progress_file = self.get_progress_file_path(session_id)
        progress_data['last_updated'] = time.time()
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, default=str)
            
            self.logger.debug(f"Progress saved: {progress_data}")
            
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
    
    def load_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        プログレス情報を読み込み
        
        Args:
            session_id: セッションID
            
        Returns:
            プログレスデータ（存在しない場合はNone）
        """
        progress_file = self.get_progress_file_path(session_id)
        
        if not progress_file.exists():
            return None
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load progress: {e}")
            return None
    
    def stream_write_models(self, session_id: str, models: List[Dict[str, Any]], 
                           suffix: str = "raw") -> bool:
        """
        モデルデータをストリーム書き込み（追記モード）
        
        Args:
            session_id: セッションID
            models: モデルデータのリスト
            suffix: ファイル接尾辞
            
        Returns:
            成功時True
        """
        file_path = self.get_intermediate_file_path(session_id, suffix)
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                for model in models:
                    # JSONL形式で保存（1行1JSON）
                    f.write(json.dumps(model, ensure_ascii=False, default=str) + '\n')
            
            self.logger.debug(f"Streamed {len(models)} models to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stream write models: {e}")
            return False
    
    def stream_read_models(self, session_id: str, suffix: str = "raw", 
                          batch_size: int = 100) -> Generator[List[Dict[str, Any]], None, None]:
        """
        モデルデータをストリーム読み込み
        
        Args:
            session_id: セッションID
            suffix: ファイル接尾辞
            batch_size: バッチサイズ
            
        Yields:
            モデルデータのバッチ
        """
        file_path = self.get_intermediate_file_path(session_id, suffix)
        
        if not file_path.exists():
            self.logger.warning(f"Intermediate file not found: {file_path}")
            return
        
        try:
            batch = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        model_data = json.loads(line)
                        batch.append(model_data)
                        
                        # バッチサイズに達したら yield
                        if len(batch) >= batch_size:
                            yield batch
                            batch = []
                            
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON at line {line_num}: {e}")
                        continue
            
            # 残りのデータを yield
            if batch:
                yield batch
                
        except Exception as e:
            self.logger.error(f"Failed to stream read models: {e}")
    
    def count_models_in_file(self, session_id: str, suffix: str = "raw") -> int:
        """
        ファイル内のモデル数をカウント
        
        Args:
            session_id: セッションID
            suffix: ファイル接尾辞
            
        Returns:
            モデル数
        """
        file_path = self.get_intermediate_file_path(session_id, suffix)
        
        if not file_path.exists():
            return 0
        
        try:
            count = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to count models: {e}")
            return 0
    
    def cleanup_session(self, session_id: str, keep_processed: bool = True) -> None:
        """
        セッションファイルのクリーンアップ
        
        Args:
            session_id: セッションID
            keep_processed: 処理済みファイルを保持するかどうか
        """
        files_to_remove = []
        
        # プログレスファイルは常に削除
        progress_file = self.get_progress_file_path(session_id)
        if progress_file.exists():
            files_to_remove.append(progress_file)
        
        # 中間ファイルの処理
        for suffix in ["raw", "filtered"]:
            file_path = self.get_intermediate_file_path(session_id, suffix)
            if file_path.exists():
                if not keep_processed or suffix != "processed":
                    files_to_remove.append(file_path)
        
        # ファイル削除実行
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                self.logger.debug(f"Cleaned up: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        セッションの概要情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション概要
        """
        summary = {
            'session_id': session_id,
            'raw_models': self.count_models_in_file(session_id, 'raw'),
            'filtered_models': self.count_models_in_file(session_id, 'filtered'),
            'processed_models': self.count_models_in_file(session_id, 'processed'),
            'progress': self.load_progress(session_id),
            'files': {}
        }
        
        # ファイルサイズ情報
        for suffix in ['raw', 'filtered', 'processed']:
            file_path = self.get_intermediate_file_path(session_id, suffix)
            if file_path.exists():
                summary['files'][suffix] = {
                    'path': str(file_path),
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
        
        return summary