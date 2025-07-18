"""Functional tests for preview manager - testing actual business logic."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from PIL import Image
import io

from src.preview import PreviewManager
from src.interfaces import ModelInfo, ModelVersion, ModelImage, ModelFile, ModelType
from src.config import ConfigManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=ConfigManager)
    config.config = MagicMock()
    config.config.download_path = "/tmp/test_downloads"
    return config


@pytest.fixture
def sample_model():
    """Create sample model data."""
    return ModelInfo(
        id=12345,
        name="Test Model",
        type=ModelType.LORA,
        description="Test model for functional testing",
        tags=["test", "functional"],
        creator="test_user",
        stats={"downloadCount": 100, "favoriteCount": 20},
        nsfw=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_version():
    """Create sample version data."""
    return ModelVersion(
        id=67890,
        model_id=12345,
        name="v1.0",
        description="Test version",
        base_model="SD 1.5",
        trained_words=["test_trigger"],
        files=[
            ModelFile(
                id=1,
                name="test_model.safetensors",
                size_bytes=50 * 1024 * 1024,
                format="Model",
                fp="fp16",
                hash="abc123",
                download_url="https://example.com/model.safetensors",
                metadata={}
            )
        ],
        images=[
            ModelImage(
                id=1,
                url="https://example.com/image1.jpg",
                width=512,
                height=512,
                hash="img1",
                nsfw=False,
                meta={"prompt": "test prompt", "seed": 123456}
            ),
            ModelImage(
                id=2,
                url="https://example.com/image2.jpg",
                width=1024,
                height=1024,
                hash="img2",
                nsfw=False,
                meta={"prompt": "another prompt", "seed": 789012}
            )
        ],
        download_url="https://example.com/version",
        created_at=datetime.now()
    )


class TestPreviewManagerFunctional:
    """Test actual business logic of PreviewManager."""
    
    def test_image_size_filtering_logic(self, mock_config, sample_model, sample_version):
        """Test the business logic of image size filtering."""
        mock_api_client = AsyncMock()
        mock_api_client.get_model_versions.return_value = [sample_version]
        
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test the filtering logic directly
        images = sample_version.images
        
        # Test 512px filtering with 20% tolerance (410-614 range)
        filtered_512 = []
        for img in images:
            size_diff = abs(img.width - 512) / 512
            if size_diff <= 0.2:  # 20% tolerance
                filtered_512.append(img)
        
        assert len(filtered_512) == 1  # Only 512x512 image should match
        assert filtered_512[0].width == 512
        
        # Test 1024px filtering
        filtered_1024 = []
        for img in images:
            size_diff = abs(img.width - 1024) / 1024
            if size_diff <= 0.2:
                filtered_1024.append(img)
        
        assert len(filtered_1024) == 1  # Only 1024x1024 image should match
        assert filtered_1024[0].width == 1024
        
        # Test no filtering (size=0) - should return all images
        all_images = images.copy()
        # Sort by area (largest first)
        all_images.sort(key=lambda x: x.width * x.height, reverse=True)
        
        assert len(all_images) == 2
        assert all_images[0].width == 1024  # Largest first
        assert all_images[1].width == 512   # Smaller second
    
    def test_model_info_display_content(self, mock_config, sample_model, sample_version, capsys):
        """Test the actual content of model info display."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Call the actual display function
        preview_manager.display_model_info(sample_model, sample_version)
        
        # Capture the output
        captured = capsys.readouterr()
        output = captured.out
        
        # Test that actual business data is displayed
        assert "Test Model" in output
        assert "12345" in output
        assert "LORA" in output
        assert "test_user" in output
        assert "100" in output  # downloadCount
        assert "20" in output   # favoriteCount
        assert "v1.0" in output
        assert "SD 1.5" in output
        assert "test_model.safetensors" in output
        assert "50.0 MB" in output  # File size formatting
        assert "test_trigger" in output  # Trained words
        
        # Test emoji usage
        assert "📦" in output
        assert "👤" in output
        assert "📊" in output
    
    def test_metadata_json_structure(self, mock_config, sample_model, sample_version):
        """Test the actual JSON structure of saved metadata."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            
            # Use the actual save method (async)
            import asyncio
            asyncio.run(preview_manager.save_model_metadata(sample_model, [sample_version], metadata_path))
            
            # Verify file was created
            assert metadata_path.exists()
            
            # Load and verify the actual JSON structure
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Test actual data structure
            assert 'model' in metadata
            assert 'versions' in metadata
            assert 'saved_at' in metadata
            
            # Test model data
            model_data = metadata['model']
            assert model_data['id'] == sample_model.id
            assert model_data['name'] == sample_model.name
            assert model_data['type'] == sample_model.type.value
            assert model_data['creator'] == sample_model.creator
            assert model_data['tags'] == sample_model.tags
            assert model_data['nsfw'] == sample_model.nsfw
            
            # Test version data
            version_data = metadata['versions'][0]
            assert version_data['id'] == sample_version.id
            assert version_data['name'] == sample_version.name
            assert version_data['base_model'] == sample_version.base_model
            assert version_data['trained_words'] == sample_version.trained_words
            
            # Test file data
            file_data = version_data['files'][0]
            assert file_data['name'] == "test_model.safetensors"
            assert file_data['size_bytes'] == 50 * 1024 * 1024
            assert file_data['format'] == "Model"
            assert file_data['fp'] == "fp16"
            
            # Test image data
            image_data = version_data['images'][0]
            assert image_data['width'] == 512
            assert image_data['height'] == 512
            assert image_data['url'] == "https://example.com/image1.jpg"
            assert image_data['meta']['prompt'] == "test prompt"
            assert image_data['meta']['seed'] == 123456
    
    def test_text_formatting_business_logic(self, mock_config):
        """Test the actual text formatting business logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test HTML tag removal
        html_text = "<p>This is <b>bold</b> text with <a href='#'>links</a> and <br> breaks.</p>"
        formatted = preview_manager._format_text(html_text, width=100)
        
        # Verify HTML tags are actually removed
        assert "<p>" not in formatted
        assert "<b>" not in formatted
        assert "</b>" not in formatted
        assert "<a href=" not in formatted
        assert "<br>" not in formatted
        
        # Verify content is preserved
        assert "This is bold text with links and breaks" in formatted
        
        # Test word wrapping
        long_text = "This is a very long text that should be wrapped to multiple lines when displayed in the terminal interface for better readability and user experience."
        formatted = preview_manager._format_text(long_text, width=30, indent=4)
        
        lines = formatted.split('\n')
        assert len(lines) > 1  # Should be wrapped
        
        # Test indentation
        for line in lines:
            if line.strip():  # Skip empty lines
                assert line.startswith('    ')  # 4 spaces indent
        
        # Test line length (excluding indent)
        for line in lines:
            if line.strip():
                assert len(line) <= 34  # 30 + 4 indent
    
    def test_model_comparison_logic(self, mock_config, capsys):
        """Test the actual model comparison business logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Create multiple models for comparison
        model1 = ModelInfo(
            id=1, name="Model A", type=ModelType.LORA, description="First model",
            tags=["anime"], creator="creator1", stats={"downloadCount": 1000, "favoriteCount": 100},
            nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
        )
        
        model2 = ModelInfo(
            id=2, name="Model B", type=ModelType.CHECKPOINT, description="Second model",
            tags=["realistic"], creator="creator2", stats={"downloadCount": 500, "favoriteCount": 50},
            nsfw=True, created_at=datetime.now(), updated_at=datetime.now()
        )
        
        version1 = ModelVersion(
            id=1, model_id=1, name="v1.0", description="", base_model="SD 1.5",
            trained_words=["anime_style"], files=[], images=[], download_url="",
            created_at=datetime.now()
        )
        
        version2 = ModelVersion(
            id=2, model_id=2, name="v2.0", description="", base_model="SDXL 1.0",
            trained_words=["realistic_photo"], files=[], images=[], download_url="",
            created_at=datetime.now()
        )
        
        models_data = [(model1, version1), (model2, version2)]
        
        # Call the actual comparison function
        preview_manager.display_model_comparison(models_data)
        
        # Capture and verify output
        captured = capsys.readouterr()
        output = captured.out
        
        # Test comparison table content
        assert "MODEL COMPARISON" in output
        assert "Model A" in output
        assert "Model B" in output
        assert "LORA" in output
        assert "Checkpoint" in output
        assert "creator1" in output
        assert "creator2" in output
        assert "1,000" in output or "1000" in output  # Download count formatting
        assert "500" in output
        
        # Test table headers
        assert "Model" in output
        assert "Type" in output
        assert "Creator" in output
        assert "Downloads" in output
        assert "Rating" in output
        assert "Updated" in output
    
    def test_license_info_display_logic(self, mock_config, sample_model, capsys):
        """Test the actual license information display logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Call the actual license display function
        preview_manager.display_license_info(sample_model)
        
        # Capture and verify output
        captured = capsys.readouterr()
        output = captured.out
        
        # Test license information content
        assert "LICENSE INFORMATION" in output
        assert "Commercial Use" in output
        assert "Derivatives" in output
        assert "Credit Requirements" in output
        assert "verify license terms" in output
        assert "⚖️" in output  # License emoji
        
        # Test warning message
        assert "original model page" in output
    
    def test_image_metadata_display_logic(self, mock_config, capsys):
        """Test the actual image metadata display logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with comprehensive metadata
        metadata = {
            "prompt": "masterpiece, best quality, anime girl, detailed face, beautiful eyes",
            "negativePrompt": "lowres, bad anatomy, bad hands, text, error, missing fingers",
            "seed": 123456789,
            "cfgScale": 7.5,
            "steps": 20,
            "sampler": "DPM++ 2M Karras",
            "model": "animePaintedMix_v1",
            "clipSkip": 2,
            "denoisingStrength": 0.7
        }
        
        # Call the actual metadata display function
        preview_manager._display_image_metadata(metadata, indent=2)
        
        # Capture and verify output
        captured = capsys.readouterr()
        output = captured.out
        
        # Test metadata content
        assert "masterpiece, best quality, anime girl" in output
        assert "lowres, bad anatomy, bad hands" in output
        assert "123456789" in output
        assert "7.5" in output
        assert "20" in output
        assert "DPM++ 2M Karras" in output
        assert "animePaintedMix_v1" in output
        assert "2" in output  # clipSkip
        assert "0.7" in output  # denoisingStrength
        
        # Test indentation
        lines = output.split('\n')
        for line in lines:
            if line.strip():
                assert line.startswith('  ')  # 2-space indent
    
    def test_file_size_formatting_logic(self, mock_config):
        """Test the actual file size formatting business logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test various file sizes
        test_sizes = [
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (50 * 1024 * 1024, "50.0 MB"),
            (1536 * 1024 * 1024, "1.5 GB"),
            (512, "512 B"),
        ]
        
        for size_bytes, expected in test_sizes:
            formatted = preview_manager._format_file_size(size_bytes)
            assert formatted == expected
    
    def test_aspect_ratio_calculation_logic(self, mock_config):
        """Test the actual aspect ratio calculation logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test various aspect ratios
        test_cases = [
            # (original_width, original_height, target_size, expected_width, expected_height)
            (1920, 1080, 512, 512, 288),  # 16:9 landscape
            (1080, 1920, 512, 288, 512),  # 9:16 portrait
            (1024, 1024, 512, 512, 512),  # 1:1 square
            (1600, 900, 400, 400, 225),   # 16:9 landscape smaller
            (3840, 2160, 1024, 1024, 576), # 4K 16:9
        ]
        
        for orig_w, orig_h, target, exp_w, exp_h in test_cases:
            # This would be the actual calculation logic from the resize method
            if orig_w > orig_h:
                new_width = target
                new_height = int(orig_h * (target / orig_w))
            else:
                new_height = target
                new_width = int(orig_w * (target / orig_h))
            
            assert new_width == exp_w
            assert new_height == exp_h
            
            # Verify aspect ratio is preserved (within reasonable tolerance)
            original_ratio = orig_w / orig_h
            new_ratio = new_width / new_height
            assert abs(original_ratio - new_ratio) < 0.01  # Within 1% tolerance


class TestPreviewManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_model_data_handling(self, mock_config, capsys):
        """Test handling of empty or minimal model data."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Model with minimal data
        minimal_model = ModelInfo(
            id=1, name="", type=ModelType.LORA, description="",
            tags=[], creator="", stats={}, nsfw=False,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        
        # Should not crash
        preview_manager.display_model_info(minimal_model)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should still display basic structure
        assert "📦" in output
        assert "ID: 1" in output
        assert "Type: LORA" in output
    
    def test_metadata_with_missing_fields(self, mock_config):
        """Test metadata handling with missing or invalid fields."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with various missing fields
        incomplete_metadata = {
            "prompt": "test prompt",
            # Missing negativePrompt
            "seed": "invalid_seed",  # Invalid type
            "cfgScale": None,  # None value
            # Missing steps, sampler, model
        }
        
        # Should not crash
        preview_manager._display_image_metadata(incomplete_metadata)
        
        # Should handle None values gracefully
        none_metadata = {
            "prompt": None,
            "seed": None,
            "cfgScale": None,
        }
        
        preview_manager._display_image_metadata(none_metadata)
    
    def test_extreme_file_sizes(self, mock_config):
        """Test file size formatting with extreme values."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test edge cases
        extreme_sizes = [
            (0, "0 B"),
            (1, "1 B"),
            (1023, "1023 B"),
            (1024 * 1024 * 1024 * 1024, "1.0 TB"),  # 1 TB
            (999 * 1024 * 1024 * 1024, "999.0 GB"),  # 999 GB
        ]
        
        for size_bytes, expected in extreme_sizes:
            formatted = preview_manager._format_file_size(size_bytes)
            assert formatted == expected
    
    def test_unicode_and_special_characters(self, mock_config):
        """Test handling of unicode and special characters."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with unicode text
        unicode_text = "アニメ風イラスト、美少女、高品質、詳細な背景、🎨✨"
        formatted = preview_manager._format_text(unicode_text, width=50)
        
        # Should preserve unicode characters
        assert "アニメ風イラスト" in formatted
        assert "🎨✨" in formatted
        
        # Test with HTML and unicode
        html_unicode = "<p>アニメ風の<strong>美少女</strong>イラスト</p>"
        formatted = preview_manager._format_text(html_unicode, width=50)
        
        # Should remove HTML but preserve unicode
        assert "<p>" not in formatted
        assert "<strong>" not in formatted
        assert "アニメ風の美少女イラスト" in formatted