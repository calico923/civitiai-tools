#!/usr/bin/env python3
"""
Illustrious Type別独立調査スクリプト

Type別（Checkpoint、LORA、LyCORIS）に独立して調査を実行し、
Enhanced形式（CSV、HTML、JSON）で出力する。

Usage:
    python illustrious_type_search.py --type checkpoint --tag style --sort "Highest Rated"
    python illustrious_type_search.py --type lora --tag notag --sort "Most Downloaded"
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.client import CivitaiClient
from src.core.enhanced_url_collector import EnhancedURLCollector


class IllustriousTypeSearcher:
    """Illustrious Type別独立調査クラス"""
    
    def __init__(self, api_key: str):
        self.client = CivitaiClient(api_key)
        
        # 出力ディレクトリ
        self.output_dir = Path("outputs/enhanced")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.enhanced_collector = EnhancedURLCollector(api_key=api_key, output_dir=self.output_dir)
        
        # 検索パラメータ
        self.base_model = "Illustrious"
        self.valid_types = ["Checkpoint", "LORA", "LoCon"]
        self.valid_tags = ["style", "concept", "pose", "nsfw", "sexy", "hentai", "anime", "notag"]
        self.valid_sorts = ["Highest Rated", "Most Downloaded", "Most Liked"]
    
    def search_models(self, model_type: str, tag: str, sort_order: str, limit: int = 500) -> list:
        """
        指定条件でモデルを検索
        
        Args:
            model_type: モデルタイプ (Checkpoint, LORA, LyCORIS)
            tag: タグ ("notag"の場合はタグ指定なし)
            sort_order: ソート順
            limit: 検索上限
            
        Returns:
            モデルデータのリスト
        """
        print(f"🔍 検索開始: {self.base_model} + {model_type} + {tag} + {sort_order}")
        
        try:
            # タグの処理
            search_tag = None if tag == "notag" else tag
            
            # API検索実行
            models = self.client.search_models_with_cursor(
                types=[model_type],
                tag=search_tag,
                base_models=[self.base_model],
                sort=sort_order,
                limit=100,  # API制限
                max_pages=min(5, limit // 100 + 1)  # 最大5ページまたは指定limit分
            )
            
            # 上限を適用
            models = models[:limit]
            
            print(f"✅ {len(models)}個のモデルを取得")
            return models
            
        except Exception as e:
            print(f"❌ 検索エラー: {e}")
            return []
    
    def generate_filename(self, model_type: str, tag: str, sort_order: str) -> str:
        """
        ファイル名を生成
        
        Args:
            model_type: モデルタイプ
            tag: タグ
            sort_order: ソート順
            
        Returns:
            ファイル名（拡張子なし）
        """
        # ソート順を安全なファイル名に変換
        safe_sort = sort_order.lower().replace(" ", "_")
        
        # モデルタイプを小文字に変換
        safe_type = model_type.lower()
        
        return f"illustrious_{safe_type}_{safe_sort}_{tag}"
    
    def run_search(self, model_type: str, tag: str, sort_order: str, limit: int = 500) -> dict:
        """
        検索を実行してEnhanced形式で出力
        
        Args:
            model_type: モデルタイプ
            tag: タグ
            sort_order: ソート順
            limit: 検索上限
            
        Returns:
            実行結果の辞書
        """
        # パラメータ検証
        if model_type not in self.valid_types:
            raise ValueError(f"無効なモデルタイプ: {model_type}. 有効な値: {self.valid_types}")
        
        if tag not in self.valid_tags:
            raise ValueError(f"無効なタグ: {tag}. 有効な値: {self.valid_tags}")
        
        if sort_order not in self.valid_sorts:
            raise ValueError(f"無効なソート順: {sort_order}. 有効な値: {self.valid_sorts}")
        
        # 検索実行
        start_time = datetime.now()
        models_data = self.search_models(model_type, tag, sort_order, limit)
        search_time = (datetime.now() - start_time).total_seconds()
        
        if not models_data:
            print("⚠️ 検索結果が空でした")
            return {
                "status": "empty",
                "message": "検索結果が空でした",
                "search_time": search_time
            }
        
        # Enhanced情報収集
        print(f"📊 Enhanced情報を収集中...")
        try:
            model_infos = self.enhanced_collector.collect_enhanced_model_info(models_data)
            
            if not model_infos:
                print("⚠️ Enhanced情報の収集に失敗しました")
                return {
                    "status": "failed",
                    "message": "Enhanced情報の収集に失敗",
                    "search_time": search_time
                }
            
            # ファイル名生成
            filename = self.generate_filename(model_type, tag, sort_order)
            
            # Enhanced形式で出力
            print(f"💾 Enhanced出力を生成中...")
            exported_files = self.enhanced_collector.export_all_formats(
                model_infos,
                filename
            )
            
            print(f"✅ 出力完了:")
            print(f"  📊 CSV: {exported_files.get('csv', 'N/A')}")
            print(f"  🌐 HTML: {exported_files.get('html', 'N/A')}")
            print(f"  📋 JSON: {exported_files.get('json', 'N/A')}")
            
            return {
                "status": "success",
                "model_count": len(model_infos),
                "search_time": search_time,
                "exported_files": exported_files,
                "filename": filename
            }
            
        except Exception as e:
            print(f"❌ Enhanced出力エラー: {e}")
            return {
                "status": "error",
                "message": str(e),
                "search_time": search_time
            }
    
    def run_all_combinations(self, model_type: str = None, limit: int = 500) -> dict:
        """
        指定モデルタイプの全組み合わせを実行
        
        Args:
            model_type: モデルタイプ (Noneの場合は全タイプ)
            limit: 各検索の上限
            
        Returns:
            実行結果のサマリー
        """
        types_to_run = [model_type] if model_type else self.valid_types
        results = []
        
        total_combinations = len(types_to_run) * len(self.valid_tags) * len(self.valid_sorts)
        current_combination = 0
        
        print(f"🚀 Illustrious Type別独立調査開始")
        print(f"📊 実行組み合わせ数: {total_combinations}")
        print(f"🎯 各検索の上限: {limit}モデル")
        print()
        
        for model_type in types_to_run:
            for tag in self.valid_tags:
                for sort_order in self.valid_sorts:
                    current_combination += 1
                    
                    print(f"📈 進行状況: {current_combination}/{total_combinations} ({current_combination/total_combinations*100:.1f}%)")
                    
                    try:
                        result = self.run_search(model_type, tag, sort_order, limit)
                        result.update({
                            "model_type": model_type,
                            "tag": tag,
                            "sort_order": sort_order,
                            "combination": current_combination
                        })
                        results.append(result)
                        
                    except Exception as e:
                        print(f"❌ 組み合わせ実行エラー: {e}")
                        results.append({
                            "status": "error",
                            "model_type": model_type,
                            "tag": tag,
                            "sort_order": sort_order,
                            "combination": current_combination,
                            "message": str(e)
                        })
                    
                    print()  # 区切り
        
        # サマリー生成
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") in ["error", "failed"]]
        empty = [r for r in results if r.get("status") == "empty"]
        
        print(f"🎉 全組み合わせ実行完了!")
        print(f"✅ 成功: {len(successful)}")
        print(f"❌ 失敗: {len(failed)}")
        print(f"⚠️ 空結果: {len(empty)}")
        print(f"📊 総モデル数: {sum(r.get('model_count', 0) for r in successful)}")
        
        return {
            "total_combinations": total_combinations,
            "successful": len(successful),
            "failed": len(failed),
            "empty": len(empty),
            "total_models": sum(r.get('model_count', 0) for r in successful),
            "results": results
        }


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Illustrious Type別独立調査実行"
    )
    
    parser.add_argument(
        "--type",
        choices=["checkpoint", "lora", "locon", "all"],
        default="all",
        help="検索対象のモデルタイプ (default: all)"
    )
    parser.add_argument(
        "--tag",
        choices=["style", "concept", "pose", "nsfw", "sexy", "hentai", "anime", "notag", "all"],
        help="検索対象のタグ (指定時は単一実行、未指定時は全タグ実行)"
    )
    parser.add_argument(
        "--sort",
        choices=["Highest Rated", "Most Downloaded", "Most Liked", "all"],
        help="ソート順 (指定時は単一実行、未指定時は全ソート実行)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="各検索の上限 (default: 500)"
    )
    
    args = parser.parse_args()
    
    # APIキー取得
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("❌ エラー: CIVITAI_API_KEY環境変数を設定してください")
        sys.exit(1)
    
    # 検索実行
    searcher = IllustriousTypeSearcher(api_key)
    
    try:
        # 型名の正規化
        def normalize_type(type_str):
            if type_str.lower() == "checkpoint":
                return "Checkpoint"
            elif type_str.lower() == "lora":
                return "LORA"
            elif type_str.lower() in ["lycoris", "locon"]:
                return "LoCon"
            else:
                return type_str.title()
        
        if args.tag and args.sort and args.type != "all":
            # 単一組み合わせ実行
            model_type = normalize_type(args.type)
            result = searcher.run_search(model_type, args.tag, args.sort, args.limit)
            print(f"実行結果: {result}")
        else:
            # 全組み合わせ実行
            model_type = None if args.type == "all" else normalize_type(args.type)
            summary = searcher.run_all_combinations(model_type, args.limit)
            print(f"実行サマリー: 成功{summary['successful']}/失敗{summary['failed']}/空{summary['empty']}")
            
    except KeyboardInterrupt:
        print("\n⚠️ 検索が中断されました")
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()