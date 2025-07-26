#!/usr/bin/env python3
"""
Streaming Search Engine - ストリーム処理対応検索エンジン
中間ファイルを使用したエラーリカバリ機能付き検索処理
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
import logging
from pathlib import Path

from .intermediate_file_manager import IntermediateFileManager
from ..search.search_engine import AdvancedSearchEngine
from ..search.advanced_search import AdvancedSearchParams
from ..category import CategoryClassifier

logger = logging.getLogger(__name__)


class StreamingSearchEngine:
    """
    ストリーム処理対応検索エンジン
    API → 中間ファイル → フィルタリング → DB の3段階処理
    """
    
    def __init__(self, search_engine: AdvancedSearchEngine, 
                 intermediate_manager: Optional[IntermediateFileManager] = None):
        """
        初期化
        
        Args:
            search_engine: 基本検索エンジン
            intermediate_manager: 中間ファイルマネージャー
        """
        self.search_engine = search_engine
        self.intermediate_manager = intermediate_manager or IntermediateFileManager()
        self.category_classifier = CategoryClassifier()
        self.logger = logging.getLogger(__name__)
    
    async def streaming_search_with_recovery(self, search_params: AdvancedSearchParams,
                                           resume_session: Optional[str] = None,
                                           batch_size: int = 50) -> Tuple[str, Dict[str, Any]]:
        """
        リカバリ機能付きストリーミング検索
        
        Args:
            search_params: 検索パラメータ
            resume_session: 再開するセッションID
            batch_size: バッチサイズ
            
        Returns:
            (session_id, summary) のタプル
        """
        # セッションIDの決定
        if resume_session:
            session_id = resume_session
            self.logger.info(f"Resuming session: {session_id}")
        else:
            session_id = self.intermediate_manager.generate_session_id(search_params.__dict__)
            self.logger.info(f"Starting new session: {session_id}")
        
        try:
            # Step 1: API検索 → 中間ファイル保存
            await self._stream_api_to_intermediate(session_id, search_params, batch_size)
            
            # Step 2: 中間ファイル → フィルタリング → 中間ファイル
            await self._stream_filter_intermediate(session_id, search_params, batch_size)
            
            # Step 3: 最終処理（カテゴリ分類など）
            await self._stream_final_processing(session_id, batch_size)
            
            # 完了情報を保存
            self.intermediate_manager.save_progress(session_id, {
                'status': 'completed',
                'completed_at': time.time(),
                'search_params': search_params.__dict__
            })
            
            # セッション概要を返す
            summary = self.intermediate_manager.get_session_summary(session_id)
            self.logger.info(f"Search completed successfully: {summary}")
            
            return session_id, summary
            
        except Exception as e:
            # エラー情報を保存
            self.intermediate_manager.save_progress(session_id, {
                'status': 'error',
                'error': str(e),
                'error_at': time.time(),
                'search_params': search_params.__dict__
            })
            self.logger.error(f"Search failed: {e}")
            raise
    
    async def _stream_api_to_intermediate(self, session_id: str, 
                                        search_params: AdvancedSearchParams,
                                        batch_size: int) -> None:
        """
        Step 1: API検索結果を中間ファイルにストリーム保存
        
        Args:
            session_id: セッションID
            search_params: 検索パラメータ
            batch_size: バッチサイズ
        """
        self.logger.info("Step 1: Streaming API results to intermediate file...")
        
        # プログレス確認（再開の場合）
        progress = self.intermediate_manager.load_progress(session_id)
        if progress and progress.get('step1_completed'):
            self.logger.info("Step 1 already completed, skipping...")
            return
        
        total_fetched = 0
        start_time = time.time()
        
        try:
            # ストリーミング検索を実行
            async for batch_result in self.search_engine.search_streaming(search_params, batch_size):
                if batch_result.models:
                    # 中間ファイルに保存
                    success = self.intermediate_manager.stream_write_models(
                        session_id, batch_result.models, 'raw'
                    )
                    
                    if not success:
                        raise Exception("Failed to write models to intermediate file")
                    
                    total_fetched += len(batch_result.models)
                    
                    # プログレス更新
                    self.intermediate_manager.save_progress(session_id, {
                        'step': 1,
                        'step1_fetched': total_fetched,
                        'step1_last_batch_time': time.time(),
                        'search_params': search_params.__dict__
                    })
                    
                    self.logger.info(f"Fetched batch: {len(batch_result.models)} models (total: {total_fetched})")
                    
                    # レート制限対応
                    await asyncio.sleep(0.1)
            
            # Step 1 完了マーク
            self.intermediate_manager.save_progress(session_id, {
                'step': 1,
                'step1_completed': True,
                'step1_total_models': total_fetched,
                'step1_duration': time.time() - start_time,
                'search_params': search_params.__dict__
            })
            
            self.logger.info(f"Step 1 completed: {total_fetched} models fetched in {time.time() - start_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Step 1 failed: {e}")
            raise
    
    async def _stream_filter_intermediate(self, session_id: str,
                                        search_params: AdvancedSearchParams,
                                        batch_size: int) -> None:
        """
        Step 2: 中間ファイルからフィルタリング処理
        
        Args:
            session_id: セッションID
            search_params: 検索パラメータ
            batch_size: バッチサイズ
        """
        self.logger.info("Step 2: Filtering intermediate file...")
        
        # プログレス確認
        progress = self.intermediate_manager.load_progress(session_id)
        if progress and progress.get('step2_completed'):
            self.logger.info("Step 2 already completed, skipping...")
            return
        
        total_processed = 0
        total_filtered = 0
        start_time = time.time()
        
        try:
            # ローカル版LocalVersionFilterを使用
            from ..search.search_engine import LocalVersionFilter
            version_filter = LocalVersionFilter()
            
            # 中間ファイルをストリーム読み込み
            for batch in self.intermediate_manager.stream_read_models(session_id, 'raw', batch_size):
                # フィルタリング実行
                filtered_models, filter_stats = version_filter.filter_by_version_criteria(
                    batch,
                    base_model=search_params.base_model,
                    model_types=search_params.model_types,
                    categories=[cat.value for cat in search_params.categories] if search_params.categories else None
                )
                
                if filtered_models:
                    # フィルタリング済みを中間ファイルに保存
                    success = self.intermediate_manager.stream_write_models(
                        session_id, filtered_models, 'filtered'
                    )
                    
                    if not success:
                        raise Exception("Failed to write filtered models to intermediate file")
                
                total_processed += len(batch)
                total_filtered += len(filtered_models)
                
                # プログレス更新
                self.intermediate_manager.save_progress(session_id, {
                    'step': 2,
                    'step2_processed': total_processed,
                    'step2_filtered': total_filtered,
                    'step2_last_batch_time': time.time(),
                    'search_params': search_params.__dict__
                })
                
                self.logger.info(f"Filtered batch: {len(batch)} → {len(filtered_models)} (total: {total_filtered}/{total_processed})")
            
            # Step 2 完了マーク
            self.intermediate_manager.save_progress(session_id, {
                'step': 2,
                'step2_completed': True,
                'step2_total_processed': total_processed,
                'step2_total_filtered': total_filtered,
                'step2_duration': time.time() - start_time,
                'search_params': search_params.__dict__
            })
            
            self.logger.info(f"Step 2 completed: {total_filtered}/{total_processed} models filtered in {time.time() - start_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Step 2 failed: {e}")
            raise
    
    async def _stream_final_processing(self, session_id: str, batch_size: int) -> None:
        """
        Step 3: 最終処理（カテゴリ分類等）
        
        Args:
            session_id: セッションID
            batch_size: バッチサイズ
        """
        self.logger.info("Step 3: Final processing (category classification)...")
        
        # プログレス確認
        progress = self.intermediate_manager.load_progress(session_id)
        if progress and progress.get('step3_completed'):
            self.logger.info("Step 3 already completed, skipping...")
            return
        
        total_processed = 0
        start_time = time.time()
        
        try:
            # フィルタリング済みファイルをストリーム読み込み
            for batch in self.intermediate_manager.stream_read_models(session_id, 'filtered', batch_size):
                processed_models = []
                
                for model in batch:
                    # カテゴリ分類
                    primary_category, all_categories = self.category_classifier.classify_model(model)
                    
                    # 処理済みデータに分類結果を追加
                    processed_model = model.copy()
                    processed_model['_processing'] = {
                        'primary_category': primary_category,
                        'all_categories': all_categories,
                        'processed_at': time.time()
                    }
                    
                    processed_models.append(processed_model)
                
                # 処理済みを中間ファイルに保存
                success = self.intermediate_manager.stream_write_models(
                    session_id, processed_models, 'processed'
                )
                
                if not success:
                    raise Exception("Failed to write processed models to intermediate file")
                
                total_processed += len(processed_models)
                
                # プログレス更新
                self.intermediate_manager.save_progress(session_id, {
                    'step': 3,
                    'step3_processed': total_processed,
                    'step3_last_batch_time': time.time()
                })
                
                self.logger.info(f"Processed batch: {len(processed_models)} models (total: {total_processed})")
            
            # Step 3 完了マーク
            self.intermediate_manager.save_progress(session_id, {
                'step': 3,
                'step3_completed': True,
                'step3_total_processed': total_processed,
                'step3_duration': time.time() - start_time
            })
            
            self.logger.info(f"Step 3 completed: {total_processed} models processed in {time.time() - start_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Step 3 failed: {e}")
            raise
    
    def get_processed_models_stream(self, session_id: str, 
                                  batch_size: int = 100) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        処理済みモデルをストリーム取得
        
        Args:
            session_id: セッションID
            batch_size: バッチサイズ
            
        Yields:
            処理済みモデルのバッチ
        """
        async def _stream():
            for batch in self.intermediate_manager.stream_read_models(session_id, 'processed', batch_size):
                yield batch
        
        return _stream()
    
    def cleanup_session(self, session_id: str, keep_final: bool = True) -> None:
        """
        セッションのクリーンアップ
        
        Args:
            session_id: セッションID
            keep_final: 最終処理済みファイルを保持するか
        """
        self.intermediate_manager.cleanup_session(session_id, keep_final)