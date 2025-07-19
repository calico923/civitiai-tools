#!/usr/bin/env python3
"""
CivitAI 総当たり検索スクリプト

指定されたBase Models、Types、Tags、Sort Ordersの全組み合わせで検索を実行し、
結果を分析用データとして保存する。

Usage:
    python comprehensive_search.py --base-models illustrious noobai pony animagine --limit 500
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
from dataclasses import dataclass, asdict

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.client import CivitaiClient
from src.core.enhanced_url_collector import EnhancedURLCollector


@dataclass
class SearchResult:
    """検索結果を格納するデータクラス"""
    base_model: str
    model_type: str
    tag: str
    sort_order: str
    found_count: int
    unique_ids: List[int]
    search_time: float
    api_calls: int
    timestamp: str
    error: str = None


class ComprehensiveSearcher:
    """総当たり検索を実行するクラス"""
    
    def __init__(self, api_key: str, output_dir: str = "outputs/search_analysis"):
        self.client = CivitaiClient(api_key)
        self.enhanced_collector = EnhancedURLCollector(api_key=api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced output directory
        self.enhanced_output_dir = Path(output_dir) / "enhanced"
        self.enhanced_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 検索パラメータ
        self.base_models = ["Illustrious", "NoobAI", "Pony", "Animagine"]
        self.model_types = ["Checkpoint", "LORA", "LyCORIS"]
        self.tags = ["style", "concept", "pose", "nsfw", "sexy", "hentai"]
        # 初回は3つのSort Orderに絞る
        self.sort_orders = [
            "Highest Rated", "Most Downloaded", "Most Liked"
        ]
        
        # 2回目の調査で追加予定
        self.sort_orders_phase2 = [
            "Most Images", "Most Collected", "Newest", "Oldest"
        ]
        
        # 統計情報（Model Type別に分離）
        self.all_model_ids: Set[int] = set()
        self.model_ids_by_type: Dict[str, Set[int]] = {
            "Checkpoint": set(),
            "LORA": set(),
            "LyCORIS": set()
        }
        self.search_results: List[SearchResult] = []
        self.total_api_calls = 0
        self.start_time = datetime.now()
    
    def calculate_total_combinations(self) -> int:
        """総検索組み合わせ数を計算"""
        return len(self.base_models) * len(self.model_types) * len(self.tags) * len(self.sort_orders)
    
    def search_single_combination(self, 
                                base_model: str, 
                                model_type: str, 
                                tag: str, 
                                sort_order: str,
                                limit: int = 500) -> SearchResult:
        """単一の組み合わせで検索を実行"""
        
        search_start = time.time()
        api_calls = 0
        unique_ids = []
        models_data = []  # 詳細なモデルデータを保存
        error = None
        
        try:
            print(f"🔍 {base_model} + {model_type} + {tag} + {sort_order}")
            
            # API検索実行
            models = self.client.search_models_with_cursor(
                types=[model_type],
                tag=tag,
                base_models=[base_model],
                sort=sort_order,
                limit=100,  # API制限
                max_pages=min(5, limit // 100 + 1)  # 最大5ページまたは指定limit分
            )
            
            # モデルIDを抽出（Type別に管理）
            for model in models[:limit]:  # 上限を適用
                model_id = model.get('id')
                if model_id:
                    unique_ids.append(model_id)
                    models_data.append(model)  # 詳細データも保存
                    self.all_model_ids.add(model_id)
                    # Model Type別にも追加
                    if model_type in self.model_ids_by_type:
                        self.model_ids_by_type[model_type].add(model_id)
            
            # Enhanced output の生成（少量の場合のみ）
            if len(models_data) <= 100:  # 大量データの場合はスキップ
                self._save_enhanced_results(models_data, base_model, model_type, tag, sort_order)
            
            api_calls = min(5, limit // 100 + 1)  # 実際のAPI呼び出し数
            self.total_api_calls += api_calls
            
            print(f"  ✅ {len(unique_ids)}個のモデルを発見")
            
        except Exception as e:
            error = str(e)
            print(f"  ❌ エラー: {error}")
        
        search_time = time.time() - search_start
        
        return SearchResult(
            base_model=base_model,
            model_type=model_type,
            tag=tag,
            sort_order=sort_order,
            found_count=len(unique_ids),
            unique_ids=unique_ids,
            search_time=search_time,
            api_calls=api_calls,
            timestamp=datetime.now().isoformat(),
            error=error
        )
    
    def run_comprehensive_search(self, 
                               base_models: List[str] = None,
                               limit: int = 500,
                               save_frequency: int = 50) -> None:
        """総当たり検索を実行"""
        
        if base_models is None:
            base_models = self.base_models
        
        # 検索対象のBase Modelsを正規化
        normalized_base_models = []
        for bm in base_models:
            if bm.lower() == "illustrious":
                normalized_base_models.append("Illustrious")
            elif bm.lower() == "noobai":
                normalized_base_models.append("NoobAI")
            elif bm.lower() == "pony":
                normalized_base_models.append("Pony")
            elif bm.lower() == "animagine":
                normalized_base_models.append("Animagine")
            else:
                normalized_base_models.append(bm.title())
        
        total_combinations = len(normalized_base_models) * len(self.model_types) * len(self.tags) * len(self.sort_orders)
        current_combination = 0
        
        print(f"🚀 総当たり検索開始")
        print(f"📊 検索組み合わせ数: {total_combinations}")
        print(f"📋 Base Models: {normalized_base_models}")
        print(f"🎯 各組み合わせの上限: {limit}モデル")
        print(f"⏱️ 推定実行時間: {total_combinations * 2 / 60:.1f}分")
        print()
        
        for base_model in normalized_base_models:
            print(f"\n🔎 Base Model: {base_model} の検索開始")
            base_model_results = []
            
            for model_type in self.model_types:
                for tag in self.tags:
                    for sort_order in self.sort_orders:
                        current_combination += 1
                        
                        print(f"📈 進行状況: {current_combination}/{total_combinations} ({current_combination/total_combinations*100:.1f}%)")
                        
                        # 検索実行
                        result = self.search_single_combination(
                            base_model, model_type, tag, sort_order, limit
                        )
                        
                        self.search_results.append(result)
                        base_model_results.append(result)
                        
                        # 定期的に結果を保存
                        if current_combination % save_frequency == 0:
                            self._save_intermediate_results(base_model)
                        
                        # レート制限対策
                        time.sleep(0.5)
            
            # Base Model毎に結果を保存
            self._save_base_model_results(base_model, base_model_results)
            print(f"✅ {base_model} の検索完了 ({len(base_model_results)}組み合わせ)")
        
        # 最終結果を保存
        self._save_final_results()
        
        # 全体の Enhanced 出力を生成
        self._generate_comprehensive_enhanced_output()
        
        # サマリー表示
        self._print_summary()
    
    def _save_base_model_results(self, base_model: str, results: List[SearchResult]) -> None:
        """Base Model毎の結果を保存"""
        filename = f"{base_model.lower()}_search_results.json"
        filepath = self.output_dir / filename
        
        data = {
            "base_model": base_model,
            "total_combinations": len(results),
            "total_found_models": sum(r.found_count for r in results),
            "unique_model_ids": list(set(model_id for r in results for model_id in r.unique_ids)),
            "search_results": [asdict(result) for result in results],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 保存完了: {filepath}")
    
    def _save_intermediate_results(self, current_base_model: str) -> None:
        """中間結果を保存（再開用）"""
        filename = f"intermediate_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        data = {
            "current_base_model": current_base_model,
            "total_combinations_completed": len(self.search_results),
            "unique_model_ids_so_far": list(self.all_model_ids),
            "search_results": [asdict(result) for result in self.search_results],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_final_results(self) -> None:
        """最終的な統合結果を保存"""
        
        # 1. 総合サマリー
        summary_data = {
            "search_summary": {
                "total_combinations": len(self.search_results),
                "total_api_calls": self.total_api_calls,
                "total_found_models": sum(r.found_count for r in self.search_results),
                "unique_model_count": len(self.all_model_ids),
                "duplication_rate": 1 - (len(self.all_model_ids) / max(sum(r.found_count for r in self.search_results), 1)),
                "execution_time_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            },
            "base_model_stats": self._calculate_base_model_stats(),
            "type_stats": self._calculate_type_stats(),
            "tag_stats": self._calculate_tag_stats(),
            "sort_stats": self._calculate_sort_stats()
        }
        
        summary_file = self.output_dir / "comprehensive_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        # 2. 全ユニークモデルID
        unique_models_file = self.output_dir / "final_unique_models.json"
        unique_data = {
            "unique_model_ids": list(self.all_model_ids),
            "count": len(self.all_model_ids),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(unique_models_file, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 最終結果保存完了:")
        print(f"  📊 サマリー: {summary_file}")
        print(f"  🆔 ユニークモデル: {unique_models_file}")
    
    def _save_enhanced_results(self, models_data: List[Dict], base_model: str, model_type: str, tag: str, sort_order: str) -> None:
        """個別の検索結果をEnhanced形式で保存"""
        if not models_data:
            return
        
        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{base_model}_{model_type}_{tag}_{sort_order.replace(' ', '_')}_{timestamp}"
        
        try:
            # Enhanced URL Collectorで情報を収集
            model_infos = self.enhanced_collector.collect_enhanced_model_info(models_data)
            
            if model_infos:
                # 複数形式でエクスポート
                exported_files = self.enhanced_collector.export_all_formats(
                    model_infos, 
                    safe_filename,
                    output_dir=self.enhanced_output_dir
                )
                
                print(f"  💾 Enhanced出力: {len(model_infos)}モデル -> {safe_filename}")
        
        except Exception as e:
            print(f"  ⚠️ Enhanced出力エラー: {e}")
    
    def _generate_comprehensive_enhanced_output(self) -> None:
        """全体の検索結果から総合Enhanced出力を生成"""
        print(f"\n📦 総合Enhanced出力を生成中...")
        
        try:
            # Type別にユニークモデルIDを収集
            for model_type, unique_ids in self.model_ids_by_type.items():
                if not unique_ids:
                    continue
                
                print(f"  🔍 {model_type}: {len(unique_ids)}ユニークモデルを処理中...")
                
                # APIでモデル詳細を取得（バッチ処理）
                models_data = []
                for i, model_id in enumerate(list(unique_ids)[:500]):  # 最大5003067で制限
                    if i > 0 and i % 50 == 0:
                        print(f"    進行状況: {i}/{min(len(unique_ids), 500)}")
                        time.sleep(2)  # レート制限対策
                    
                    try:
                        model_data = self.client.get_model_by_id(model_id)
                        if model_data:
                            models_data.append(model_data)
                    except Exception as e:
                        print(f"    ⚠️ モデルID {model_id} の取得に失敗: {e}")
                        continue
                
                if models_data:
                    # Enhanced出力を生成
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comprehensive_{model_type.lower()}_{timestamp}"
                    
                    model_infos = self.enhanced_collector.collect_enhanced_model_info(models_data)
                    if model_infos:
                        exported_files = self.enhanced_collector.export_all_formats(
                            model_infos, 
                            filename,
                            output_dir=self.enhanced_output_dir
                        )
                        
                        print(f"  ✅ {model_type} Enhanced出力完了: {len(model_infos)}モデル")
                        print(f"    CSV: {exported_files.get('csv', 'N/A')}")
                        print(f"    JSON: {exported_files.get('json', 'N/A')}")
                        print(f"    HTML: {exported_files.get('html', 'N/A')}")
        
        except Exception as e:
            print(f"  ❌ 総合Enhanced出力エラー: {e}")
    
    def _calculate_base_model_stats(self) -> Dict:
        """Base Model別の統計を計算"""
        stats = {}
        for base_model in self.base_models:
            results = [r for r in self.search_results if r.base_model == base_model]
            if results:
                unique_ids = set()
                for r in results:
                    unique_ids.update(r.unique_ids)
                
                stats[base_model] = {
                    "combinations": len(results),
                    "total_found": sum(r.found_count for r in results),
                    "unique_models": len(unique_ids),
                    "avg_models_per_search": sum(r.found_count for r in results) / len(results)
                }
        return stats
    
    def _calculate_type_stats(self) -> Dict:
        """Type別の統計を計算"""
        stats = {}
        for model_type in self.model_types:
            results = [r for r in self.search_results if r.model_type == model_type]
            if results:
                unique_ids = set()
                for r in results:
                    unique_ids.update(r.unique_ids)
                
                stats[model_type] = {
                    "combinations": len(results),
                    "total_found": sum(r.found_count for r in results),
                    "unique_models": len(unique_ids)
                }
        return stats
    
    def _calculate_tag_stats(self) -> Dict:
        """Tag別の統計を計算"""
        stats = {}
        for tag in self.tags:
            results = [r for r in self.search_results if r.tag == tag]
            if results:
                unique_ids = set()
                for r in results:
                    unique_ids.update(r.unique_ids)
                
                stats[tag] = {
                    "combinations": len(results),
                    "total_found": sum(r.found_count for r in results),
                    "unique_models": len(unique_ids)
                }
        return stats
    
    def _calculate_sort_stats(self) -> Dict:
        """Sort Order別の統計を計算"""
        stats = {}
        for sort_order in self.sort_orders:
            results = [r for r in self.search_results if r.sort_order == sort_order]
            if results:
                stats[sort_order] = {
                    "combinations": len(results),
                    "total_found": sum(r.found_count for r in results),
                    "avg_models_per_search": sum(r.found_count for r in results) / len(results)
                }
        return stats
    
    def _print_summary(self) -> None:
        """実行結果のサマリーを表示"""
        execution_time = (datetime.now() - self.start_time).total_seconds() / 60
        total_found = sum(r.found_count for r in self.search_results)
        
        print(f"\n" + "="*60)
        print(f"🎉 総当たり検索完了!")
        print(f"="*60)
        print(f"⏱️ 実行時間: {execution_time:.1f}分")
        print(f"🔍 総検索組み合わせ: {len(self.search_results)}")
        print(f"📞 総API呼び出し: {self.total_api_calls}")
        print(f"📊 発見モデル総数: {total_found:,}")
        print(f"🆔 ユニークモデル数: {len(self.all_model_ids):,}")
        print(f"📈 重複率: {(1 - len(self.all_model_ids) / max(total_found, 1)) * 100:.1f}%")
        print(f"💾 結果保存先: {self.output_dir}")
        print(f"="*60)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="CivitAI 総当たり検索実行"
    )
    
    parser.add_argument(
        "--base-models",
        nargs="+",
        default=["illustrious", "noobai", "pony", "animagine"],
        choices=["illustrious", "noobai", "pony", "animagine"],
        help="検索対象のBase Models (default: all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="各組み合わせあたりの検索上限 (default: 500)"
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/search_analysis",
        help="出力ディレクトリ (default: outputs/search_analysis)"
    )
    parser.add_argument(
        "--save-frequency",
        type=int,
        default=50,
        help="中間保存の頻度 (default: 50組み合わせ毎)"
    )
    
    args = parser.parse_args()
    
    # APIキー取得
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("❌ エラー: CIVITAI_API_KEY環境変数を設定してください")
        sys.exit(1)
    
    # 検索実行
    searcher = ComprehensiveSearcher(api_key, args.output_dir)
    
    try:
        searcher.run_comprehensive_search(
            base_models=args.base_models,
            limit=args.limit,
            save_frequency=args.save_frequency
        )
    except KeyboardInterrupt:
        print("\n⚠️ 検索が中断されました")
        print("💾 中間結果を保存中...")
        searcher._save_intermediate_results("interrupted")
        print("✅ 中間結果保存完了")


if __name__ == "__main__":
    main()