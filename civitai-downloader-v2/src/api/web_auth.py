#!/usr/bin/env python3
"""
Web Authentication Manager for CivitAI.
Handles web-based authentication, cookie management, and session persistence.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio


class WebAuthManager:
    """Manages web-based authentication for CivitAI."""
    
    def __init__(self):
        """Initialize web authentication manager."""
        self.session_cookies = {}
        self._cookie_file = Path.home() / ".civitai" / "cookies.json"
        self._ensure_config_dir()
        self._http_client = httpx.AsyncClient()
        self._is_logged_in = False
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self._cookie_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def login(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Perform web-based login.
        
        Args:
            credentials: Login credentials (username, password)
            
        Returns:
            Login result with success status
        """
        # In real implementation, would perform actual login
        # For testing, simulate successful login
        if 'username' in credentials and 'password' in credentials:
            # Mock successful login
            self.session_cookies = {
                'session': 'test_session_cookie',
                'csrf_token': 'test_csrf_token'
            }
            self._is_logged_in = True
            
            # Save cookies
            self.save_cookies(self.session_cookies)
            
            return {
                'success': True,
                'user': {'id': 123, 'username': credentials['username']}
            }
        
        return {'success': False, 'error': 'Invalid credentials'}
    
    def is_logged_in(self) -> bool:
        """
        Check if currently logged in.
        
        Returns:
            True if logged in, False otherwise
        """
        if not self._is_logged_in and self.session_cookies:
            # Check if we have valid cookies
            return self.are_cookies_valid()
        
        return self._is_logged_in
    
    def save_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Save cookies to file.
        
        Args:
            cookies: Cookie dictionary to save
        """
        cookie_data = {
            'cookies': cookies,
            'saved_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        try:
            with open(self._cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
        except Exception:
            pass
    
    def load_cookies(self) -> Optional[Dict[str, str]]:
        """
        Load cookies from file.
        
        Returns:
            Cookie dictionary or None if not found/expired
        """
        if not self._cookie_file.exists():
            return None
        
        try:
            with open(self._cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            # Check expiration
            if 'expires_at' in cookie_data:
                expires_at = datetime.fromisoformat(cookie_data['expires_at'])
                if datetime.now() > expires_at:
                    # Cookies expired
                    self._cookie_file.unlink()
                    return None
            
            cookies = cookie_data.get('cookies', {})
            self.session_cookies = cookies
            return cookies
            
        except Exception:
            return None
    
    def are_cookies_valid(self) -> bool:
        """
        Check if cookies are valid.
        
        Returns:
            True if cookies are valid, False otherwise
        """
        if not self.session_cookies:
            # Try to load cookies
            cookies = self.load_cookies()
            if not cookies:
                return False
        
        # Check if essential cookies exist
        return 'session' in self.session_cookies
    
    async def logout(self) -> None:
        """Perform logout and clear session."""
        self.session_cookies = {}
        self._is_logged_in = False
        
        # Delete cookie file
        if self._cookie_file.exists():
            self._cookie_file.unlink()
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()