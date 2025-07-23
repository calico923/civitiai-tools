#!/usr/bin/env python3
"""
CivitAI Downloader v2 - 基本使用例

このファイルはCivitAI Downloader v2の基本的な使用方法を示すサンプルです。
実際のCLIコマンドの使い方を学ぶことができます。
"""

import subprocess
import json
from pathlib import Path

def run_command(cmd):
    """コマンドを実行し、結果を表示する"""
    print(f"\n🔄 実行中: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 成功")
            if result.stdout:
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        else:
            print("❌ エラー")
            if result.stderr:
                print(result.stderr)
    except Exception as e:
        print(f"❌ 例外発生: {e}")

def basic_search_examples():
    """基本的な検索例"""
    print("=" * 60)
    print("📋 基本的な検索例")
    print("=" * 60)
    
    # 基本検索
    run_command('python -m src.cli.main search "anime" --limit 3 --format simple')
    
    # フィルタリング検索
    run_command('python -m src.cli.main search "character" --types LORA --category character --limit 3 --format simple')
    
    # 日付フィルタ
    run_command('python -m src.cli.main search "style" --published-within 30days --limit 3 --format simple')
    
    # 高度ソート
    run_command('python -m src.cli.main search "realistic" --sort-by download_count --sort-direction desc --limit 3 --format simple')

def advanced_search_examples():
    """高度な検索例"""
    print("=" * 60)
    print("🔍 高度な検索例")
    print("=" * 60)
    
    # 複数条件の組み合わせ
    run_command('python -m src.cli.main search "cyberpunk" --category style,concept --types LORA --nsfw-level sfw --min-likes 100 --limit 3 --format simple')
    
    # JSON出力
    output_file = "search_results.json"
    run_command(f'python -m src.cli.main search "landscape" --category background --format json --output {output_file} --limit 3')
    
    # 結果ファイルの確認
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            data = json.load(f)
            print(f"📄 {output_file} に {len(data)} 件の結果を保存しました")

def utility_commands():
    """ユーティリティコマンド例"""
    print("=" * 60)
    print("🛠️ ユーティリティコマンド例")
    print("=" * 60)
    
    # バージョン確認
    run_command('python -m src.cli.main version')
    
    # モデル情報表示
    run_command('python -m src.cli.main info 4201')
    
    # バージョン管理
    run_command('python -m src.cli.main model-versions 4201 --output simple')

def filtering_examples():
    """フィルタリング機能の例"""
    print("=" * 60)
    print("🎯 フィルタリング機能例")
    print("=" * 60)
    
    # NSFWレベル制御
    run_command('python -m src.cli.main search "anime" --nsfw-level sfw --limit 3 --format simple')
    
    # 評価フィルタ
    run_command('python -m src.cli.main search "character" --min-like-ratio 0.9 --limit 3 --format simple')
    
    # 複数カテゴリ
    run_command('python -m src.cli.main search "art" --category style,concept --limit 3 --format simple')

def main():
    """メイン実行関数"""
    print("🚀 CivitAI Downloader v2 - 基本使用例")
    print("=" * 60)
    print("このスクリプトは様々なCLIコマンドの使用例を実行します。")
    print("ネットワーク接続が必要です。")
    print("=" * 60)
    
    try:
        # 各種例を実行
        basic_search_examples()
        advanced_search_examples()
        filtering_examples()
        utility_commands()
        
        print("\n" + "=" * 60)
        print("✅ 全ての例の実行が完了しました！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⏹️ 実行が中断されました。")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")

if __name__ == "__main__":
    main()