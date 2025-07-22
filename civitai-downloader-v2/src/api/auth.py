#!/usr/bin/env python3
"""
Authentication Manager for CivitAI API.
Handles API key authentication, session management, and credential storage.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from ..core.config.env_loader import get_civitai_api_key
except ImportError:
    # Handle relative import issues
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config.env_loader import get_civitai_api_key


class AuthError(Exception):
    """Authentication-specific error."""
    
    def __init__(self, message: str, error_type: str = "UNKNOWN"):
        """
        Initialize authentication error.
        
        Args:
            message: Error message
            error_type: Type of authentication error
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class AuthManager:
    """Manages API authentication and session handling."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize authentication manager.
        
        Args:
            api_key: CivitAI API key (if None, will try to load from environment)
        """
        # Use provided API key or load from environment
        self.api_key = api_key or get_civitai_api_key()
        self.session = {}
        self._session_file = Path.home() / ".civitai" / "session.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self._session_file.parent.mkdir(parents=True, exist_ok=True)
    
    def validate_api_key(self) -> bool:
        """
        Validate API key format.
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.api_key or (isinstance(self.api_key, str) and self.api_key.strip() == ""):
            return False
        
        if isinstance(self.api_key, str):
            # CivitAI API keys are typically 32-character hexadecimal strings
            if len(self.api_key) == 32:
                # Check if it's a valid hexadecimal string
                try:
                    int(self.api_key, 16)
                    return True
                except ValueError:
                    pass
            # Also accept longer keys or keys with prefixes
            elif len(self.api_key) > 10:
                return True
        
        return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary of authentication headers
        """
        if not self.api_key:
            return {}
        
        return {
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def save_session(self, session_data: Dict[str, Any]) -> None:
        """
        Save session data to file.
        
        Args:
            session_data: Session data to save
        """
        self.session = session_data
        try:
            with open(self._session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
        except Exception:
            # Silently fail if can't save session
            pass
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load session data from file.
        
        Returns:
            Session data or None if not found/expired
        """
        if not self._session_file.exists():
            return None
        
        try:
            with open(self._session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session is expired
            if 'expires_at' in session_data:
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if datetime.now() > expires_at:
                    # Session expired
                    self._session_file.unlink()  # Delete expired session
                    return None
            
            self.session = session_data
            return session_data
            
        except Exception:
            return None
    
    def is_session_valid(self) -> bool:
        """
        Check if current session is valid.
        
        Returns:
            True if session is valid, False otherwise
        """
        if not self.session:
            self.load_session()
        
        if not self.session:
            return False
        
        if 'expires_at' in self.session:
            expires_at = datetime.fromisoformat(self.session['expires_at'])
            return datetime.now() < expires_at
        
        return True
    
    def should_refresh_session(self, session: Dict[str, Any]) -> bool:
        """
        Check if session should be refreshed.
        
        Args:
            session: Session data to check
            
        Returns:
            True if session needs refresh, False otherwise
        """
        if 'expires_at' not in session:
            return True
        
        expires_at = datetime.fromisoformat(session['expires_at'])
        # Refresh if less than 1 hour remaining
        return datetime.now() > (expires_at - timedelta(hours=1))
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        # Check API key first
        if self.validate_api_key():
            return True
        
        # Check session
        return self.is_session_valid()
    
    async def authenticate(self) -> bool:
        """
        Perform authentication.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.validate_api_key():
            return True
        
        # In real implementation, would perform actual auth
        return False
    
    async def ensure_authenticated(self) -> bool:
        """
        Ensure user is authenticated, re-authenticating if necessary.
        
        Returns:
            True if authenticated, False otherwise
        """
        if self.is_authenticated():
            return True
        
        # Try to re-authenticate
        return await self.authenticate()


class MultiAuthStrategy:
    """Manages multiple authentication strategies with fallback."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize multi-auth strategy.
        
        Args:
            api_key: Optional API key (if None, will try to load from environment)
        """
        # Use provided API key or load from environment
        self.api_key = api_key or get_civitai_api_key()
        self._auth_manager = AuthManager(self.api_key)
        self._web_auth = None  # Lazy load web auth
    
    def get_primary_auth_method(self) -> str:
        """
        Get primary authentication method.
        
        Returns:
            Primary auth method name
        """
        if self.api_key:
            return "api_key"
        return "web"
    
    async def authenticate_with_api_key(self) -> bool:
        """
        Authenticate using API key.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            raise Exception("No API key provided")
        
        return self._auth_manager.validate_api_key()
    
    async def authenticate_with_web(self) -> bool:
        """
        Authenticate using web method.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            NotImplementedError: Web authentication not yet implemented
        """
        # TODO: Implement actual web authentication using WebAuthManager
        # This is a placeholder that should be replaced with real implementation
        # For now, raise NotImplementedError to prevent security vulnerabilities
        raise NotImplementedError(
            "Web authentication is not yet implemented. "
            "Please use API key authentication or implement web auth logic."
        )
    
    async def authenticate(self) -> bool:
        """
        Authenticate using available methods with fallback.
        
        Returns:
            True if any method succeeds, False otherwise
        """
        # Try primary method first
        if self.get_primary_auth_method() == "api_key":
            try:
                return await self.authenticate_with_api_key()
            except Exception:
                # Fall back to web auth
                pass
        
        # Try web authentication (will raise NotImplementedError for now)
        try:
            return await self.authenticate_with_web()
        except NotImplementedError:
            # Web authentication not implemented yet, use API key as fallback
            return False


class CredentialStore:
    """Secure credential storage."""
    
    def __init__(self):
        """Initialize credential store."""
        self._cred_file = Path.home() / ".civitai" / "credentials.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self._cred_file.parent.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Save credentials securely.
        
        Args:
            credentials: Credentials to save
        """
        # In real implementation, would encrypt credentials
        # For now, just obfuscate sensitive data
        safe_creds = {}
        for key, value in credentials.items():
            if key in ['api_key', 'password'] and value:
                # Simple obfuscation (not secure, just for testing)
                safe_creds[key] = '*' * len(str(value))
            else:
                safe_creds[key] = value
        
        try:
            with open(self._cred_file, 'w') as f:
                json.dump(safe_creds, f, indent=2)
        except Exception:
            pass
    
    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Load saved credentials.
        
        Returns:
            Credentials or None if not found
        """
        if not self._cred_file.exists():
            return None
        
        try:
            with open(self._cred_file, 'r') as f:
                creds = json.load(f)
            
            # Return credentials (in real impl would decrypt)
            return creds
        except Exception:
            return None
    
    def delete_credentials(self) -> None:
        """Delete stored credentials."""
        if self._cred_file.exists():
            self._cred_file.unlink()
    
    def _get_raw_storage(self) -> Optional[str]:
        """
        Get raw storage content for testing.
        
        Returns:
            Raw file content or None
        """
        if self._cred_file.exists():
            return self._cred_file.read_text()
        return None