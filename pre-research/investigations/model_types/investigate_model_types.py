#!/usr/bin/env python3
"""
CivitAI APIの全モデルタイプを調査
"""

import os
import requests
import json
import time
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

class ModelTypeInvestigator:
    def __init__(self):
        self.api_key = os.getenv('CIVITAI_API_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else None
        }
        self.base_url = 'https://civitai.com/api/v1'
    
    def request(self, endpoint: str, params: dict = None) -> dict:
        """API リクエストを実行"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return {}
    
    def test_known_types(self) -> dict:
        """既知のモデルタイプをテスト"""
        print("🔍 既知のモデルタイプをテスト中...")
        
        # 既知のタイプ（様々なソースから収集）
        known_types = [
            # 基本タイプ
            "Checkpoint", "LORA", "LoCon", "LyCORIS",
            
            # 追加の可能性があるタイプ
            "TextualInversion", "Hypernetwork", "AestheticGradient",
            "ControlNet", "VAE", "Embedding", "Poses", "Wildcards",
            "Workflows", "Other", "DoRA", "IP-Adapter", "Motion",
            
            # 大文字小文字のバリエーション
            "checkpoint", "lora", "locon", "lycoris",
            "textualinversion", "hypernetwork", "aestheticgradient",
            "controlnet", "vae", "embedding", "poses", "wildcards",
            "workflows", "other", "dora", "ip-adapter", "motion",
            
            # 可能性のある新しいタイプ
            "Upscaler", "CLIP", "Model", "Training", "Dataset",
            "Animation", "Video", "Audio", "Style", "Concept"
        ]
        
        results = {}
        
        for model_type in known_types:
            print(f"  Testing type: {model_type}")
            
            response = self.request('models', {
                'types': model_type,
                'limit': 5
            })
            
            if response and 'items' in response:
                items = response['items']
                results[model_type] = {
                    'success': True,
                    'count': len(items),
                    'total_available': response.get('metadata', {}).get('totalItems', 'unknown'),
                    'examples': [item['name'] for item in items[:3]]
                }
                
                if items:
                    print(f"    ✅ Found {len(items)} items (Total: {results[model_type]['total_available']})")
                else:
                    print(f"    ⚠️ Valid type but no results")
            else:
                results[model_type] = {
                    'success': False,
                    'error': 'Invalid type or API error'
                }
                print(f"    ❌ Invalid or no results")
            
            time.sleep(0.5)  # レート制限対策
        
        return results
    
    def discover_types_from_samples(self) -> dict:
        """サンプルデータから実際のタイプを発見"""
        print("\n🔬 実際のモデルから使用されているタイプを収集中...")
        
        # 複数の検索条件でサンプルを取得
        search_conditions = [
            {'sort': 'Newest', 'limit': 100},
            {'sort': 'Most Downloaded', 'limit': 100},
            {'sort': 'Highest Rated', 'limit': 100},
            {'baseModels': 'SDXL 1.0', 'limit': 100},
            {'baseModels': 'SD 1.5', 'limit': 100},
            {'baseModels': 'Pony', 'limit': 100},
            {'tags': 'anime', 'limit': 100},
            {'tags': 'realistic', 'limit': 100}
        ]
        
        all_types = []
        
        for i, condition in enumerate(search_conditions, 1):
            print(f"  Sampling condition {i}: {condition}")
            
            response = self.request('models', condition)
            
            if response and 'items' in response:
                for item in response['items']:
                    if 'type' in item:
                        all_types.append(item['type'])
            
            time.sleep(1)
        
        # タイプの統計
        type_counts = Counter(all_types)
        
        print(f"\n📊 発見したモデルタイプ ({len(type_counts)}種類):")
        for model_type, count in type_counts.most_common():
            print(f"  - {model_type}: {count}回出現")
        
        return {
            'discovered_types': list(type_counts.keys()),
            'type_statistics': dict(type_counts),
            'total_samples': len(all_types)
        }
    
    def test_multiple_types(self) -> dict:
        """複数タイプの同時指定をテスト"""
        print("\n🔗 複数タイプの同時指定をテスト中...")
        
        # 複数タイプの組み合わせをテスト
        multi_type_tests = [
            "Checkpoint,LORA",
            "Checkpoint,LORA,LoCon",
            "LORA,LyCORIS",
            "TextualInversion,Hypernetwork",
            "ControlNet,VAE",
            "Checkpoint|LORA",  # 区切り文字のテスト
            "Checkpoint;LORA",
            "Checkpoint LORA",   # スペース区切り
        ]
        
        results = {}
        
        for types_param in multi_type_tests:
            print(f"  Testing: {types_param}")
            
            response = self.request('models', {
                'types': types_param,
                'limit': 10
            })
            
            if response and 'items' in response:
                items = response['items']
                found_types = [item['type'] for item in items if 'type' in item]
                unique_types = list(set(found_types))
                
                results[types_param] = {
                    'success': True,
                    'count': len(items),
                    'found_types': unique_types,
                    'type_distribution': dict(Counter(found_types))
                }
                
                print(f"    ✅ Found types: {unique_types}")
            else:
                results[types_param] = {
                    'success': False
                }
                print(f"    ❌ Failed")
            
            time.sleep(0.5)
        
        return results
    
    def investigate_base_model_types(self) -> dict:
        """ベースモデルタイプの調査"""
        print("\n🏗️ ベースモデルタイプを調査中...")
        
        # いくつかのモデルの詳細を取得してbaseModelTypeを確認
        sample_model_ids = [140272, 24149, 24350, 25494, 82098]
        
        base_model_types = []
        
        for model_id in sample_model_ids:
            print(f"  Checking model {model_id}...")
            
            response = self.request(f'models/{model_id}')
            
            if response and 'modelVersions' in response:
                for version in response['modelVersions']:
                    if 'baseModelType' in version:
                        base_model_types.append(version['baseModelType'])
            
            time.sleep(1)
        
        base_type_counts = Counter(base_model_types)
        
        print(f"📊 発見したベースモデルタイプ:")
        for base_type, count in base_type_counts.most_common():
            print(f"  - {base_type}: {count}回出現")
        
        return {
            'base_model_types': list(base_type_counts.keys()),
            'statistics': dict(base_type_counts)
        }

def main():
    investigator = ModelTypeInvestigator()
    
    print("🔍 CivitAI モデルタイプの包括的調査")
    print("=" * 60)
    
    # 各種調査を実行
    investigations = {
        'known_type_tests': investigator.test_known_types(),
        'discovered_from_samples': investigator.discover_types_from_samples(),
        'multiple_types': investigator.test_multiple_types(),
        'base_model_types': investigator.investigate_base_model_types()
    }
    
    # 結果をまとめ
    print("\n" + "=" * 60)
    print("📊 調査結果サマリー")
    
    # 有効なタイプを特定
    valid_types = []
    if 'known_type_tests' in investigations:
        valid_types = [
            type_name for type_name, result in investigations['known_type_tests'].items()
            if result.get('success', False)
        ]
    
    print(f"✅ 有効なモデルタイプ: {len(valid_types)}個")
    for type_name in sorted(valid_types):
        result = investigations['known_type_tests'][type_name]
        total = result.get('total_available', 'unknown')
        print(f"  - {type_name}: {total}モデル")
    
    # 実際に使用されているタイプ
    if 'discovered_from_samples' in investigations:
        discovered = investigations['discovered_from_samples']['discovered_types']
        print(f"\n🔬 実際に使用されているタイプ: {len(discovered)}個")
        for type_name in sorted(discovered):
            count = investigations['discovered_from_samples']['type_statistics'][type_name]
            print(f"  - {type_name}: {count}サンプル")
    
    # 複数タイプ指定
    if 'multiple_types' in investigations:
        working_multi = [
            combo for combo, result in investigations['multiple_types'].items()
            if result.get('success', False)
        ]
        print(f"\n🔗 複数タイプ指定: {len(working_multi)}個の組み合わせが動作")
        for combo in working_multi:
            print(f"  - {combo}")
    
    # 結果を保存
    with open('model_types_comprehensive_investigation.json', 'w', encoding='utf-8') as f:
        json.dump(investigations, f, indent=2, ensure_ascii=False)
    
    print(f"\n詳細結果: model_types_comprehensive_investigation.json")

if __name__ == "__main__":
    main()