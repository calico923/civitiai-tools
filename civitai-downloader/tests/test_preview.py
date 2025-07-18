"""Tests for model preview and details display system."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import json
import tempfile
import os
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
        name="Test Anime Model",
        type=ModelType.LORA,
        description="A test model for anime generation with detailed description that can be quite long.",
        tags=["anime", "character", "portrait", "style", "detailed"],
        creator="test_creator",
        stats={
            "downloadCount": 1500,
            "favoriteCount": 234,
            "commentCount": 45,
            "ratingCount": 89,
            "rating": 4.2
        },
        nsfw=False,
        created_at=datetime(2023, 1, 15, 10, 30, 0),
        updated_at=datetime(2023, 6, 20, 14, 45, 0)
    )


@pytest.fixture
def sample_version():
    """Create sample version data."""
    return ModelVersion(
        id=67890,
        model_id=12345,
        name="v1.0",
        description="Initial release version",
        base_model="SD 1.5",
        trained_words=["anime_style", "character_art"],
        files=[
            ModelFile(
                id=1,
                name="test_model.safetensors",
                size_bytes=50 * 1024 * 1024,  # 50MB
                format="Model",
                fp="fp16",
                hash="abc123def456",
                download_url="https://example.com/download/test_model.safetensors",
                metadata={"format": "safetensors"}
            )
        ],
        images=[
            ModelImage(
                id=1,
                url="https://example.com/image1.jpg",
                width=512,
                height=512,
                hash="img123",
                nsfw=False,
                meta={
                    "prompt": "anime girl portrait, detailed, masterpiece",
                    "negativePrompt": "blurry, low quality",
                    "seed": 123456789,
                    "cfgScale": 7.5,
                    "steps": 20,
                    "sampler": "DPM++ 2M Karras",
                    "model": "test_model_v1"
                }
            ),
            ModelImage(
                id=2,
                url="https://example.com/image2.jpg",
                width=1024,
                height=1024,
                hash="img456",
                nsfw=False,
                meta={
                    "prompt": "anime character, full body, detailed background",
                    "seed": 987654321,
                    "steps": 30
                }
            )
        ],
        download_url="https://example.com/download/version",
        created_at=datetime(2023, 1, 15, 10, 30, 0)
    )


@pytest.fixture
def sample_images():
    """Create sample image data."""
    return [
        ModelImage(
            id=1,
            url="https://example.com/image1.jpg",
            width=512,
            height=512,
            hash="img123",
            nsfw=False,
            meta={"prompt": "test prompt", "seed": 123456}
        ),
        ModelImage(
            id=2,
            url="https://example.com/image2.jpg",
            width=256,
            height=256,
            hash="img456",
            nsfw=False,
            meta={"prompt": "another test", "seed": 654321}
        ),
        ModelImage(
            id=3,
            url="https://example.com/image3.jpg",
            width=1024,
            height=1024,
            hash="img789",
            nsfw=True,
            meta={"prompt": "high res test", "seed": 999999}
        )
    ]


class TestPreviewManager:
    """Test PreviewManager functionality."""
    
    @pytest.mark.asyncio
    async def test_get_preview_images_with_size_filter(self, mock_config, sample_model, sample_version):
        """Test getting preview images with size filtering."""
        mock_api_client = AsyncMock()
        mock_api_client.get_model_versions.return_value = [sample_version]
        
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test filtering by size (512px)
        images = await preview_manager.get_preview_images(sample_model, size=512)
        
        # Should return only the 512x512 image
        assert len(images) == 1
        assert images[0].width == 512
        assert images[0].height == 512
        
        # Test no size filtering
        images = await preview_manager.get_preview_images(sample_model, size=0)
        
        # Should return all images, sorted by size (largest first)
        assert len(images) == 2
        assert images[0].width == 1024  # Largest first
        assert images[1].width == 512
    
    @pytest.mark.asyncio
    async def test_get_preview_images_with_tolerance(self, mock_config, sample_model):
        """Test size filtering with tolerance."""
        # Create version with images of various sizes
        version = ModelVersion(
            id=1, model_id=sample_model.id, name="v1.0", description="Test",
            base_model="SD 1.5", trained_words=[], files=[], download_url="",
            created_at=datetime.now(),
            images=[
                ModelImage(id=1, url="test1.jpg", width=480, height=480, hash="h1", nsfw=False, meta={}),
                ModelImage(id=2, url="test2.jpg", width=512, height=512, hash="h2", nsfw=False, meta={}),
                ModelImage(id=3, url="test3.jpg", width=550, height=550, hash="h3", nsfw=False, meta={}),
                ModelImage(id=4, url="test4.jpg", width=800, height=800, hash="h4", nsfw=False, meta={}),
            ]
        )
        
        mock_api_client = AsyncMock()
        mock_api_client.get_model_versions.return_value = [version]
        
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test filtering by 512 with 20% tolerance (should accept 410-614 range)
        images = await preview_manager.get_preview_images(sample_model, size=512)
        
        # Should return images 1, 2, 3 (within tolerance) but not 4 (too large)
        assert len(images) == 3
        widths = [img.width for img in images]
        assert 480 in widths
        assert 512 in widths
        assert 550 in widths
        assert 800 not in widths
    
    @pytest.mark.asyncio
    async def test_download_image_without_resize(self, mock_config):
        """Test downloading image without resizing - focuses on file handling logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Mock image data
        test_image = ModelImage(
            id=1, url="https://example.com/test.jpg", width=512, height=512,
            hash="test", nsfw=False, meta={}
        )
        
        # Mock aiohttp response with proper async context manager
        mock_response_data = b"fake_image_data_that_represents_actual_jpeg_content"
        
        with patch('src.preview.aiohttp.ClientSession') as mock_session_class:
            # Create proper mock hierarchy for async context managers
            mock_session_instance = AsyncMock()
            mock_response = AsyncMock()
            mock_response.read.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            # Mock the async context manager chain
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session_instance
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "test_image.jpg"
                
                await preview_manager.download_image(test_image, download_path)
                
                # Verify the actual business logic
                assert download_path.exists(), "File should be created"
                assert download_path.read_bytes() == mock_response_data, "File content should match"
                
                # Verify directory creation logic
                assert download_path.parent.exists(), "Parent directory should be created"
                
                # Verify API interaction
                mock_session_instance.get.assert_called_once_with("https://example.com/test.jpg")
                mock_response.raise_for_status.assert_called_once()
                mock_response.read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_image_with_resize(self, mock_config):
        """Test downloading image with resizing - validates image processing logic."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        test_image = ModelImage(
            id=1, url="https://example.com/test.jpg", width=1024, height=1024,
            hash="test", nsfw=False, meta={}
        )
        
        # Create a realistic test image
        from PIL import Image
        test_pil_image = Image.new('RGB', (1024, 1024), color='red')
        image_buffer = io.BytesIO()
        test_pil_image.save(image_buffer, format='PNG')
        mock_response_data = image_buffer.getvalue()
        
        with patch('src.preview.aiohttp.ClientSession') as mock_session_class:
            # Create proper mock hierarchy for async context managers
            mock_session_instance = AsyncMock()
            mock_response = AsyncMock()
            mock_response.read.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            # Mock the async context manager chain
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session_instance
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "test_image_resized.png"
                
                await preview_manager.download_image(test_image, download_path, size=512)
                
                # Verify the actual business logic
                assert download_path.exists(), "Resized image file should be created"
                
                # Load and verify the resized image
                resized_image = Image.open(download_path)
                assert resized_image.size == (512, 512), "Image should be resized to 512x512"
                
                # Verify the image is still valid and properly formatted
                assert resized_image.format == 'PNG', "Image should be saved as PNG"
                assert resized_image.mode == 'RGB', "Image should maintain RGB mode"
                
                # Verify API interaction
                mock_session_instance.get.assert_called_once_with("https://example.com/test.jpg")
                mock_response.raise_for_status.assert_called_once()
                mock_response.read.assert_called_once()
    
    def test_display_model_info_basic(self, mock_config, sample_model, sample_version, capsys):
        """Test basic model info display."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        preview_manager.display_model_info(sample_model, sample_version)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that key information is displayed
        assert "Test Anime Model" in output
        assert "ID: 12345" in output
        assert "Type: LORA" in output
        assert "Creator: test_creator" in output
        assert "Downloads: 1,500" in output
        assert "Favorites: 234" in output
        assert "Rating: 4.2/5" in output
        assert "v1.0" in output
        assert "SD 1.5" in output
        assert "test_model.safetensors" in output
        assert "50.0 MB" in output
    
    def test_display_model_info_with_tags(self, mock_config, sample_model, capsys):
        """Test model info display with tags."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        preview_manager.display_model_info(sample_model)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check tags are displayed
        assert "anime, character, portrait, style, detailed" in output
    
    def test_display_model_info_with_nsfw(self, mock_config, sample_model, capsys):
        """Test model info display with NSFW indicator."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with NSFW model
        sample_model.nsfw = True
        preview_manager.display_model_info(sample_model)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "NSFW: Yes" in output
    
    def test_display_model_comparison(self, mock_config, capsys):
        """Test model comparison display."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Create multiple models for comparison
        models = [
            (ModelInfo(
                id=1, name="Model A", type=ModelType.LORA, description="First model",
                tags=["test"], creator="creator1", stats={"downloadCount": 1000, "rating": 4.5},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ), None),
            (ModelInfo(
                id=2, name="Model B", type=ModelType.CHECKPOINT, description="Second model",
                tags=["test"], creator="creator2", stats={"downloadCount": 500, "rating": 4.0},
                nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
            ), None),
        ]
        
        preview_manager.display_model_comparison(models)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check comparison table is displayed
        assert "MODEL COMPARISON" in output
        assert "Model A" in output
        assert "Model B" in output
        assert "LORA" in output
        assert "Checkpoint" in output  # ModelType.CHECKPOINT.value is "Checkpoint"
        assert "creator1" in output
        assert "creator2" in output
        assert "1,000" in output or "1000" in output  # Accept both formats
        assert "500" in output
    
    def test_display_license_info(self, mock_config, sample_model, capsys):
        """Test license information display."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        preview_manager.display_license_info(sample_model)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check license information is displayed
        assert "LICENSE INFORMATION" in output
        assert "Commercial Use" in output
        assert "Derivatives" in output
        assert "Credit Requirements" in output
        assert "verify license terms" in output
    
    @pytest.mark.asyncio
    async def test_get_model_details_with_versions(self, mock_config, sample_model, sample_version):
        """Test getting comprehensive model details."""
        mock_api_client = AsyncMock()
        mock_api_client.get_model_details.return_value = sample_model
        mock_api_client.get_model_versions.return_value = [sample_version]
        
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        model, versions = await preview_manager.get_model_details_with_versions(12345)
        
        assert model == sample_model
        assert len(versions) == 1
        assert versions[0] == sample_version
        
        # Verify API calls were made
        mock_api_client.get_model_details.assert_called_once_with(12345)
        mock_api_client.get_model_versions.assert_called_once_with(12345)
    
    @pytest.mark.asyncio
    async def test_save_model_metadata(self, mock_config, sample_model, sample_version):
        """Test saving model metadata to JSON."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            
            await preview_manager.save_model_metadata(sample_model, [sample_version], metadata_path)
            
            # Check file was created
            assert metadata_path.exists()
            
            # Load and verify metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check model data
            assert metadata['model']['id'] == sample_model.id
            assert metadata['model']['name'] == sample_model.name
            assert metadata['model']['type'] == sample_model.type.value
            assert metadata['model']['creator'] == sample_model.creator
            
            # Check version data
            assert len(metadata['versions']) == 1
            version_data = metadata['versions'][0]
            assert version_data['id'] == sample_version.id
            assert version_data['name'] == sample_version.name
            assert version_data['base_model'] == sample_version.base_model
            assert len(version_data['files']) == 1
            assert len(version_data['images']) == 2
            
            # Check file data
            file_data = version_data['files'][0]
            assert file_data['name'] == "test_model.safetensors"
            assert file_data['size_bytes'] == 50 * 1024 * 1024
            
            # Check image data
            image_data = version_data['images'][0]
            assert image_data['width'] == 512
            assert image_data['height'] == 512
            assert 'prompt' in image_data['meta']
    
    def test_load_model_metadata(self, mock_config):
        """Test loading model metadata from JSON."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Create test metadata
        test_metadata = {
            "model": {
                "id": 12345,
                "name": "Test Model",
                "type": "LORA"
            },
            "versions": [
                {
                    "id": 67890,
                    "name": "v1.0",
                    "files": [],
                    "images": []
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            
            # Save test metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(test_metadata, f)
            
            # Load metadata
            loaded_metadata = preview_manager.load_model_metadata(metadata_path)
            
            assert loaded_metadata == test_metadata
            
            # Test loading non-existent file
            non_existent_path = Path(temp_dir) / "nonexistent.json"
            result = preview_manager.load_model_metadata(non_existent_path)
            assert result is None
    
    def test_format_text_wrapping(self, mock_config):
        """Test text formatting with word wrapping."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test long text
        long_text = "This is a very long text that should be wrapped to multiple lines when displayed in the terminal interface."
        
        formatted = preview_manager._format_text(long_text, width=30, indent=4)
        
        # Check that text is wrapped
        lines = formatted.split('\n')
        assert len(lines) > 1
        
        # Check indentation
        for line in lines:
            assert line.startswith('    ')  # 4 spaces indent
        
        # Check line length (excluding indent)
        for line in lines:
            assert len(line) <= 34  # 30 + 4 indent
    
    def test_format_text_html_removal(self, mock_config):
        """Test HTML tag removal from text."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test text with HTML tags
        html_text = "This is <b>bold</b> text with <a href='#'>links</a> and <br> breaks."
        
        formatted = preview_manager._format_text(html_text, width=100)
        
        # Check that HTML tags are removed
        assert '<b>' not in formatted
        assert '</b>' not in formatted
        assert '<a href=' not in formatted
        assert '<br>' not in formatted
        assert 'bold text with links and breaks' in formatted
    
    def test_display_image_metadata(self, mock_config, capsys):
        """Test image metadata display."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test metadata
        metadata = {
            "prompt": "anime girl, detailed, masterpiece",
            "negativePrompt": "blurry, low quality, bad anatomy",
            "seed": 123456789,
            "cfgScale": 7.5,
            "steps": 20,
            "sampler": "DPM++ 2M Karras",
            "model": "test_model_v1"
        }
        
        preview_manager._display_image_metadata(metadata, indent=2)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that metadata is displayed with proper indentation
        lines = output.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                assert line.startswith('  ')  # 2 spaces indent
        
        # Check content
        assert "anime girl, detailed, masterpiece" in output
        assert "blurry, low quality, bad anatomy" in output
        assert "123456789" in output
        assert "7.5" in output
        assert "20" in output
        assert "DPM++ 2M Karras" in output
        assert "test_model_v1" in output


class TestPreviewManagerRealWorldScenarios:
    """Test PreviewManager with real-world scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_image_size_filtering_real_world_scenarios(self, mock_config):
        """Test image size filtering with realistic data variations."""
        mock_api_client = AsyncMock()
        
        # Create versions with realistic image size variations
        versions = [
            ModelVersion(
                id=1, model_id=123, name="v1.0", description="", base_model="SD 1.5",
                trained_words=[], files=[], download_url="", created_at=datetime.now(),
                images=[
                    # Common sizes in the wild
                    ModelImage(id=1, url="1.jpg", width=512, height=512, hash="h1", nsfw=False, meta={}),
                    ModelImage(id=2, url="2.jpg", width=768, height=768, hash="h2", nsfw=False, meta={}),
                    ModelImage(id=3, url="3.jpg", width=1024, height=1024, hash="h3", nsfw=False, meta={}),
                    ModelImage(id=4, url="4.jpg", width=1536, height=1536, hash="h4", nsfw=False, meta={}),
                    # Irregular sizes
                    ModelImage(id=5, url="5.jpg", width=600, height=400, hash="h5", nsfw=False, meta={}),
                    ModelImage(id=6, url="6.jpg", width=256, height=256, hash="h6", nsfw=False, meta={}),
                    # Very large sizes
                    ModelImage(id=7, url="7.jpg", width=2048, height=2048, hash="h7", nsfw=False, meta={}),
                ]
            )
        ]
        
        mock_api_client.get_model_versions.return_value = versions
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        model = ModelInfo(
            id=123, name="Test", type=ModelType.LORA, description="", tags=[], creator="",
            stats={}, nsfw=False, created_at=datetime.now(), updated_at=datetime.now()
        )
        
        # Test filtering by 512 (should accept 410-614 range with 20% tolerance)
        images_512 = await preview_manager.get_preview_images(model, size=512)
        assert len(images_512) == 2  # 512x512 and 600x400 (width in range)
        
        # Test filtering by 1024 (should accept 819-1229 range)
        images_1024 = await preview_manager.get_preview_images(model, size=1024)
        assert len(images_1024) == 1  # Only 1024x1024
        
        # Test no filtering (should return all, sorted by area)
        images_all = await preview_manager.get_preview_images(model, size=0)
        assert len(images_all) == 7
        # Should be sorted by area (largest first)
        areas = [img.width * img.height for img in images_all]
        assert areas == sorted(areas, reverse=True)
        
        # Test filtering by uncommon size
        images_256 = await preview_manager.get_preview_images(model, size=256)
        assert len(images_256) == 1  # Only 256x256
        assert images_256[0].width == 256
    
    @pytest.mark.asyncio
    async def test_aspect_ratio_preservation_in_resize(self, mock_config):
        """Test that aspect ratio is preserved when resizing non-square images."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with rectangular image (16:9 aspect ratio)
        test_image = ModelImage(
            id=1, url="https://example.com/test.jpg", width=1920, height=1080,
            hash="test", nsfw=False, meta={}
        )
        
        # Create a rectangular test image
        from PIL import Image
        test_pil_image = Image.new('RGB', (1920, 1080), color='blue')
        image_buffer = io.BytesIO()
        test_pil_image.save(image_buffer, format='PNG')
        mock_response_data = image_buffer.getvalue()
        
        with patch('src.preview.aiohttp.ClientSession') as mock_session_class:
            mock_session_instance = AsyncMock()
            mock_response = AsyncMock()
            mock_response.read.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session_instance
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "test_rectangular.png"
                
                await preview_manager.download_image(test_image, download_path, size=512)
                
                # Verify aspect ratio is preserved
                resized_image = Image.open(download_path)
                
                # For 16:9 aspect ratio, if width is 512, height should be 288
                expected_height = int(512 * (1080 / 1920))  # 288
                assert resized_image.size == (512, expected_height)
                
                # Verify aspect ratio is approximately preserved
                original_ratio = 1920 / 1080
                resized_ratio = resized_image.width / resized_image.height
                assert abs(original_ratio - resized_ratio) < 0.01  # Within 1% tolerance
    
    @pytest.mark.asyncio
    async def test_error_handling_network_failures(self, mock_config):
        """Test error handling during network failures."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        test_image = ModelImage(
            id=1, url="https://example.com/test.jpg", width=512, height=512,
            hash="test", nsfw=False, meta={}
        )
        
        # Test HTTP error
        with patch('src.preview.aiohttp.ClientSession') as mock_session_class:
            mock_session_instance = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 404")
            
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session_instance
            
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir) / "test_error.jpg"
                
                # Should raise exception
                with pytest.raises(Exception):
                    await preview_manager.download_image(test_image, download_path)
                
                # File should not be created
                assert not download_path.exists()
    
    def test_text_formatting_with_complex_content(self, mock_config):
        """Test text formatting with complex real-world content."""
        mock_api_client = AsyncMock()
        preview_manager = PreviewManager(api_client=mock_api_client, config=mock_config)
        
        # Test with complex HTML content
        html_content = """
        <p>This is a <strong>comprehensive</strong> model for generating 
        <em>high-quality</em> anime characters with <a href="https://example.com">detailed features</a>.</p>
        
        <ul>
            <li>Support for multiple art styles</li>
            <li>Compatible with <code>SD 1.5</code> and <code>SDXL</code></li>
            <li>Trained on <span style="color: red;">10,000+ images</span></li>
        </ul>
        
        <h3>Usage Instructions:</h3>
        <p>Use the trigger words: <strong>anime_style</strong>, <strong>detailed_character</strong></p>
        """
        
        formatted = preview_manager._format_text(html_content, width=60, indent=2)
        
        # Verify HTML tags are removed
        assert '<p>' not in formatted
        assert '<strong>' not in formatted
        assert '<ul>' not in formatted
        assert '<li>' not in formatted
        assert '<a href=' not in formatted
        assert '<span style=' not in formatted
        
        # Verify content is preserved
        assert 'comprehensive model' in formatted
        assert 'high-quality' in formatted
        assert 'anime characters' in formatted
        assert 'detailed features' in formatted
        assert 'Support for' in formatted and 'multiple art styles' in formatted
        assert 'SD 1.5' in formatted
        assert 'SDXL' in formatted
        assert '10,000+ images' in formatted
        assert 'anime_style' in formatted
        assert 'detailed_character' in formatted
        
        # Verify formatting
        lines = formatted.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                assert line.startswith('  ')  # 2-space indent
                assert len(line) <= 62  # 60 + 2 indent