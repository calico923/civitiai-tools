#!/usr/bin/env python3
"""
CivitAI APIで全モデルタイプにおけるbaseModelの分布を包括的に調査

このスクリプトは以下を実行します:
1. 各モデルタイプ（Checkpoint、LORA、LoCon、TextualInversion、VAE等）でのbaseModelの分布調査
2. 主要なbaseModelカテゴリの出現頻度分析
3. baseModelフィールドの値の正規化
4. 統計結果をCSVとJSONで出力
"""

import os
import sys
import json
import csv
import time
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Optional, Set
import re

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.client import CivitaiClient


class BaseModelAnalyzer:
    """BaseModel分布の包括的分析"""
    
    def __init__(self, api_key: str):
        self.client = CivitaiClient(api_key)
        self.results = {}
        self.normalized_basemodels = {}
        self.all_raw_basemodels = set()
        
        # 調査対象のモデルタイプ
        self.model_types = [
            "Checkpoint",
            "LORA",
            "LoCon",
            "TextualInversion",
            "VAE",
            "Hypernetwork",
            "AestheticGradient",
            "Embedding",
            "Poses",
            "Wildcards",
            "Workflows",
            "Other"
        ]
        
        # BaseModelの正規化ルール
        self.normalization_rules = {
            # SDXL系
            r'sdxl.*1\.0': 'SDXL 1.0',
            r'sdxl.*0\.9': 'SDXL 0.9',
            r'sdxl.*base': 'SDXL 1.0',
            r'sdxl': 'SDXL 1.0',
            r'sd.*xl': 'SDXL 1.0',
            
            # SD系
            r'sd.*1\.5': 'SD 1.5',
            r'sd.*1\.4': 'SD 1.4',
            r'sd.*2\.1': 'SD 2.1',
            r'sd.*2\.0': 'SD 2.0',
            r'stable.*diffusion.*1\.5': 'SD 1.5',
            r'stable.*diffusion.*1\.4': 'SD 1.4',
            r'stable.*diffusion.*2\.1': 'SD 2.1',
            r'stable.*diffusion.*2\.0': 'SD 2.0',
            
            # Pony系
            r'pony.*diffusion.*v6': 'Pony Diffusion V6 XL',
            r'pony.*v6': 'Pony Diffusion V6 XL',
            r'pony.*diffusion': 'Pony Diffusion V6 XL',
            r'pony': 'Pony Diffusion V6 XL',
            
            # Illustrious系
            r'illustrious.*xl': 'Illustrious XL',
            r'illustrious': 'Illustrious XL',
            
            # NoobAI系
            r'noobai.*xl': 'NoobAI XL',
            r'noobai': 'NoobAI XL',
            
            # Flux系
            r'flux.*1.*dev': 'FLUX.1 [dev]',
            r'flux.*1.*schnell': 'FLUX.1 [schnell]',
            r'flux.*dev': 'FLUX.1 [dev]',
            r'flux.*schnell': 'FLUX.1 [schnell]',
            r'flux': 'FLUX.1 [dev]',
            
            # その他
            r'other': 'Other',
            r'none': 'None',
            r'unknown': 'Unknown',
            r'n/a': 'N/A',
            r'custom': 'Custom',
        }
    
    def normalize_basemodel(self, basemodel: str) -> str:
        """baseModelの名前を正規化"""
        if not basemodel:
            return "Unknown"
        
        # 小文字に変換して比較
        normalized = basemodel.lower().strip()
        
        # 正規化ルールを適用
        for pattern, replacement in self.normalization_rules.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                return replacement
        
        # マッチしない場合は元の値を返す（最初の文字を大文字に）
        return basemodel.strip()
    
    def analyze_model_type(self, model_type: str, sample_size: int = 200) -> Dict:
        """特定のモデルタイプのbaseModel分布を分析"""
        print(f"\n{'='*60}")
        print(f"分析中: {model_type}")
        print(f"{'='*60}")
        
        # モデルを取得
        try:
            models = self.client.search_models_with_cursor(
                types=[model_type],
                sort="Highest Rated",
                limit=100,
                max_pages=max(1, sample_size // 100)  # sample_sizeに基づいてページ数を調整
            )
            
            if not models:
                print(f"⚠️  {model_type}のモデルが見つかりませんでした")
                return {
                    "type": model_type,
                    "total_models": 0,
                    "basemodel_distribution": {},
                    "normalized_distribution": {},
                    "sample_models": []
                }
            
            # サンプルサイズに制限
            if len(models) > sample_size:
                models = models[:sample_size]
                print(f"サンプルを{sample_size}個に制限しました")
            
            print(f"分析対象: {len(models)}個のモデル")
            
            # baseModelの分布を集計
            raw_basemodels = []
            normalized_basemodels = []
            sample_models = []
            
            for model in models:
                # モデルバージョンから最新のbaseModelを取得
                model_versions = model.get("modelVersions", [])
                if model_versions:
                    latest_version = model_versions[0]  # 最初のバージョンが最新
                    base_model = latest_version.get("baseModel", "Unknown")
                else:
                    base_model = "Unknown"
                
                raw_basemodels.append(base_model)
                normalized = self.normalize_basemodel(base_model)
                normalized_basemodels.append(normalized)
                
                # 分析用のサンプルデータを保存
                sample_models.append({
                    "id": model.get("id"),
                    "name": model.get("name", "Unknown"),
                    "raw_basemodel": base_model,
                    "normalized_basemodel": normalized,
                    "tags": model.get("tags", []),
                    "stats": model.get("stats", {}),
                    "created_at": model.get("createdAt", ""),
                    "updated_at": model.get("updatedAt", "")
                })
                
                # 全体の統計用
                self.all_raw_basemodels.add(base_model)
            
            # 分布を計算
            raw_distribution = dict(Counter(raw_basemodels))
            normalized_distribution = dict(Counter(normalized_basemodels))
            
            # 結果を表示
            print(f"\n--- Raw BaseModel分布 ---")
            for basemodel, count in sorted(raw_distribution.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(models)) * 100
                print(f"  {basemodel}: {count}個 ({percentage:.1f}%)")
            
            print(f"\n--- Normalized BaseModel分布 ---")
            for basemodel, count in sorted(normalized_distribution.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(models)) * 100
                print(f"  {basemodel}: {count}個 ({percentage:.1f}%)")
            
            return {
                "type": model_type,
                "total_models": len(models),
                "basemodel_distribution": raw_distribution,
                "normalized_distribution": normalized_distribution,
                "sample_models": sample_models
            }
            
        except Exception as e:
            print(f"❌ {model_type}の分析でエラー: {e}")
            return {
                "type": model_type,
                "total_models": 0,
                "basemodel_distribution": {},
                "normalized_distribution": {},
                "sample_models": [],
                "error": str(e)
            }
    
    def run_comprehensive_analysis(self, sample_size_per_type: int = 200) -> Dict:
        """全モデルタイプの包括的分析を実行"""
        print("CivitAI BaseModel分布の包括的調査を開始します")
        print(f"各モデルタイプのサンプルサイズ: {sample_size_per_type}")
        
        start_time = time.time()
        
        # 各モデルタイプを分析
        for model_type in self.model_types:
            result = self.analyze_model_type(model_type, sample_size_per_type)
            self.results[model_type] = result
            
            # 進捗表示
            print(f"\n✅ {model_type}の分析完了")
            time.sleep(1)  # APIレート制限対応
        
        # 全体統計を計算
        total_models = sum(r["total_models"] for r in self.results.values())
        overall_normalized = defaultdict(int)
        overall_raw = defaultdict(int)
        
        for result in self.results.values():
            for basemodel, count in result["normalized_distribution"].items():
                overall_normalized[basemodel] += count
            for basemodel, count in result["basemodel_distribution"].items():
                overall_raw[basemodel] += count
        
        # 結果をまとめ
        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "total_models_analyzed": total_models,
            "model_types_analyzed": len(self.model_types),
            "sample_size_per_type": sample_size_per_type,
            "overall_normalized_distribution": dict(overall_normalized),
            "overall_raw_distribution": dict(overall_raw),
            "type_specific_results": self.results,
            "normalization_rules": self.normalization_rules,
            "unique_raw_basemodels": len(self.all_raw_basemodels),
            "analysis_duration_seconds": time.time() - start_time
        }
        
        return analysis_result
    
    def save_results(self, results: Dict, output_dir: str = "outputs/basemodel_analysis"):
        """結果をCSVとJSONで保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON形式で保存
        json_file = os.path.join(output_dir, f"basemodel_analysis_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 JSON結果を保存: {json_file}")
        
        # CSV形式で保存（概要）
        csv_file = os.path.join(output_dir, f"basemodel_summary_{timestamp}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー
            writer.writerow([
                "Model Type",
                "Total Models", 
                "Top BaseModel",
                "Top BaseModel Count",
                "Top BaseModel Percentage",
                "Unique BaseModels"
            ])
            
            # 各モデルタイプの概要
            for model_type, result in results["type_specific_results"].items():
                if result["total_models"] > 0:
                    normalized_dist = result["normalized_distribution"]
                    if normalized_dist:
                        top_basemodel = max(normalized_dist.items(), key=lambda x: x[1])
                        top_name, top_count = top_basemodel
                        top_percentage = (top_count / result["total_models"]) * 100
                        unique_count = len(normalized_dist)
                    else:
                        top_name, top_count, top_percentage, unique_count = "None", 0, 0, 0
                    
                    writer.writerow([
                        model_type,
                        result["total_models"],
                        top_name,
                        top_count,
                        f"{top_percentage:.1f}%",
                        unique_count
                    ])
        
        print(f"📊 CSV概要を保存: {csv_file}")
        
        # 詳細なBaseModel分布CSV
        detail_csv = os.path.join(output_dir, f"basemodel_distribution_{timestamp}.csv")
        with open(detail_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー
            writer.writerow([
                "Model Type",
                "BaseModel (Normalized)",
                "BaseModel (Raw)",
                "Count",
                "Percentage"
            ])
            
            # 各モデルタイプの詳細分布
            for model_type, result in results["type_specific_results"].items():
                if result["total_models"] > 0:
                    # 正規化された分布を処理
                    for norm_basemodel, count in sorted(result["normalized_distribution"].items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / result["total_models"]) * 100
                        
                        # 対応するrawベースモデルを探す
                        raw_basemodels = []
                        for model in result["sample_models"]:
                            if model["normalized_basemodel"] == norm_basemodel:
                                raw_basemodels.append(model["raw_basemodel"])
                        raw_unique = list(set(raw_basemodels))
                        
                        writer.writerow([
                            model_type,
                            norm_basemodel,
                            "; ".join(raw_unique),
                            count,
                            f"{percentage:.1f}%"
                        ])
        
        print(f"📈 詳細CSV分布を保存: {detail_csv}")
        
        return {
            "json_file": json_file,
            "csv_summary": csv_file,
            "csv_detail": detail_csv
        }
    
    def print_summary(self, results: Dict):
        """分析結果の概要を表示"""
        print(f"\n{'='*80}")
        print("BaseModel分布分析 - 概要")
        print(f"{'='*80}")
        
        print(f"📊 分析対象: {results['total_models_analyzed']:,}個のモデル")
        print(f"🔍 モデルタイプ数: {results['model_types_analyzed']}種類")
        print(f"⏱️  分析時間: {results['analysis_duration_seconds']:.1f}秒")
        print(f"🔧 ユニークなraw BaseModel: {results['unique_raw_basemodels']}種類")
        
        print(f"\n--- 全体のBaseModel分布 (正規化後) ---")
        for basemodel, count in sorted(results["overall_normalized_distribution"].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / results["total_models_analyzed"]) * 100
            print(f"  {basemodel}: {count:,}個 ({percentage:.1f}%)")
        
        print(f"\n--- モデルタイプ別概要 ---")
        for model_type, result in results["type_specific_results"].items():
            if result["total_models"] > 0:
                print(f"  {model_type}: {result['total_models']}個")
                if result["normalized_distribution"]:
                    top_basemodel = max(result["normalized_distribution"].items(), key=lambda x: x[1])
                    top_name, top_count = top_basemodel
                    top_percentage = (top_count / result["total_models"]) * 100
                    print(f"    → 最多: {top_name} ({top_count}個, {top_percentage:.1f}%)")
                else:
                    print(f"    → BaseModelデータなし")
        
        print(f"\n{'='*80}")


def main():
    """メイン実行関数"""
    # APIキーの確認
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("❌ CIVITAI_API_KEYが設定されていません")
        print("export CIVITAI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # 分析実行
    analyzer = BaseModelAnalyzer(api_key)
    
    try:
        # 包括的分析を実行
        results = analyzer.run_comprehensive_analysis(sample_size_per_type=200)
        
        # 結果を保存
        saved_files = analyzer.save_results(results)
        
        # 概要を表示
        analyzer.print_summary(results)
        
        print(f"\n🎉 分析完了!")
        print(f"結果ファイル:")
        for file_type, file_path in saved_files.items():
            print(f"  {file_type}: {file_path}")
        
    except KeyboardInterrupt:
        print("\n⏹️  分析が中断されました")
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()