#!/usr/bin/env python3
"""
CivitAI API応答の完全なスキーマを分析し、すべての取得可能フィールドを文書化
"""

import json
import os
from typing import Any, Dict, List, Set

def analyze_structure(obj: Any, path: str = "", depth: int = 0, visited: Set[str] = None) -> Dict[str, Any]:
    """オブジェクトの構造を再帰的に分析"""
    if visited is None:
        visited = set()
    
    result = {
        "type": type(obj).__name__,
        "path": path
    }
    
    if isinstance(obj, dict):
        result["fields"] = {}
        for key, value in obj.items():
            if depth < 5:  # 深さ制限
                field_path = f"{path}.{key}" if path else key
                if field_path not in visited:
                    visited.add(field_path)
                    result["fields"][key] = analyze_structure(value, field_path, depth + 1, visited)
                else:
                    result["fields"][key] = {"type": type(value).__name__, "note": "circular reference"}
    
    elif isinstance(obj, list) and obj:
        result["length"] = len(obj)
        result["item_example"] = analyze_structure(obj[0], f"{path}[0]", depth + 1, visited)
    
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        result["value_example"] = obj if depth < 3 else "..."
    
    return result

def extract_all_fields(obj: Any, prefix: str = "") -> List[Dict[str, Any]]:
    """すべてのフィールドとその型、サンプル値を抽出"""
    fields = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_path = f"{prefix}.{key}" if prefix else key
            field_info = {
                "path": field_path,
                "type": type(value).__name__,
                "sample": None
            }
            
            if isinstance(value, (str, int, float, bool)) or value is None:
                field_info["sample"] = value
            elif isinstance(value, list):
                field_info["length"] = len(value)
                if value and isinstance(value[0], (str, int, float, bool)):
                    field_info["sample"] = value[0]
            
            fields.append(field_info)
            
            # 再帰的に処理
            if isinstance(value, dict):
                fields.extend(extract_all_fields(value, field_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                fields.extend(extract_all_fields(value[0], f"{field_path}[0]"))
    
    return fields

def categorize_fields(fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """フィールドをカテゴリ別に分類"""
    categories = {
        "基本情報": [],
        "ライセンス・権限": [],
        "統計情報": [],
        "バージョン情報": [],
        "メタデータ": [],
        "技術情報": [],
        "コンテンツ": [],
        "その他": []
    }
    
    for field in fields:
        path = field["path"]
        
        # カテゴリ分類
        if any(x in path.lower() for x in ["name", "id", "description", "type", "creator"]):
            categories["基本情報"].append(field)
        elif any(x in path.lower() for x in ["allow", "license", "permission", "commercial"]):
            categories["ライセンス・権限"].append(field)
        elif any(x in path.lower() for x in ["stat", "count", "rating", "favorite", "download"]):
            categories["統計情報"].append(field)
        elif "modelVersions" in path:
            categories["バージョン情報"].append(field)
        elif any(x in path.lower() for x in ["tag", "meta", "poi", "nsfw", "minor"]):
            categories["メタデータ"].append(field)
        elif any(x in path.lower() for x in ["base", "train", "epoch", "step", "size", "hash"]):
            categories["技術情報"].append(field)
        elif any(x in path.lower() for x in ["image", "file", "download"]):
            categories["コンテンツ"].append(field)
        else:
            categories["その他"].append(field)
    
    return categories

def generate_documentation(data: Dict[str, Any]) -> str:
    """API仕様ドキュメントを生成"""
    doc = "# CivitAI API v1 完全仕様書\n\n"
    doc += "## 概要\n"
    doc += "CivitAI APIから取得可能なすべてのフィールドとその詳細\n\n"
    
    # 構造分析
    structure = analyze_structure(data)
    
    # フィールド抽出
    all_fields = extract_all_fields(data)
    categorized = categorize_fields(all_fields)
    
    # トップレベルフィールドのサマリー
    doc += "## トップレベルフィールド\n\n"
    if isinstance(data, dict):
        for key, value in data.items():
            doc += f"- **{key}** ({type(value).__name__})\n"
    doc += "\n"
    
    # カテゴリ別フィールド詳細
    for category, fields in categorized.items():
        if fields:
            doc += f"## {category}\n\n"
            doc += "| フィールドパス | 型 | サンプル値/説明 |\n"
            doc += "|--------------|---|-------------|\n"
            
            for field in sorted(fields, key=lambda x: x["path"]):
                path = field["path"]
                field_type = field["type"]
                sample = field.get("sample", "")
                
                # サンプル値の整形
                if isinstance(sample, str) and len(sample) > 50:
                    sample = sample[:47] + "..."
                elif field.get("length"):
                    sample = f"配列 (長さ: {field['length']})"
                elif field_type == "dict":
                    sample = "オブジェクト"
                elif field_type == "list":
                    sample = "配列"
                elif sample is None:
                    sample = "null"
                
                doc += f"| `{path}` | {field_type} | {sample} |\n"
            
            doc += "\n"
    
    # 特別な分析セクション
    doc += "## 特筆すべき発見\n\n"
    
    # ライセンス関連
    doc += "### ライセンス・商用利用\n"
    doc += "- `allowCommercialUse`: 商用利用の詳細な許可レベル\n"
    doc += "  - 'Image': 生成画像の商用利用\n"
    doc += "  - 'Rent': モデルのレンタル\n"
    doc += "  - 'RentCivit': CivitAI上でのレンタル\n"
    doc += "  - 'Sell': モデルの販売\n"
    doc += "- `allowDerivatives`: 派生作品の作成許可\n"
    doc += "- `allowDifferentLicense`: 異なるライセンスでの再配布\n"
    doc += "- `allowNoCredit`: クレジット表記不要での使用\n\n"
    
    # 統計情報
    doc += "### 統計・メトリクス\n"
    doc += "- ダウンロード数、いいね数、コメント数など詳細な統計\n"
    doc += "- 評価（rating）とレビュー数\n"
    doc += "- お気に入り数とチップ数\n\n"
    
    # バージョン管理
    doc += "### バージョン・ファイル管理\n"
    doc += "- 複数バージョンの管理\n"
    doc += "- 各バージョンごとのファイル情報\n"
    doc += "- ハッシュ値による整合性確認\n"
    doc += "- トレーニング設定の詳細\n\n"
    
    return doc

def main():
    # API応答を読み込み
    with open('api_response_sample.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # ドキュメント生成
    documentation = generate_documentation(data)
    
    # ファイルに保存
    with open('docs/civitai_api_full_spec.md', 'w', encoding='utf-8') as f:
        f.write(documentation)
    
    print("API仕様書を生成しました: docs/civitai_api_full_spec.md")
    
    # 簡易サマリーも出力
    print("\n=== API応答の概要 ===")
    print(f"トップレベルフィールド数: {len(data.keys())}")
    
    all_fields = extract_all_fields(data)
    print(f"総フィールド数: {len(all_fields)}")
    
    categorized = categorize_fields(all_fields)
    print("\nカテゴリ別フィールド数:")
    for category, fields in categorized.items():
        if fields:
            print(f"  - {category}: {len(fields)}フィールド")

if __name__ == "__main__":
    main()