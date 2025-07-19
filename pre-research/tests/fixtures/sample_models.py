"""テスト用のサンプルモデルデータ"""

VALID_MODEL_DATA = [
    {
        "id": 12345,
        "name": "Test LORA Model",
        "type": "LORA",
        "tags": ["pony", "style"],
        "creator": {"username": "test_creator"},
        "modelVersions": [
            {
                "id": 67890,
                "name": "v1.0",
                "files": [
                    {
                        "name": "test_model.safetensors",
                        "sizeKB": 1000,
                        "type": "Model",
                        "format": "SafeTensors"
                    }
                ]
            }
        ]
    },
    {
        "id": 54321,
        "name": "Another Test Model",
        "type": "Checkpoint",
        "tags": ["realistic", "portrait"],
        "creator": {"username": "another_creator"},
        "modelVersions": [
            {
                "id": 98765,
                "name": "v2.1",
                "files": [
                    {
                        "name": "checkpoint.safetensors",
                        "sizeKB": 5000,
                        "type": "Model",
                        "format": "SafeTensors"
                    }
                ]
            }
        ]
    }
]

INVALID_MODEL_DATA = [
    # modelVersionsが空のモデル
    {
        "id": 11111,
        "name": "No Versions Model",
        "type": "LORA",
        "tags": ["test"],
        "creator": {"username": "test_user"},
        "modelVersions": []
    },
    # modelVersionsがないモデル
    {
        "id": 22222,
        "name": "Missing Versions Model",
        "type": "LORA",
        "tags": ["test"],
        "creator": {"username": "test_user"}
    },
    # filesが空のモデル
    {
        "id": 33333,
        "name": "No Files Model",
        "type": "LORA",
        "tags": ["test"],
        "creator": {"username": "test_user"},
        "modelVersions": [
            {
                "id": 44444,
                "name": "v1.0",
                "files": []
            }
        ]
    }
]

EDGE_CASE_MODEL_DATA = [
    # 極端に大きなファイルサイズ
    {
        "id": 99999,
        "name": "Large Model",
        "type": "Checkpoint",
        "tags": ["large"],
        "creator": {"username": "large_creator"},
        "modelVersions": [
            {
                "id": 88888,
                "name": "v1.0",
                "files": [
                    {
                        "name": "large_model.safetensors",
                        "sizeKB": 10000000,  # 10GB
                        "type": "Model",
                        "format": "SafeTensors"
                    }
                ]
            }
        ]
    }
]