#!/usr/bin/env python3
"""
Authentication system tests.
Tests for API key management, session handling, and web authentication.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import importlib.util
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestAuthentication:
    """Test authentication and authorization functionality."""
    
    @property
    def api_dir(self) -> Path:
        """Get the API directory."""
        return Path(__file__).parent.parent.parent / "src" / "api"
    
    def test_auth_manager_initialization(self):
        """Test AuthManager proper initialization with API key."""
        # Import auth manager
        auth_path = self.api_dir / "auth.py"
        assert auth_path.exists(), "auth.py must exist"
        
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        # Test AuthManager class exists
        assert hasattr(auth_module, 'AuthManager'), "AuthManager class must exist"
        AuthManager = auth_module.AuthManager
        
        # Test initialization with API key
        api_key = "test_api_key_123"
        auth_manager = AuthManager(api_key=api_key)
        
        # Validate properties
        assert hasattr(auth_manager, 'api_key'), "AuthManager must have api_key"
        assert hasattr(auth_manager, 'session'), "AuthManager must have session"
        assert hasattr(auth_manager, 'is_authenticated'), "AuthManager must have is_authenticated method"
        assert auth_manager.api_key == api_key, "API key should be stored correctly"
    
    def test_api_key_validation(self):
        """Test API key validation and format checking."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        AuthManager = auth_module.AuthManager
        
        # Test valid API key
        valid_key = "civitai_1234567890abcdef"
        auth_manager = AuthManager(api_key=valid_key)
        assert auth_manager.validate_api_key(), "Valid API key should pass validation"
        
        # Test invalid API key formats
        invalid_keys = [
            "",  # Empty key
            None,  # None key
            "short",  # Too short
            "no_prefix_1234567890",  # Missing prefix
            "wrong_prefix_1234567890"  # Wrong prefix
        ]
        
        for invalid_key in invalid_keys:
            auth_manager = AuthManager(api_key=invalid_key)
            assert not auth_manager.validate_api_key(), f"Invalid key '{invalid_key}' should fail validation"
    
    @pytest.mark.asyncio
    async def test_api_authentication_headers(self):
        """Test that authentication headers are properly set."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        AuthManager = auth_module.AuthManager
        
        api_key = "civitai_test_key_123"
        auth_manager = AuthManager(api_key=api_key)
        
        # Get authentication headers
        headers = auth_manager.get_auth_headers()
        
        assert isinstance(headers, dict), "Headers must be a dictionary"
        assert 'Authorization' in headers, "Authorization header must be present"
        assert headers['Authorization'] == f'Bearer {api_key}', "Bearer token format must be correct"
    
    @pytest.mark.asyncio
    async def test_session_persistence(self):
        """Test session persistence and restoration."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        AuthManager = auth_module.AuthManager
        
        auth_manager = AuthManager(api_key="test_key")
        
        # Create test session data
        test_session = {
            'session_id': 'test_session_123',
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
            'user_data': {'id': 123, 'username': 'testuser'}
        }
        
        # Test session storage
        auth_manager.save_session(test_session)
        
        # Test session restoration
        restored_session = auth_manager.load_session()
        assert restored_session is not None, "Session should be restored"
        assert restored_session['session_id'] == test_session['session_id'], "Session ID should match"
        assert 'expires_at' in restored_session, "Session should have expiration"
        assert 'user_data' in restored_session, "Session should have user data"
    
    @pytest.mark.asyncio
    async def test_session_expiration_handling(self):
        """Test handling of expired sessions."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        AuthManager = auth_module.AuthManager
        
        auth_manager = AuthManager(api_key="test_key")
        
        # Create expired session
        expired_session = {
            'session_id': 'expired_session_123',
            'expires_at': (datetime.now() - timedelta(hours=1)).isoformat(),
            'user_data': {'id': 123}
        }
        
        auth_manager.save_session(expired_session)
        
        # Check if session is considered expired
        assert not auth_manager.is_session_valid(), "Expired session should be invalid"
        
        # Load expired session should return None or trigger refresh
        session = auth_manager.load_session()
        if session:
            assert auth_manager.should_refresh_session(session), "Should indicate session needs refresh"
    
    def test_web_auth_manager_initialization(self):
        """Test WebAuthManager for web scraping authentication."""
        # Import web auth manager
        web_auth_path = self.api_dir / "web_auth.py"
        assert web_auth_path.exists(), "web_auth.py must exist"
        
        spec = importlib.util.spec_from_file_location("web_auth", web_auth_path)
        web_auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_auth_module)
        
        # Test WebAuthManager class exists
        assert hasattr(web_auth_module, 'WebAuthManager'), "WebAuthManager class must exist"
        WebAuthManager = web_auth_module.WebAuthManager
        
        # Test initialization
        web_auth = WebAuthManager()
        
        # Validate properties
        assert hasattr(web_auth, 'session_cookies'), "WebAuthManager must manage cookies"
        assert hasattr(web_auth, 'login'), "WebAuthManager must have login method"
        assert hasattr(web_auth, 'is_logged_in'), "WebAuthManager must have is_logged_in method"
    
    @pytest.mark.asyncio
    async def test_web_login_flow(self):
        """Test web-based login flow with credentials."""
        web_auth_path = self.api_dir / "web_auth.py"
        spec = importlib.util.spec_from_file_location("web_auth", web_auth_path)
        web_auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_auth_module)
        
        WebAuthManager = web_auth_module.WebAuthManager
        
        web_auth = WebAuthManager()
        
        # Mock the HTTP client for login
        with patch.object(web_auth, '_http_client') as mock_http:
            # Mock successful login response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.cookies = {'session': 'test_session_cookie'}
            mock_response.json.return_value = {'success': True, 'user': {'id': 123}}
            mock_http.post = AsyncMock(return_value=mock_response)
            
            # Test login
            credentials = {'username': 'testuser', 'password': 'testpass'}
            result = await web_auth.login(credentials)
            
            assert result['success'] is True, "Login should succeed"
            assert web_auth.is_logged_in(), "Should be logged in after successful login"
            assert len(web_auth.session_cookies) > 0, "Should have session cookies"
    
    @pytest.mark.asyncio
    async def test_web_auth_cookie_management(self):
        """Test cookie storage and retrieval for web authentication."""
        web_auth_path = self.api_dir / "web_auth.py"
        spec = importlib.util.spec_from_file_location("web_auth", web_auth_path)
        web_auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_auth_module)
        
        WebAuthManager = web_auth_module.WebAuthManager
        
        web_auth = WebAuthManager()
        
        # Test cookie storage
        test_cookies = {
            'session': 'session_value_123',
            'csrf_token': 'csrf_token_456',
            'user_id': '789'
        }
        
        web_auth.save_cookies(test_cookies)
        
        # Test cookie retrieval
        retrieved_cookies = web_auth.load_cookies()
        assert retrieved_cookies is not None, "Cookies should be retrieved"
        assert 'session' in retrieved_cookies, "Session cookie should be present"
        assert retrieved_cookies['session'] == test_cookies['session'], "Session cookie should match"
        
        # Test cookie expiration check
        assert web_auth.are_cookies_valid(), "Fresh cookies should be valid"
    
    @pytest.mark.asyncio
    async def test_automatic_reauthentication(self):
        """Test automatic re-authentication when session expires."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        AuthManager = auth_module.AuthManager
        
        auth_manager = AuthManager(api_key="test_key")
        
        # Mock authentication check
        with patch.object(auth_manager, 'is_authenticated') as mock_auth:
            mock_auth.return_value = False  # Not authenticated
            
            with patch.object(auth_manager, 'authenticate') as mock_authenticate:
                mock_authenticate.return_value = True  # Successful re-auth
                
                # Test automatic re-authentication
                result = await auth_manager.ensure_authenticated()
                
                assert result is True, "Should successfully re-authenticate"
                mock_authenticate.assert_called_once()
    
    def test_auth_error_handling(self):
        """Test authentication error handling and recovery."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        # Test AuthError class exists
        assert hasattr(auth_module, 'AuthError'), "AuthError class must exist"
        AuthError = auth_module.AuthError
        
        # Test different auth error types
        errors = [
            AuthError("Invalid API key", error_type="INVALID_KEY"),
            AuthError("Session expired", error_type="SESSION_EXPIRED"),
            AuthError("Rate limited", error_type="RATE_LIMITED"),
            AuthError("Network error", error_type="NETWORK_ERROR")
        ]
        
        for error in errors:
            assert hasattr(error, 'error_type'), "AuthError must have error_type"
            assert hasattr(error, 'message'), "AuthError must have message"
            assert error.error_type in ["INVALID_KEY", "SESSION_EXPIRED", "RATE_LIMITED", "NETWORK_ERROR"], \
                "Error type must be valid"
    
    @pytest.mark.asyncio
    async def test_multi_auth_strategy(self):
        """Test fallback between API key and web authentication."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        # Test MultiAuthStrategy class exists
        assert hasattr(auth_module, 'MultiAuthStrategy'), "MultiAuthStrategy class must exist"
        MultiAuthStrategy = auth_module.MultiAuthStrategy
        
        # Initialize with API key
        multi_auth = MultiAuthStrategy(api_key="test_key")
        
        # Test primary authentication (API key)
        assert multi_auth.get_primary_auth_method() == "api_key", "Primary should be API key"
        
        # Mock API key failure
        with patch.object(multi_auth, 'authenticate_with_api_key') as mock_api_auth:
            mock_api_auth.side_effect = Exception("API key invalid")
            
            # Mock web auth success
            with patch.object(multi_auth, 'authenticate_with_web') as mock_web_auth:
                mock_web_auth.return_value = True
                
                # Test fallback to web auth
                result = await multi_auth.authenticate()
                
                assert result is True, "Should succeed with web auth fallback"
                mock_api_auth.assert_called_once()
                mock_web_auth.assert_called_once()
    
    def test_secure_credential_storage(self):
        """Test secure storage of credentials."""
        auth_path = self.api_dir / "auth.py"
        spec = importlib.util.spec_from_file_location("auth", auth_path)
        auth_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_module)
        
        # Test CredentialStore class exists
        assert hasattr(auth_module, 'CredentialStore'), "CredentialStore class must exist"
        CredentialStore = auth_module.CredentialStore
        
        store = CredentialStore()
        
        # Test secure storage
        test_credentials = {
            'api_key': 'civitai_secret_key_123',
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Store credentials
        store.save_credentials(test_credentials)
        
        # Verify credentials are not stored in plain text
        stored_data = store._get_raw_storage()
        if stored_data:
            assert 'civitai_secret_key_123' not in str(stored_data), "API key should not be in plain text"
            assert 'testpass123' not in str(stored_data), "Password should not be in plain text"
        
        # Test retrieval
        retrieved = store.load_credentials()
        assert retrieved is not None, "Should retrieve credentials"
        assert 'api_key' in retrieved, "Should have API key"
        
        # Test credential deletion
        store.delete_credentials()
        assert store.load_credentials() is None, "Credentials should be deleted"