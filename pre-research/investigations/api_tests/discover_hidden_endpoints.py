#!/usr/bin/env python3
"""
CivitAI APIの隠れたエンドポイントと機能を発見
"""

import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

class CivitAIEndpointDiscovery:
    def __init__(self):
        self.api_key = os.getenv('CIVITAI_API_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else None
        }
        self.base_url = 'https://civitai.com/api/v1'
    
    def test_endpoint(self, endpoint: str, params: dict = None) -> dict:
        """エンドポイントをテスト"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "content_type": response.headers.get('content-type', ''),
                "data": response.json() if response.status_code == 200 and 'json' in response.headers.get('content-type', '') else None,
                "error": None
            }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "error": str(e)
            }
    
    def discover_endpoints(self) -> dict:
        """様々なエンドポイントを発見"""
        print("🔍 隠れたエンドポイントを発見中...")
        
        # 試行するエンドポイント
        endpoints_to_test = [
            # 基本エンドポイント
            ("models", {}),
            ("models/categories", {}),
            ("models/tags", {}),
            
            # ユーザー関連
            ("users", {}),
            ("users/me", {}),
            ("creators", {}),
            
            # 画像関連
            ("images", {}),
            ("images/featured", {}),
            ("images/recent", {}),
            
            # 統計・ランキング
            ("stats", {}),
            ("leaderboard", {}),
            ("trending", {}),
            ("featured", {}),
            
            # コレクション
            ("collections", {}),
            ("favorites", {}),
            
            # コメント・レビュー
            ("comments", {}),
            ("reviews", {}),
            ("ratings", {}),
            
            # 検索・フィルタ
            ("search", {}),
            ("filters", {}),
            ("categories", {}),
            
            # 通知・活動
            ("notifications", {}),
            ("activities", {}),
            ("feed", {}),
            
            # 管理者・モデレーション
            ("moderation", {}),
            ("reports", {}),
            
            # システム情報
            ("health", {}),
            ("version", {}),
            ("status", {}),
            
            # モデル特定情報（既知のIDで）
            ("models/140272/reviews", {}),
            ("models/140272/comments", {}),
            ("models/140272/images", {}),
            ("models/140272/versions", {}),
            ("models/140272/download", {}),
            
            # タグ関連詳細
            ("tags", {}),
            ("tags/popular", {}),
            ("tags/recent", {}),
            
            # 生成関連
            ("generations", {}),
            ("generate", {}),
            
            # API情報
            ("api", {}),
            ("docs", {}),
            ("schema", {}),
        ]
        
        results = {}
        
        for endpoint, params in endpoints_to_test:
            print(f"  Testing: /{endpoint}")
            result = self.test_endpoint(endpoint, params)
            results[endpoint] = result
            
            if result["success"] and result["data"]:
                # 成功した場合、構造を簡単に分析
                data = result["data"]
                result["structure_info"] = {
                    "type": type(data).__name__,
                    "keys": list(data.keys()) if isinstance(data, dict) else None,
                    "length": len(data) if isinstance(data, (list, dict)) else None
                }
            
            time.sleep(0.5)  # レート制限対策
        
        return results
    
    def analyze_pagination(self) -> dict:
        """ページネーション機能の分析"""
        print("📄 ページネーション機能を分析中...")
        
        pagination_tests = [
            # オフセットベース
            {"limit": 5, "page": 1},
            {"limit": 5, "page": 2},
            {"limit": 5, "offset": 0},
            {"limit": 5, "offset": 5},
            
            # カーソルベース
            {"limit": 5, "cursor": ""},
            {"limit": 5, "nextCursor": ""},
            
            # その他
            {"limit": 5, "sort": "Newest"},
            {"limit": 100},  # 最大リミットテスト
            {"limit": 1000}, # 過度なリミットテスト
        ]
        
        results = {}
        
        for i, params in enumerate(pagination_tests):
            print(f"  Testing pagination {i+1}: {params}")
            result = self.test_endpoint("models", params)
            
            if result["success"] and result["data"]:
                data = result["data"]
                results[f"test_{i+1}"] = {
                    "params": params,
                    "items_returned": len(data.get("items", [])),
                    "has_metadata": "metadata" in data,
                    "metadata_keys": list(data.get("metadata", {}).keys()),
                    "pagination_info": {
                        "nextCursor": data.get("metadata", {}).get("nextCursor"),
                        "prevCursor": data.get("metadata", {}).get("prevCursor"),
                        "currentPage": data.get("metadata", {}).get("currentPage"),
                        "pageSize": data.get("metadata", {}).get("pageSize"),
                        "totalItems": data.get("metadata", {}).get("totalItems"),
                        "totalPages": data.get("metadata", {}).get("totalPages"),
                    }
                }
            else:
                results[f"test_{i+1}"] = {
                    "params": params,
                    "failed": True,
                    "error": result.get("error")
                }
            
            time.sleep(1)
        
        return results
    
    def discover_advanced_search(self) -> dict:
        """高度な検索機能を発見"""
        print("🔎 高度な検索機能を発見中...")
        
        advanced_params = [
            # 複数値パラメータ
            {"types": "Checkpoint,LORA"},
            {"tags": "anime,style"},
            {"baseModels": "Illustrious,SDXL 1.0"},
            
            # 範囲検索
            {"minDownloads": 1000},
            {"maxDownloads": 10000},
            {"minRating": 4.0},
            {"maxRating": 5.0},
            
            # 日付範囲
            {"startDate": "2024-01-01"},
            {"endDate": "2024-12-31"},
            {"createdAfter": "2024-06-01"},
            {"createdBefore": "2024-12-31"},
            
            # 高度なフィルタ
            {"featured": "true"},
            {"verified": "true"},
            {"commercial": "true"},
            {"derivatives": "true"},
            {"mature": "false"},
            
            # ソート組み合わせ
            {"sort": "Most Downloaded", "period": "Month"},
            {"sort": "Newest", "direction": "desc"},
            
            # 検索クエリ
            {"query": "anime style", "tags": "anime"},
            {"q": "realistic portrait"},
            
            # フィールド指定
            {"include": "stats,creator,tags"},
            {"exclude": "description,images"},
            {"fields": "id,name,type,stats"}
        ]
        
        results = {}
        
        for i, params in enumerate(advanced_params):
            params["limit"] = 3  # 小さなリミットでテスト
            print(f"  Testing advanced search {i+1}: {list(params.keys())}")
            
            result = self.test_endpoint("models", params)
            results[f"advanced_{i+1}"] = {
                "params": params,
                "success": result["success"],
                "items_count": len(result.get("data", {}).get("items", [])) if result["success"] else 0,
                "error": result.get("error")
            }
            
            time.sleep(0.5)
        
        return results

def main():
    discovery = CivitAIEndpointDiscovery()
    
    print("🚀 CivitAI API 隠れた機能の発見を開始...")
    print("=" * 60)
    
    investigations = {
        "endpoint_discovery": discovery.discover_endpoints(),
        "pagination_analysis": discovery.analyze_pagination(),
        "advanced_search": discovery.discover_advanced_search()
    }
    
    # 結果を保存
    with open('civitai_api_hidden_features.json', 'w', encoding='utf-8') as f:
        json.dump(investigations, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("📊 発見結果サマリー:")
    
    # 成功したエンドポイント
    successful_endpoints = [
        endpoint for endpoint, result in investigations["endpoint_discovery"].items()
        if result["success"]
    ]
    
    print(f"✅ 利用可能エンドポイント: {len(successful_endpoints)}個")
    if successful_endpoints:
        print(f"   成功: {', '.join(successful_endpoints[:10])}{'...' if len(successful_endpoints) > 10 else ''}")
    
    # 失敗したエンドポイント
    failed_endpoints = [
        endpoint for endpoint, result in investigations["endpoint_discovery"].items()
        if not result["success"]
    ]
    
    print(f"❌ 利用不可エンドポイント: {len(failed_endpoints)}個")
    
    # ページネーション結果
    pagination_working = sum(1 for test in investigations["pagination_analysis"].values() 
                           if not test.get("failed", False))
    print(f"📄 ページネーション方式: {pagination_working}個の方式が動作")
    
    # 高度検索結果
    advanced_working = sum(1 for test in investigations["advanced_search"].values() 
                         if test["success"])
    print(f"🔎 高度検索パラメータ: {advanced_working}個が動作")
    
    print(f"\n詳細結果: civitai_api_hidden_features.json")

if __name__ == "__main__":
    main()