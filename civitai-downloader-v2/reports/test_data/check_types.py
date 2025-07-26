import json

with open('reports/test_data/lora_100_mixed.json', 'r') as f:
    models = json.load(f)

# Count by model type
model_types = {}
for model in models:
    model_type = model.get('type', 'Unknown')
    model_types[model_type] = model_types.get(model_type, 0) + 1

print('Model types in mixed dataset:')
for model_type, count in sorted(model_types.items()):
    print(f'  {model_type}: {count} models')

# Check if we have non-LoRA types
non_lora_count = 0
for model in models:
    if model.get('type', '') != 'LoRA':
        non_lora_count += 1
        if non_lora_count <= 3:
            print(f'  Non-LoRA: {model.get("name", "Unknown")} (Type: {model.get("type", "Unknown")})')

print(f'Total non-LoRA models: {non_lora_count}')