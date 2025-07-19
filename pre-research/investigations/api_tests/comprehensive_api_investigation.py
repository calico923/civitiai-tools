#!/usr/bin/env python3
"""
CivitAI APIの包括的調査 - 異なるモデルタイプと検索エンドポイントの詳細分析
"""

import os
import requests
import json
import time
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv()

class CivitAIAPIInvestigator:
    def __init__(self):
        self.api_key = os.getenv('CIVITAI_API_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else None
        }
        self.base_url = 'https://civitai.com/api/v1'
    
    def request(self, endpoint: str, params: Dict = None) -> Dict:
        """API リクエストを実行"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return {}
    
    def investigate_search_endpoints(self) -> Dict:
        """検索エンドポイントの調査"""
        print("🔍 検索エンドポイントの調査...")
        
        # 基本的な検索パラメータ
        search_params = {
            'limit': 3,
            'types': 'Checkpoint',
            'tags': 'anime'
        }
        
        search_response = self.request('models', search_params)
        
        investigation = {
            "search_response_structure": self._analyze_response_structure(search_response),
            "available_parameters": {}
        }
        
        # パラメータテストを実行
        parameter_tests = [
            ('limit', [1, 10, 100]),
            ('types', ['Checkpoint', 'LORA', 'LoCon']),
            ('sort', ['Highest Rated', 'Most Downloaded', 'Most Liked', 'Newest']),
            ('period', ['AllTime', 'Year', 'Month', 'Week', 'Day']),
            ('nsfw', ['true', 'false']),
            ('baseModels', ['Illustrious', 'SDXL 1.0', 'Pony']),
            ('tags', ['anime', 'style', 'realistic']),
            ('username', ['Ikena']),
            ('query', ['anime model'])
        ]
        
        for param_name, test_values in parameter_tests:
            print(f"  Testing parameter: {param_name}")
            investigation["available_parameters"][param_name] = {
                "tested_values": test_values,
                "results": {}
            }
            
            for value in test_values:
                test_params = {'limit': 2}
                test_params[param_name] = value
                
                result = self.request('models', test_params)
                investigation["available_parameters"][param_name]["results"][str(value)] = {
                    "success": 'items' in result,
                    "count": len(result.get('items', [])),
                    "has_metadata": 'metadata' in result
                }
                time.sleep(1)  # レート制限対策
        
        return investigation
    
    def investigate_individual_model_apis(self) -> Dict:
        """個別モデルAPIの調査"""
        print("📋 個別モデルAPIの調査...")
        
        # 異なるタイプのモデルを調査
        test_models = [
            {'id': 140272, 'type': 'Checkpoint', 'name': 'Hassaku XL'},
            {'id': 25494, 'type': 'LORA', 'name': 'Style LoRA'},
            {'id': 82098, 'type': 'LyCORIS', 'name': 'LyCORIS Model'}
        ]
        
        investigation = {
            "model_details": {},
            "common_fields": set(),
            "type_specific_fields": {}
        }
        
        all_fields = []
        
        for model_info in test_models:
            model_id = model_info['id']
            model_type = model_info['type']
            
            print(f"  調査中: {model_info['name']} ({model_type})")
            
            # 個別モデル詳細
            model_data = self.request(f'models/{model_id}')
            
            if model_data:
                fields = self._extract_all_field_paths(model_data)
                all_fields.extend(fields)
                
                investigation["model_details"][model_id] = {
                    "type": model_type,
                    "name": model_info['name'],
                    "field_count": len(fields),
                    "unique_fields": fields
                }
                
                investigation["type_specific_fields"][model_type] = fields
            
            time.sleep(2)  # レート制限対策
        
        # 共通フィールドを特定
        if len(investigation["type_specific_fields"]) > 1:
            field_sets = [set(fields) for fields in investigation["type_specific_fields"].values()]
            investigation["common_fields"] = list(field_sets[0].intersection(*field_sets[1:]))
        
        return investigation
    
    def investigate_image_metadata(self) -> Dict:
        """画像メタデータの調査"""
        print("🖼️ 画像メタデータの調査...")
        
        # 画像付きモデルを取得
        models_with_images = self.request('models', {'limit': 3, 'types': 'Checkpoint'})
        
        investigation = {
            "image_fields": set(),
            "meta_examples": [],
            "generation_info": {}
        }
        
        if 'items' in models_with_images:
            for model in models_with_images['items'][:2]:
                if 'modelVersions' in model and model['modelVersions']:
                    version = model['modelVersions'][0]
                    if 'images' in version and version['images']:
                        for image in version['images'][:2]:
                            # 画像フィールドを収集
                            image_fields = self._extract_all_field_paths(image, prefix='image')
                            investigation["image_fields"].update(image_fields)
                            
                            # メタデータの例を保存
                            if 'meta' in image:
                                investigation["meta_examples"].append({
                                    "model_id": model['id'],
                                    "image_meta": image['meta']
                                })
        
        investigation["image_fields"] = list(investigation["image_fields"])
        return investigation
    
    def investigate_version_and_files(self) -> Dict:
        """バージョンとファイル情報の調査"""
        print("📁 バージョン・ファイル情報の調査...")
        
        # 複数バージョンを持つモデルを調査
        model_data = self.request('models/140272')  # Hassaku XL
        
        investigation = {
            "version_fields": set(),
            "file_fields": set(),
            "hash_types": set(),
            "metadata_fields": set()
        }
        
        if 'modelVersions' in model_data:
            for version in model_data['modelVersions'][:3]:  # 最初の3バージョンを調査
                # バージョンフィールド
                version_fields = self._extract_all_field_paths(version, prefix='version')
                investigation["version_fields"].update(version_fields)
                
                # ファイル情報
                if 'files' in version:
                    for file_info in version['files']:
                        file_fields = self._extract_all_field_paths(file_info, prefix='file')
                        investigation["file_fields"].update(file_fields)
                        
                        # ハッシュタイプ
                        if 'hashes' in file_info:
                            investigation["hash_types"].update(file_info['hashes'].keys())
                        
                        # メタデータフィールド
                        if 'metadata' in file_info:
                            metadata_fields = self._extract_all_field_paths(file_info['metadata'], prefix='metadata')
                            investigation["metadata_fields"].update(metadata_fields)
        
        # setをlistに変換
        for key in investigation:
            if isinstance(investigation[key], set):
                investigation[key] = list(investigation[key])
        
        return investigation
    
    def investigate_creator_info(self) -> Dict:
        """作成者情報の調査"""
        print("👤 作成者情報の調査...")
        
        # 人気作成者のプロフィール取得を試行
        creators_to_test = ['Ikena', 'Desync', 'advokat']
        
        investigation = {
            "creator_endpoints": {},
            "creator_fields": set()
        }
        
        for creator in creators_to_test:
            # 作成者のモデル一覧
            creator_models = self.request('models', {'username': creator, 'limit': 3})
            
            if 'items' in creator_models and creator_models['items']:
                first_model = creator_models['items'][0]
                if 'creator' in first_model:
                    creator_fields = self._extract_all_field_paths(first_model['creator'], prefix='creator')
                    investigation["creator_fields"].update(creator_fields)
                
                investigation["creator_endpoints"][creator] = {
                    "model_count": len(creator_models.get('items', [])),
                    "has_creator_info": 'creator' in first_model if first_model else False
                }
            
            time.sleep(1)
        
        investigation["creator_fields"] = list(investigation["creator_fields"])
        return investigation
    
    def _analyze_response_structure(self, response: Dict) -> Dict:
        """レスポンス構造を分析"""
        return {
            "top_level_keys": list(response.keys()) if response else [],
            "has_items": 'items' in response,
            "has_metadata": 'metadata' in response,
            "items_count": len(response.get('items', [])),
            "metadata_keys": list(response.get('metadata', {}).keys()) if 'metadata' in response else []
        }
    
    def _extract_all_field_paths(self, obj: Any, prefix: str = "") -> List[str]:
        """オブジェクトからすべてのフィールドパスを抽出"""
        paths = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{prefix}.{key}" if prefix else key
                paths.append(current_path)
                
                if isinstance(value, (dict, list)) and key not in ['description']:  # 説明文は除外
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        paths.extend(self._extract_all_field_paths(value[0], f"{current_path}[0]"))
                    elif isinstance(value, dict):
                        paths.extend(self._extract_all_field_paths(value, current_path))
        
        return paths

def main():
    investigator = CivitAIAPIInvestigator()
    
    print("🔬 CivitAI API 包括的調査を開始...")
    print("=" * 60)
    
    # 各種調査を実行
    investigations = {
        "search_endpoints": investigator.investigate_search_endpoints(),
        "individual_models": investigator.investigate_individual_model_apis(),
        "image_metadata": investigator.investigate_image_metadata(),
        "version_files": investigator.investigate_version_and_files(),
        "creator_info": investigator.investigate_creator_info()
    }
    
    # 結果を保存
    with open('civitai_api_comprehensive_investigation.json', 'w', encoding='utf-8') as f:
        json.dump(investigations, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("📊 調査完了! 結果サマリー:")
    
    # サマリー出力
    search_params = investigations["search_endpoints"]["available_parameters"]
    working_params = [p for p, data in search_params.items() 
                     if any(r["success"] for r in data["results"].values())]
    
    print(f"✅ 動作する検索パラメータ: {len(working_params)}個")
    print(f"   {', '.join(working_params)}")
    
    if investigations["individual_models"]["common_fields"]:
        print(f"✅ 全モデルタイプ共通フィールド: {len(investigations['individual_models']['common_fields'])}個")
    
    hash_types = investigations["version_files"]["hash_types"]
    print(f"✅ 利用可能ハッシュタイプ: {', '.join(hash_types)}")
    
    print(f"\n詳細結果: civitai_api_comprehensive_investigation.json")

if __name__ == "__main__":
    main()