import pytest
import tempfile
import shutil
import json
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.url_collector import URLCollector, URLInfo
from tests.fixtures.sample_models import VALID_MODEL_DATA, INVALID_MODEL_DATA, EDGE_CASE_MODEL_DATA


class TestURLCollectorInitialization:
    """URLCollector初期化テスト"""
    
    def setup_method(self):
        """各テストメソッド前に実行される準備処理"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """各テストメソッド後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_urlcollector_creates_output_directory(self):
        """出力ディレクトリが作成されることを確認"""
        output_dir = self.temp_dir / "test_output"
        
        collector = URLCollector(output_dir=output_dir)
        
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert collector.output_dir == output_dir
    
    def test_urlcollector_uses_default_output_directory(self):
        """デフォルト出力ディレクトリが使用されることを確認"""
        with patch('src.core.url_collector.Path') as mock_path:
            mock_output_dir = MagicMock()
            mock_path.return_value = mock_output_dir
            
            collector = URLCollector()
            
            mock_path.assert_called_once_with("outputs/urls")
            mock_output_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    def test_urlcollector_handles_existing_directory(self):
        """既存ディレクトリがある場合の処理確認"""
        output_dir = self.temp_dir / "existing_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        collector = URLCollector(output_dir=output_dir)
        
        assert output_dir.exists()
        assert collector.output_dir == output_dir


class TestURLInfoDataStructure:
    """URLInfoデータ構造テスト"""
    
    def test_urlinfo_creation_with_valid_data(self):
        """有効なデータでURLInfoが作成できることを確認"""
        url_info = URLInfo(
            model_id=12345,
            version_id=67890,
            model_name="Test Model",
            model_type="LORA",
            download_url="https://civitai.com/api/download/models/67890",
            file_size=1024000,
            tags=["tag1", "tag2"],
            creator="test_creator",
            civitai_url="https://civitai.com/models/12345"
        )
        
        assert url_info.model_id == 12345
        assert url_info.version_id == 67890
        assert url_info.model_name == "Test Model"
        assert url_info.model_type == "LORA"
        assert url_info.download_url == "https://civitai.com/api/download/models/67890"
        assert url_info.file_size == 1024000
        assert url_info.tags == ["tag1", "tag2"]
        assert url_info.creator == "test_creator"
        assert url_info.civitai_url == "https://civitai.com/models/12345"
    
    def test_urlinfo_immutability(self):
        """URLInfoが不変であることを確認"""
        url_info = URLInfo(
            model_id=1,
            version_id=2,
            model_name="Test",
            model_type="LORA",
            download_url="https://example.com",
            file_size=1000,
            tags=["tag"],
            creator="creator",
            civitai_url="https://civitai.com/models/1"
        )
        
        with pytest.raises(AttributeError):
            url_info.model_id = 999


class TestURLCollection:
    """URL収集テスト（モック使用）"""
    
    def setup_method(self):
        """各テストメソッド前に実行される準備処理"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.collector = URLCollector(output_dir=self.temp_dir)
    
    def teardown_method(self):
        """各テストメソッド後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_collect_model_urls_with_valid_data(self):
        """有効なモデルデータからURL情報を抽出できることを確認"""
        urls = self.collector.collect_model_urls(VALID_MODEL_DATA)
        
        assert len(urls) == 2
        
        # 最初のモデル確認
        first_url = urls[0]
        assert first_url.model_id == 12345
        assert first_url.version_id == 67890
        assert first_url.model_name == "Test LORA Model"
        assert first_url.model_type == "LORA"
        assert first_url.download_url == "https://civitai.com/api/download/models/67890"
        assert first_url.file_size == 1024000  # 1000KB * 1024
        assert first_url.tags == ["pony", "style"]
        assert first_url.creator == "test_creator"
        assert first_url.civitai_url == "https://civitai.com/models/12345"
        
        # 2番目のモデル確認
        second_url = urls[1]
        assert second_url.model_id == 54321
        assert second_url.version_id == 98765
        assert second_url.model_name == "Another Test Model"
        assert second_url.model_type == "Checkpoint"
    
    def test_collect_model_urls_with_invalid_data(self):
        """不正なモデルデータのハンドリング確認"""
        urls = self.collector.collect_model_urls(INVALID_MODEL_DATA)
        
        # 不正なデータは除外され、空のリストが返される
        assert len(urls) == 0
    
    def test_collect_model_urls_with_mixed_data(self):
        """有効・無効混在データでの処理確認"""
        mixed_data = VALID_MODEL_DATA + INVALID_MODEL_DATA
        urls = self.collector.collect_model_urls(mixed_data)
        
        # 有効なデータのみが抽出される
        assert len(urls) == 2
        assert all(isinstance(url, URLInfo) for url in urls)
    
    def test_collect_model_urls_with_edge_cases(self):
        """境界値テスト用データでの処理確認"""
        urls = self.collector.collect_model_urls(EDGE_CASE_MODEL_DATA)
        
        assert len(urls) == 1
        large_model_url = urls[0]
        assert large_model_url.file_size == 10240000000  # 10GB in bytes
        assert large_model_url.model_name == "Large Model"
    
    def test_collect_model_urls_with_empty_list(self):
        """空のモデルリストでの処理確認"""
        urls = self.collector.collect_model_urls([])
        
        assert len(urls) == 0
        assert isinstance(urls, list)


class TestOutputFormats:
    """出力形式テスト"""
    
    def setup_method(self):
        """各テストメソッド前に実行される準備処理"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.collector = URLCollector(output_dir=self.temp_dir)
        self.test_urls = self.collector.collect_model_urls(VALID_MODEL_DATA)
    
    def teardown_method(self):
        """各テストメソッド後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_export_to_text_format(self):
        """テキスト形式での出力確認"""
        output_file = self.collector.export_to_text(self.test_urls, "test_urls.txt")
        
        assert output_file.exists()
        assert output_file.suffix == ".txt"
        
        content = output_file.read_text(encoding='utf-8')
        assert "# Civitai Model URLs" in content
        assert "Total models: 2" in content
        assert "https://civitai.com/api/download/models/67890" in content
        assert "https://civitai.com/api/download/models/98765" in content
        assert "Test LORA Model" in content
        assert "Another Test Model" in content
    
    def test_export_to_csv_format(self):
        """CSV形式での出力確認"""
        output_file = self.collector.export_to_csv(self.test_urls, "test_urls.csv")
        
        assert output_file.exists()
        assert output_file.suffix == ".csv"
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        
        # ヘッダー確認
        expected_headers = ['model_id', 'version_id', 'model_name', 'model_type',
                          'download_url', 'file_size_mb', 'tags', 'creator', 'civitai_url']
        assert list(rows[0].keys()) == expected_headers
        
        # データ確認
        first_row = rows[0]
        assert first_row['model_id'] == '12345'
        assert first_row['model_name'] == 'Test LORA Model'
        assert first_row['file_size_mb'] == '0.98'  # 1000KB = 0.976MB
    
    def test_export_to_json_format(self):
        """JSON形式での出力確認"""
        output_file = self.collector.export_to_json(self.test_urls, "test_urls.json")
        
        assert output_file.exists()
        assert output_file.suffix == ".json"
        
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'generated_at' in data
        assert data['total_models'] == 2
        assert 'models' in data
        assert len(data['models']) == 2
        
        first_model = data['models'][0]
        assert first_model['model_id'] == 12345
        assert first_model['model_name'] == 'Test LORA Model'
        assert first_model['file_size'] == 1024000
    
    def test_export_with_empty_url_list(self):
        """空のURLリストでの出力動作確認"""
        empty_urls = []
        
        # テキスト形式
        text_file = self.collector.export_to_text(empty_urls, "empty.txt")
        content = text_file.read_text(encoding='utf-8')
        assert "Total models: 0" in content
        
        # CSV形式
        csv_file = self.collector.export_to_csv(empty_urls, "empty.csv")
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 0
        
        # JSON形式
        json_file = self.collector.export_to_json(empty_urls, "empty.json")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['total_models'] == 0
        assert data['models'] == []
    
    def test_export_with_default_filenames(self):
        """デフォルトファイル名での出力確認"""
        # デフォルトファイル名で出力
        text_file = self.collector.export_to_text(self.test_urls)
        csv_file = self.collector.export_to_csv(self.test_urls)
        json_file = self.collector.export_to_json(self.test_urls)
        
        # ファイルが作成されていることを確認
        assert text_file.exists()
        assert csv_file.exists()
        assert json_file.exists()
        
        # ファイル名にタイムスタンプが含まれていることを確認
        assert "urls_" in text_file.name
        assert "urls_" in csv_file.name  
        assert "urls_" in json_file.name
        
        # 拡張子が正しいことを確認
        assert text_file.suffix == ".txt"
        assert csv_file.suffix == ".csv"
        assert json_file.suffix == ".json"
    
    def test_file_content_encoding(self):
        """ファイル内容のエンコーディング確認"""
        # 日本語を含むテストデータ
        japanese_model_data = [{
            "id": 77777,
            "name": "日本語モデル",
            "type": "LORA",
            "tags": ["アニメ", "キャラクター"],
            "creator": {"username": "日本のクリエイター"},
            "modelVersions": [{
                "id": 88888,
                "name": "v1.0",
                "files": [{"name": "model.safetensors", "sizeKB": 1000}]
            }]
        }]
        
        urls = self.collector.collect_model_urls(japanese_model_data)
        
        # UTF-8で正しく出力されることを確認
        text_file = self.collector.export_to_text(urls, "japanese.txt")
        content = text_file.read_text(encoding='utf-8')
        assert "日本語モデル" in content
        assert "アニメ" in content
        
        csv_file = self.collector.export_to_csv(urls, "japanese.csv")
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "日本語モデル" in content
        assert "日本のクリエイター" in content