#!/usr/bin/env python3
"""
CivitAI APIからライセンス情報が取得可能か確認するスクリプト
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def get_model_details(model_id):
    """個別モデルの詳細情報を取得"""
    api_key = os.getenv('CIVITAI_API_KEY')
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    url = f'https://civitai.com/api/v1/models/{model_id}'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching model {model_id}: {e}")
        return None

def analyze_license_fields(model_data):
    """モデルデータからライセンス関連フィールドを分析"""
    print(f"\n=== Model: {model_data.get('name', 'Unknown')} (ID: {model_data.get('id')}) ===")
    
    # トップレベルのフィールドを確認
    print("\n1. Top-level fields:")
    relevant_fields = ['allowCommercialUse', 'allowDerivatives', 'allowDifferentLicense', 
                      'allowNoCredit', 'description', 'poi', 'nsfw']
    
    for field in relevant_fields:
        if field in model_data:
            value = model_data[field]
            if field == 'description':
                # 説明文にライセンス情報が含まれているか確認
                desc_lower = str(value).lower()
                license_keywords = ['license', 'commercial', 'copyright', 'terms', 'usage', 
                                  'restriction', 'prohibited', 'allowed', 'permission']
                has_license_info = any(keyword in desc_lower for keyword in license_keywords)
                print(f"  - {field}: <text of {len(str(value))} chars> (Has license info: {has_license_info})")
                
                # ライセンス関連の文言を抽出
                if has_license_info:
                    print("    License-related text found:")
                    lines = value.split('\n')
                    for line in lines:
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in license_keywords):
                            print(f"    > {line.strip()[:100]}...")
            else:
                print(f"  - {field}: {value}")
    
    # バージョン情報を確認
    if 'modelVersions' in model_data and model_data['modelVersions']:
        print("\n2. Model Version fields:")
        version = model_data['modelVersions'][0]
        version_fields = ['trainedWords', 'baseModel', 'baseModelType', 'earlyAccessTimeFrame']
        for field in version_fields:
            if field in version:
                print(f"  - {field}: {version[field]}")
    
    # その他の可能性のあるフィールドを探索
    print("\n3. All available fields:")
    all_fields = list(model_data.keys())
    print(f"  Fields: {', '.join(all_fields)}")
    
    # ライセンス関連の可能性があるフィールドを特定
    potential_license_fields = [f for f in all_fields if 'license' in f.lower() or 
                              'commercial' in f.lower() or 'terms' in f.lower()]
    if potential_license_fields:
        print(f"\n4. Potential license fields found: {potential_license_fields}")
        for field in potential_license_fields:
            print(f"  - {field}: {model_data[field]}")

def main():
    # テスト用モデルID（上位3モデル）
    test_model_ids = [
        140272,  # Hassaku XL (Illustrious)
        24149,   # Mistoon_Anime
        24350    # PerfectDeliberate
    ]
    
    print("Testing CivitAI API for license information...")
    print("=" * 60)
    
    for model_id in test_model_ids:
        model_data = get_model_details(model_id)
        if model_data:
            analyze_license_fields(model_data)
        else:
            print(f"\nFailed to fetch model {model_id}")
        
        print("\n" + "=" * 60)
    
    # API応答の完全な構造を1つ保存
    print("\nSaving complete API response for analysis...")
    if test_model_ids:
        model_data = get_model_details(test_model_ids[0])
        if model_data:
            with open('api_response_sample.json', 'w', encoding='utf-8') as f:
                json.dump(model_data, f, indent=2, ensure_ascii=False)
            print(f"Complete API response saved to api_response_sample.json")

if __name__ == "__main__":
    main()