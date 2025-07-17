"""Unit tests for CivitAI API client."""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
import json

from src.api.client import CivitAIClient
from src.api.exceptions import (
    APIError, NetworkError, RateLimitError, AuthenticationError
)
from src.api.models import SearchResponse, ModelDetails


class TestCivitAIClient:
    """Test cases for CivitAI API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = CivitAIClient(api_key="test_key", calls_per_second=10)  # Fast for testing
    
    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = CivitAIClient()
            assert client.api_key is None
            assert "Authorization" not in client.session.headers
    
    def test_init_with_env_api_key(self):
        """Test client initialization with environment variable API key."""
        with patch.dict('os.environ', {'CIVITAI_API_KEY': 'env_key'}):
            client = CivitAIClient()
            assert client.api_key == "env_key"
    
    def test_rate_limiting_applied(self):
        """Test that rate limiting is applied to requests."""
        with patch.object(self.client.rate_limiter, 'wait_if_needed') as mock_wait:
            with patch.object(self.client.session, 'request') as mock_request:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.encoding = None
                mock_response.json.return_value = {"items": [], "metadata": {}}
                mock_request.return_value = mock_response
                
                self.client.search_models()
                
                mock_wait.assert_called_once()
    
    def test_authentication_error_handling(self):
        """Test handling of authentication errors."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_request.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                self.client.search_models()
    
    def test_rate_limit_error_handling(self):
        """Test handling of rate limit errors."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_request.return_value = mock_response
            
            with pytest.raises(RateLimitError):
                self.client.search_models()
    
    def test_network_error_handling(self):
        """Test handling of network errors."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(NetworkError):
                self.client.search_models()
    
    def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Request timeout")
            
            with pytest.raises(NetworkError):
                self.client.search_models()
    
    def test_api_error_handling(self):
        """Test handling of general API errors."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            mock_request.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                self.client.search_models()
            
            assert exc_info.value.status_code == 500
    
    def test_json_parsing_error(self):
        """Test handling of invalid JSON responses."""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.encoding = None
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_request.return_value = mock_response
            
            with pytest.raises(APIError):
                self.client.search_models()
    
    def test_get_model(self):
        """Test getting model details."""
        mock_response_data = {
            "id": 123,
            "name": "Test Model",
            "type": "Checkpoint",
            "description": "A test model",
            "stats": {"downloadCount": 100},
            "tags": [{"name": "anime"}],
            "creator": {"username": "test_user"},
            "modelVersions": [
                {
                    "id": 456,
                    "name": "v1.0",
                    "baseModel": "SD 1.5",
                    "files": [
                        {
                            "id": 789,
                            "name": "model.safetensors",
                            "type": "Model",
                            "downloadUrl": "https://example.com/download",
                            "sizeKB": 4000000
                        }
                    ],
                    "images": []
                }
            ],
            "images": []
        }
        
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.encoding = None
            mock_response.json.return_value = mock_response_data
            mock_request.return_value = mock_response
            
            result = self.client.get_model(123)
            
            assert isinstance(result, ModelDetails)
            assert result.id == "123"
            assert result.name == "Test Model"
            assert result.type == "Checkpoint"
            assert len(result.versions) == 1
            assert result.versions[0].base_model == "SD 1.5"
    
    def test_download_file_progress(self):
        """Test file download with progress tracking."""
        test_content = b"test file content"
        
        with patch.object(self.client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.headers = {'content-length': str(len(test_content))}
            mock_response.iter_content.return_value = [test_content[:8], test_content[8:]]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                progress_data = list(self.client.download_file(
                    "https://example.com/file", 
                    "/tmp/test_file"
                ))
                
                assert len(progress_data) == 2
                assert progress_data[0]['downloaded'] == 8
                assert progress_data[1]['downloaded'] == len(test_content)
                assert progress_data[1]['percentage'] == 100.0
    
    def test_rate_limiter_stats(self):
        """Test getting rate limiter statistics."""
        stats = self.client.get_rate_limiter_stats()
        
        assert isinstance(stats, dict)
        assert 'calls_made' in stats
        assert 'elapsed_time' in stats
        assert 'average_rate' in stats
        assert 'configured_rate' in stats


class TestRateLimiter:
    """Test cases for rate limiter."""
    
    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        from src.api.rate_limiter import RateLimiter
        
        limiter = RateLimiter(calls_per_second=2.0)
        assert limiter.min_interval == 0.5
        assert limiter.calls_made == 0
    
    def test_rate_limiter_wait(self):
        """Test rate limiter wait functionality."""
        from src.api.rate_limiter import RateLimiter
        import time
        
        limiter = RateLimiter(calls_per_second=10.0)  # Fast for testing
        
        start_time = time.time()
        limiter.wait_if_needed(verbose=False)
        limiter.wait_if_needed(verbose=False)
        end_time = time.time()
        
        # Should have waited at least the minimum interval
        assert end_time - start_time >= limiter.min_interval
        assert limiter.calls_made == 2
    
    def test_rate_limiter_reset(self):
        """Test rate limiter reset functionality."""
        from src.api.rate_limiter import RateLimiter
        
        limiter = RateLimiter(calls_per_second=10.0)
        limiter.wait_if_needed(verbose=False)
        
        assert limiter.calls_made == 1
        
        limiter.reset()
        
        assert limiter.calls_made == 0
        assert limiter.last_call == 0.0