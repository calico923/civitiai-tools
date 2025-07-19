#!/usr/bin/env python3
"""
CivitAI 重複分析スクリプト

総当たり検索結果から重複パターンを分析し、最終的なユニークモデルリストを生成する。

Usage:
    python duplicate_analyzer.py --input-dir outputs/search_analysis --output comprehensive_analysis.json
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter


class DuplicateAnalyzer:
    """重複分析を実行するクラス"""
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.search_results = []
        self.model_id_to_combinations = defaultdict(list)
        self.combination_to_models = defaultdict(set)
        
    def load_search_results(self) -> None:
        """検索結果ファイルを読み込み"""
        print("📂 検索結果ファイルを読み込み中...")
        
        result_files = list(self.input_dir.glob("*_search_results.json"))
        
        if not result_files:
            print("❌ 検索結果ファイルが見つかりません")
            return
        
        for result_file in result_files:
            print(f"  📄 読み込み中: {result_file.name}")
            
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for search_result in data.get('search_results', []):
                    self.search_results.append(search_result)
                    
                    # 組み合わせ情報を構築
                    combination = (
                        search_result['base_model'],
                        search_result['model_type'],
                        search_result['tag'],
                        search_result['sort_order']
                    )
                    
                    for model_id in search_result['unique_ids']:
                        self.model_id_to_combinations[model_id].append(combination)
                        self.combination_to_models[combination].add(model_id)
        
        print(f"✅ {len(self.search_results)}個の検索結果を読み込み完了")
    
    def analyze_duplicates(self) -> Dict:
        """重複パターンを分析"""
        print("\n🔍 重複パターンを分析中...")
        
        # 基本統計
        all_model_ids = set(self.model_id_to_combinations.keys())
        total_found_instances = sum(len(search['unique_ids']) for search in self.search_results)
        
        # 重複度別分析
        duplication_levels = Counter()
        for model_id, combinations in self.model_id_to_combinations.items():
            duplication_levels[len(combinations)] += 1
        
        # 最も重複の多いモデル
        most_duplicated = sorted(
            self.model_id_to_combinations.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]
        
        # Base Model別重複分析
        base_model_overlaps = self._analyze_base_model_overlaps()
        
        # Tag別重複分析
        tag_overlaps = self._analyze_tag_overlaps()
        
        # Sort Order効果分析
        sort_effectiveness = self._analyze_sort_effectiveness()
        
        analysis_result = {
            "basic_stats": {
                "total_search_combinations": len(self.search_results),
                "total_found_instances": total_found_instances,
                "unique_model_count": len(all_model_ids),
                "overall_duplication_rate": 1 - (len(all_model_ids) / max(total_found_instances, 1)),
                "average_duplication_per_model": total_found_instances / len(all_model_ids) if all_model_ids else 0
            },
            "duplication_levels": dict(duplication_levels),
            "most_duplicated_models": [
                {
                    "model_id": model_id,
                    "duplication_count": len(combinations),
                    "found_in_combinations": len(combinations),
                    "combinations": [
                        f"{c[0]}+{c[1]}+{c[2]}+{c[3]}" for c in combinations[:5]
                    ]  # 最初の5組み合わせのみ表示
                }
                for model_id, combinations in most_duplicated
            ],
            "base_model_analysis": base_model_overlaps,
            "tag_analysis": tag_overlaps,
            "sort_effectiveness": sort_effectiveness,
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis_result
    
    def _analyze_base_model_overlaps(self) -> Dict:
        """Base Model間の重複を分析"""
        base_models = ["Illustrious", "NoobAI", "Pony", "Animagine"]
        overlaps = {}
        
        # 各Base Modelで発見されたモデルIDセットを構築
        base_model_sets = {}
        for base_model in base_models:
            model_ids = set()
            for search in self.search_results:
                if search['base_model'] == base_model:
                    model_ids.update(search['unique_ids'])
            base_model_sets[base_model] = model_ids
        
        # 重複分析
        for i, base_model1 in enumerate(base_models):
            for base_model2 in base_models[i+1:]:
                set1 = base_model_sets[base_model1]
                set2 = base_model_sets[base_model2]
                
                intersection = set1 & set2
                union = set1 | set2
                
                overlaps[f"{base_model1}_vs_{base_model2}"] = {
                    "base_model1_unique": len(set1),
                    "base_model2_unique": len(set2),
                    "intersection": len(intersection),
                    "union": len(union),
                    "jaccard_similarity": len(intersection) / len(union) if union else 0,
                    "overlap_rate1": len(intersection) / len(set1) if set1 else 0,
                    "overlap_rate2": len(intersection) / len(set2) if set2 else 0
                }
        
        return overlaps
    
    def _analyze_tag_overlaps(self) -> Dict:
        """Tag間の重複を分析"""
        tags = ["style", "concept", "pose", "nsfw", "sexy", "hentai"]
        tag_stats = {}
        
        for tag in tags:
            model_ids = set()
            search_count = 0
            
            for search in self.search_results:
                if search['tag'] == tag:
                    model_ids.update(search['unique_ids'])
                    search_count += 1
            
            tag_stats[tag] = {
                "unique_models": len(model_ids),
                "search_combinations": search_count,
                "avg_models_per_combination": len(model_ids) / search_count if search_count > 0 else 0
            }
        
        return tag_stats
    
    def _analyze_sort_effectiveness(self) -> Dict:
        """Sort Order別の効果を分析"""
        sort_orders = [
            "Highest Rated", "Most Downloaded", "Most Liked",
            "Most Images", "Most Collected", "Newest", "Oldest"
        ]
        
        sort_stats = {}
        
        for sort_order in sort_orders:
            model_ids = set()
            search_count = 0
            total_found = 0
            
            for search in self.search_results:
                if search['sort_order'] == sort_order:
                    model_ids.update(search['unique_ids'])
                    search_count += 1
                    total_found += search['found_count']
            
            sort_stats[sort_order] = {
                "unique_models": len(model_ids),
                "search_combinations": search_count,
                "total_found_instances": total_found,
                "avg_models_per_combination": total_found / search_count if search_count > 0 else 0,
                "unique_discovery_rate": len(model_ids) / total_found if total_found > 0 else 0
            }
        
        return sort_stats
    
    def generate_optimized_search_plan(self) -> Dict:
        """効率的な検索計画を生成"""
        print("\n🎯 最適化された検索計画を生成中...")
        
        # 各組み合わせの効率性を評価
        combination_efficiency = []
        
        for search in self.search_results:
            if search['found_count'] > 0:
                # ユニークモデル発見率を計算
                unique_models_in_this_search = set(search['unique_ids'])
                
                # この組み合わせでのみ発見されたモデル数
                exclusive_models = 0
                for model_id in unique_models_in_this_search:
                    if len(self.model_id_to_combinations[model_id]) == 1:
                        exclusive_models += 1
                
                efficiency = {
                    "combination": f"{search['base_model']}+{search['model_type']}+{search['tag']}+{search['sort_order']}",
                    "found_count": search['found_count'],
                    "exclusive_models": exclusive_models,
                    "efficiency_score": exclusive_models / search['found_count'] if search['found_count'] > 0 else 0,
                    "search_time": search['search_time']
                }
                
                combination_efficiency.append(efficiency)
        
        # 効率性でソート
        combination_efficiency.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
        # 上位組み合わせで全ユニークモデルをカバーできるか分析
        covered_models = set()
        optimal_combinations = []
        
        for combo in combination_efficiency:
            # この組み合わせで新たに発見されるモデル数を計算
            combo_parts = combo['combination'].split('+')
            if len(combo_parts) == 4:
                base_model, model_type, tag, sort_order = combo_parts
                
                search_result = next(
                    (s for s in self.search_results 
                     if s['base_model'] == base_model and 
                        s['model_type'] == model_type and 
                        s['tag'] == tag and 
                        s['sort_order'] == sort_order),
                    None
                )
                
                if search_result:
                    new_models = set(search_result['unique_ids']) - covered_models
                    if new_models:
                        optimal_combinations.append({
                            "combination": combo['combination'],
                            "new_models_discovered": len(new_models),
                            "cumulative_coverage": len(covered_models) + len(new_models),
                            "efficiency_score": combo['efficiency_score']
                        })
                        covered_models.update(new_models)
                        
                        # 95%のカバー率に達したら終了
                        total_unique = len(self.model_id_to_combinations)
                        if len(covered_models) / total_unique >= 0.95:
                            break
        
        return {
            "total_combinations_analyzed": len(self.search_results),
            "total_unique_models": len(self.model_id_to_combinations),
            "optimal_combination_count": len(optimal_combinations),
            "coverage_with_optimal": len(covered_models),
            "coverage_percentage": len(covered_models) / len(self.model_id_to_combinations) * 100,
            "reduction_rate": (len(self.search_results) - len(optimal_combinations)) / len(self.search_results) * 100,
            "optimal_combinations": optimal_combinations[:20]  # 上位20組み合わせ
        }
    
    def export_final_results(self, output_file: str) -> None:
        """最終分析結果をエクスポート"""
        print(f"\n📊 最終分析結果をエクスポート中: {output_file}")
        
        # 重複分析実行
        duplicate_analysis = self.analyze_duplicates()
        
        # 最適化計画生成
        optimization_plan = self.generate_optimized_search_plan()
        
        # 最終ユニークモデルリスト
        final_unique_models = list(self.model_id_to_combinations.keys())
        
        final_results = {
            "analysis_summary": {
                "analysis_date": datetime.now().isoformat(),
                "input_directory": str(self.input_dir),
                "total_search_results": len(self.search_results),
                "final_unique_model_count": len(final_unique_models)
            },
            "duplicate_analysis": duplicate_analysis,
            "optimization_plan": optimization_plan,
            "final_unique_models": final_unique_models,
            "recommendations": self._generate_recommendations(duplicate_analysis, optimization_plan)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ エクスポート完了: {output_file}")
        
        # サマリー表示
        self._print_analysis_summary(duplicate_analysis, optimization_plan)
    
    def _generate_recommendations(self, duplicate_analysis: Dict, optimization_plan: Dict) -> List[str]:
        """分析結果に基づく推奨事項を生成"""
        recommendations = []
        
        # 重複率に基づく推奨
        duplication_rate = duplicate_analysis['basic_stats']['overall_duplication_rate']
        if duplication_rate > 0.7:
            recommendations.append("重複率が70%を超えています。より効率的な検索戦略の検討を推奨します。")
        
        # Base Model分析に基づく推奨
        base_analysis = duplicate_analysis['base_model_analysis']
        high_overlap_pairs = [
            pair for pair, data in base_analysis.items()
            if data['jaccard_similarity'] > 0.5
        ]
        if high_overlap_pairs:
            recommendations.append(f"以下のBase Model組み合わせで高い重複が検出されました: {', '.join(high_overlap_pairs)}")
        
        # 最適化に基づく推奨
        reduction_rate = optimization_plan['reduction_rate']
        if reduction_rate > 50:
            recommendations.append(f"検索組み合わせを{reduction_rate:.1f}%削減しても95%のカバー率を達成可能です。")
        
        return recommendations
    
    def _print_analysis_summary(self, duplicate_analysis: Dict, optimization_plan: Dict) -> None:
        """分析結果のサマリーを表示"""
        basic_stats = duplicate_analysis['basic_stats']
        
        print(f"\n" + "="*60)
        print(f"📊 重複分析結果サマリー")
        print(f"="*60)
        print(f"🔍 総検索組み合わせ: {basic_stats['total_search_combinations']:,}")
        print(f"📊 発見インスタンス総数: {basic_stats['total_found_instances']:,}")
        print(f"🆔 ユニークモデル数: {basic_stats['unique_model_count']:,}")
        print(f"📈 全体重複率: {basic_stats['overall_duplication_rate']*100:.1f}%")
        print(f"🎯 最適組み合わせ数: {optimization_plan['optimal_combination_count']}")
        print(f"💡 効率化可能率: {optimization_plan['reduction_rate']:.1f}%")
        print(f"="*60)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="CivitAI 重複分析実行"
    )
    
    parser.add_argument(
        "--input-dir",
        default="outputs/search_analysis",
        help="検索結果ディレクトリ (default: outputs/search_analysis)"
    )
    parser.add_argument(
        "--output",
        default="comprehensive_analysis.json",
        help="出力ファイル名 (default: comprehensive_analysis.json)"
    )
    
    args = parser.parse_args()
    
    # 分析実行
    analyzer = DuplicateAnalyzer(args.input_dir)
    
    try:
        analyzer.load_search_results()
        analyzer.export_final_results(args.output)
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        raise


if __name__ == "__main__":
    main()