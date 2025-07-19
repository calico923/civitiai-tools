#!/usr/bin/env python3
"""
CivitAI APIの追加モデルタイプ（Embedding、Tool等）を調査
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_additional_types():
    """追加の可能性があるモデルタイプをテスト"""
    api_key = os.getenv('CIVITAI_API_KEY')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else None
    }
    
    # 追加調査対象のタイプ
    additional_types = [
        # Embedding関連
        "Embedding", "Embeddings", "TextualInversion", "TI", 
        
        # Tool関連
        "Tool", "Tools", "Utility", "Script", "Extension",
        
        # 新しいAI技術
        "ControlNet", "IP-Adapter", "T2I-Adapter", "DoRA", "IA3",
        
        # データセット・学習関連
        "Dataset", "Training", "Config", "Workflow", "Workflows",
        
        # 新しいモデルタイプ
        "Motion", "Video", "Audio", "CLIP", "Upscaler", "Inpainting",
        
        # 大文字小文字・複数形バリエーション
        "embedding", "tool", "controlnet", "motion", "video", "audio",
        "vae", "lora", "checkpoint", "hypernetwork", "poses", "wildcards",
        
        # 特殊なタイプ
        "ESRGAN", "RealESRGAN", "SwinIR", "LDSR", "ScuNET",
        "Animation", "Character", "Style", "Concept", "Background",
        
        # 実験的タイプ
        "LoHa", "LoKr", "LoCon", "LyCORIS", "AdaLoRA", "Compel",
        
        # プラットフォーム固有
        "ComfyUI", "A1111", "InvokeAI", "DiffusionBee",
        
        # その他
        "Model", "Merge", "Blend", "Mix", "Fine-tune", "Adapter"
    ]
    
    print(f"🔍 {len(additional_types)}個の追加タイプを調査中...")
    print("=" * 60)
    
    valid_types = []
    invalid_types = []
    
    for i, model_type in enumerate(additional_types, 1):
        print(f"[{i:2d}/{len(additional_types)}] Testing: {model_type}")
        
        try:
            response = requests.get(
                'https://civitai.com/api/v1/models',
                headers=headers,
                params={'types': model_type, 'limit': 3},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    total = data.get('metadata', {}).get('totalItems', 'unknown')
                    examples = [item['name'] for item in data['items'][:2]]
                    valid_types.append({
                        'type': model_type,
                        'total': total,
                        'examples': examples
                    })
                    print(f"    ✅ Valid! Total: {total}")
                    for example in examples:
                        print(f"       - {example}")
                elif 'items' in data:
                    print(f"    ⚠️ Valid type but no results")
                    valid_types.append({
                        'type': model_type,
                        'total': 0,
                        'examples': []
                    })
                else:
                    print(f"    ❌ Invalid response structure")
                    invalid_types.append(model_type)
            else:
                print(f"    ❌ HTTP {response.status_code}")
                invalid_types.append(model_type)
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            invalid_types.append(model_type)
        
        # レート制限対策
        if i % 5 == 0:
            print("    💤 Sleeping 3s...")
            time.sleep(3)
        else:
            time.sleep(0.7)
    
    return valid_types, invalid_types

def main():
    print("🔬 CivitAI 追加モデルタイプ調査")
    print("Testing: Embedding, Tool, Motion, ControlNet, etc.")
    print("=" * 60)
    
    valid_types, invalid_types = test_additional_types()
    
    print("\n" + "=" * 60)
    print("📊 調査結果")
    
    print(f"\n✅ 有効なタイプ ({len(valid_types)}個):")
    for type_info in valid_types:
        if type_info['total'] != 0:
            print(f"  🟢 {type_info['type']}: {type_info['total']} models")
            if type_info['examples']:
                print(f"     Examples: {', '.join(type_info['examples'][:2])}")
        else:
            print(f"  🟡 {type_info['type']}: Valid but no results")
    
    print(f"\n❌ 無効なタイプ ({len(invalid_types)}個):")
    invalid_sample = invalid_types[:10]  # 最初の10個だけ表示
    for invalid_type in invalid_sample:
        print(f"  🔴 {invalid_type}")
    if len(invalid_types) > 10:
        print(f"  ... and {len(invalid_types) - 10} more")
    
    # 新しく発見されたタイプを強調
    known_types = ['Checkpoint', 'LORA', 'LoCon', 'TextualInversion', 'Hypernetwork', 
                   'AestheticGradient', 'VAE', 'Poses', 'Wildcards', 'Other']
    
    new_discoveries = [t for t in valid_types if t['type'] not in known_types and t['total'] != 0]
    
    if new_discoveries:
        print(f"\n🆕 新発見のタイプ ({len(new_discoveries)}個):")
        for type_info in new_discoveries:
            print(f"  ⭐ {type_info['type']}: {type_info['total']} models")
    
    # 全タイプリストを更新
    all_valid_types = known_types + [t['type'] for t in new_discoveries]
    
    print(f"\n🎯 最終的な全タイプリスト ({len(all_valid_types)}個):")
    for i, model_type in enumerate(sorted(all_valid_types), 1):
        print(f"  {i:2d}. {model_type}")
    
    # 結果をファイルに保存
    results = {
        'valid_types': valid_types,
        'invalid_types': invalid_types,
        'new_discoveries': new_discoveries,
        'all_valid_types': sorted(all_valid_types)
    }
    
    import json
    with open('additional_model_types_investigation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 詳細結果: additional_model_types_investigation.json")

if __name__ == "__main__":
    main()