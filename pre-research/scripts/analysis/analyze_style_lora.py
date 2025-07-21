#!/usr/bin/env python3
"""styleタグLoRAの詳細分析とベースモデル別カウント"""

import json
from pathlib import Path
from src.utils.context_manager import ContextManager


def analyze_existing_results():
    """既存の結果ファイルを分析"""
    
    # 既存のJSONファイルを探す
    output_dir = Path("outputs/urls")
    style_files = list(output_dir.glob("style_lora_*.json"))
    
    if not style_files:
        print("styleタグLoRAの結果ファイルが見つかりません")
        return
    
    # 最新のファイルを使用
    latest_file = max(style_files, key=lambda p: p.stat().st_mtime)
    print(f"分析対象ファイル: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    models = data.get('models', [])
    print(f"\n総styleタグLoRA数: {len(models)}")
    
    # ContextManagerでサマリー作成
    cm = ContextManager()
    summary = cm.create_summary(models, ['illustrious', 'pony', 'noobai'])
    
    print("\n=== ベースモデル別styleタグLoRA数 ===")
    for base_model, count in summary['by_base_model'].items():
        print(f"{base_model:12}: {count:3d}個")
    
    print(f"\n=== モデルタイプ別 ===")
    for model_type, count in summary['by_type'].items():
        print(f"{model_type:15}: {count:3d}個")
    
    print(f"\n=== トップ作成者（上位5位） ===")
    for i, (creator, count) in enumerate(list(summary['top_creators'].items())[:5], 1):
        print(f"{i}. {creator:20}: {count:2d}個")
    
    # サンプルモデル表示
    print(f"\n=== サンプルモデル（上位5個） ===")
    for i, model in enumerate(summary['sample_models'], 1):
        tags = ', '.join(model.get('tags', [])[:3])
        print(f"{i}. {model.get('model_name', 'Unknown')}")
        print(f"   タグ: {tags}")
        creator = model.get('creator', 'Unknown')
        if isinstance(creator, dict):
            creator = creator.get('username', 'Unknown')
        print(f"   作成者: {creator}")
        print()
    
    # 詳細分析結果を保存
    summary_file = output_dir / "style_lora_analysis_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"詳細分析結果を保存: {summary_file}")
    
    return summary


def main():
    print("=== styleタグLoRA分析ツール ===\n")
    
    try:
        summary = analyze_existing_results()
        
        if summary:
            print(f"\n=== 結論 ===")
            print(f"styleタグを持つLoRAモデルは合計 {summary['total_count']} 個存在します")
            print(f"各ベースモデル対応数:")
            for base_model, count in summary['by_base_model'].items():
                print(f"  {base_model}: {count}個")
            
            # 0個の場合の追加調査提案
            zero_count_models = [model for model, count in summary['by_base_model'].items() if count == 0]
            if zero_count_models:
                print(f"\n注意: {', '.join(zero_count_models)}は0個です")
                print("追加調査が必要な可能性があります（タグ名の表記揺れなど）")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()