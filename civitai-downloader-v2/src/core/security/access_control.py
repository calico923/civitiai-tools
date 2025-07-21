#!/usr/bin/env python3
"""
Access Control and Authorization System.
Implements requirement 18.4: Role-based access control and security policies.
"""

import logging
import time
import sqlite3
import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import functools
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions."""
    # File operations
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    EXECUTE_FILE = "execute_file"
    
    # Model operations
    SEARCH_MODELS = "search_models"
    DOWNLOAD_MODEL = "download_model"
    DELETE_MODEL = "delete_model"
    
    # System operations
    VIEW_LOGS = "view_logs"
    MODIFY_CONFIG = "modify_config"
    MANAGE_USERS = "manage_users"
    SYSTEM_ADMIN = "system_admin"
    
    # Security operations
    VIEW_SECURITY_LOGS = "view_security_logs"
    MANAGE_SECURITY = "manage_security"
    AUDIT_ACCESS = "audit_access"
    
    # Export operations
    EXPORT_DATA = "export_data"
    IMPORT_DATA = "import_data"


class Role(Enum):
    """System roles."""
    GUEST = "guest"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"
    SECURITY_ADMIN = "security_admin"
    SYSTEM = "system"


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    name: str
    description: str
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 60
    password_min_length: int = 8
    require_2fa: bool = False
    allowed_ip_ranges: List[str] = field(default_factory=list)
    blocked_ip_ranges: List[str] = field(default_factory=list)
    rate_limit_requests_per_minute: int = 60
    audit_all_access: bool = True
    enforce_https: bool = True
    
    # File access restrictions
    max_file_size_mb: int = 1000
    allowed_file_extensions: Set[str] = field(default_factory=lambda: {'.safetensors', '.ckpt', '.pt'})
    blocked_file_extensions: Set[str] = field(default_factory=lambda: {'.exe', '.bat', '.sh'})
    
    # Resource limits
    max_concurrent_downloads: int = 3
    max_disk_usage_mb: int = 10000
    max_memory_usage_mb: int = 2000


@dataclass
class AccessRequest:
    """Access request information."""
    user_id: str
    resource: str
    action: Permission
    timestamp: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessResult:
    """Result of access control check."""
    granted: bool
    reason: str
    user_id: str
    resource: str
    action: Permission
    timestamp: float
    policy_violations: List[str] = field(default_factory=list)
    risk_score: int = 0  # 0-100


class AccessController:
    """
    Role-based access control system.
    Implements requirement 18.4: Comprehensive access control with policies.
    """
    
    def __init__(self, data_dir: Path, policy: SecurityPolicy):
        """
        Initialize access controller.
        
        Args:
            data_dir: Data directory for access control database
            policy: Security policy to enforce
        """
        self.data_dir = data_dir
        self.policy = policy
        self.access_db = data_dir / "access_control.db"
        
        # Role permissions mapping
        self.role_permissions = {
            Role.GUEST: {
                Permission.SEARCH_MODELS
            },
            Role.USER: {
                Permission.SEARCH_MODELS,
                Permission.DOWNLOAD_MODEL,
                Permission.READ_FILE,
                Permission.EXPORT_DATA
            },
            Role.POWER_USER: {
                Permission.SEARCH_MODELS,
                Permission.DOWNLOAD_MODEL,
                Permission.DELETE_MODEL,
                Permission.READ_FILE,
                Permission.WRITE_FILE,
                Permission.EXPORT_DATA,
                Permission.IMPORT_DATA,
                Permission.VIEW_LOGS
            },
            Role.ADMIN: {
                Permission.SEARCH_MODELS,
                Permission.DOWNLOAD_MODEL,
                Permission.DELETE_MODEL,
                Permission.READ_FILE,
                Permission.WRITE_FILE,
                Permission.DELETE_FILE,
                Permission.EXPORT_DATA,
                Permission.IMPORT_DATA,
                Permission.VIEW_LOGS,
                Permission.MODIFY_CONFIG,
                Permission.MANAGE_USERS
            },
            Role.SECURITY_ADMIN: {
                Permission.VIEW_SECURITY_LOGS,
                Permission.MANAGE_SECURITY,
                Permission.AUDIT_ACCESS,
                Permission.SYSTEM_ADMIN,
                Permission.VIEW_LOGS,
                Permission.MANAGE_USERS
            },
            Role.SYSTEM: set(Permission)  # System role has all permissions
        }
        
        # Active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Failed login attempts
        self.failed_attempts: Dict[str, List[float]] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}
        
        # Initialize database
        self._initialize_access_db()
        
        # Load users and permissions
        self._load_system_data()
    
    def _initialize_access_db(self) -> None:
        """Initialize access control database."""
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        last_login REAL,
                        failed_attempts INTEGER DEFAULT 0,
                        locked_until REAL,
                        active BOOLEAN DEFAULT TRUE,
                        metadata TEXT
                    )
                """)
                
                # Sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        last_activity REAL DEFAULT (strftime('%s', 'now')),
                        ip_address TEXT,
                        user_agent TEXT,
                        active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Access log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        resource TEXT NOT NULL,
                        action TEXT NOT NULL,
                        granted BOOLEAN NOT NULL,
                        reason TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        risk_score INTEGER DEFAULT 0,
                        timestamp REAL DEFAULT (strftime('%s', 'now')),
                        context TEXT
                    )
                """)
                
                # Permissions table (for custom permissions)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS custom_permissions (
                        user_id TEXT NOT NULL,
                        permission TEXT NOT NULL,
                        resource_pattern TEXT,
                        granted_by TEXT,
                        granted_at REAL DEFAULT (strftime('%s', 'now')),
                        expires_at REAL,
                        PRIMARY KEY (user_id, permission, resource_pattern),
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Security events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        user_id TEXT,
                        ip_address TEXT,
                        description TEXT,
                        details TEXT,
                        timestamp REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_user ON access_log(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_timestamp ON access_log(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize access control database: {e}")
    
    def _load_system_data(self) -> None:
        """Load users and permissions from database."""
        # Create default admin user if no users exist
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    self._create_default_admin()
                    
        except Exception as e:
            logger.error(f"Failed to load system data: {e}")
    
    def _create_default_admin(self) -> None:
        """Create default admin user."""
        import secrets
        
        # Generate random password for admin
        admin_password = secrets.token_urlsafe(16)
        
        # Create admin user
        self.create_user("admin", admin_password, Role.ADMIN)
        
        logger.warning(f"Created default admin user with password: {admin_password}")
        logger.warning("Please change the admin password immediately!")
    
    def create_user(self, username: str, password: str, role: Role) -> bool:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Password
            role: User role
            
        Returns:
            True if user created successfully
        """
        try:
            # Generate salt and hash password
            salt = secrets.token_bytes(32)
            password_hash = self._hash_password(password, salt)
            
            user_id = f"user_{int(time.time())}_{username}"
            
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username, password_hash, salt, role)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, password_hash, salt.hex(), role.value))
                conn.commit()
            
            logger.info(f"Created user: {username} with role: {role.value}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"User already exists: {username}")
            return False
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: Optional[str] = None) -> Optional[str]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username
            password: Password
            ip_address: User IP address
            
        Returns:
            Session ID if authentication successful, None otherwise
        """
        current_time = time.time()
        
        # Check rate limiting
        if not self._check_rate_limit(username, ip_address):
            self._log_security_event("rate_limit_exceeded", "warning", 
                                   username, ip_address, "Authentication rate limit exceeded")
            return None
        
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, password_hash, salt, role, failed_attempts, locked_until, active
                    FROM users WHERE username = ?
                """, (username,))
                
                result = cursor.fetchone()
                if not result:
                    self._record_failed_attempt(username, ip_address, "user_not_found")
                    return None
                
                user_id, stored_hash, salt_hex, role, failed_attempts, locked_until, active = result
                
                # Check if user is active
                if not active:
                    self._log_security_event("inactive_user_login", "warning",
                                           user_id, ip_address, "Inactive user attempted login")
                    return None
                
                # Check if user is locked
                if locked_until and current_time < locked_until:
                    remaining = int(locked_until - current_time)
                    self._log_security_event("locked_user_login", "warning",
                                           user_id, ip_address, f"Locked user attempted login ({remaining}s remaining)")
                    return None
                
                # Verify password
                salt = bytes.fromhex(salt_hex)
                expected_hash = self._hash_password(password, salt)
                
                if not secrets.compare_digest(stored_hash, expected_hash):
                    self._record_failed_attempt(username, ip_address, "invalid_password")
                    return None
                
                # Authentication successful - reset failed attempts
                cursor.execute("""
                    UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ?
                    WHERE user_id = ?
                """, (current_time, user_id))
                
                # Create session
                session_id = self._create_session(user_id, ip_address)
                
                self._log_security_event("login_success", "info", user_id, ip_address,
                                       f"User {username} logged in successfully")
                
                conn.commit()
                return session_id
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def check_access(self, session_id: str, resource: str, action: Permission,
                    ip_address: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> AccessResult:
        """
        Check if user has access to perform action on resource.
        
        Args:
            session_id: User session ID
            resource: Resource being accessed
            action: Action being performed
            ip_address: User IP address
            context: Additional context
            
        Returns:
            AccessResult with decision
        """
        current_time = time.time()
        context = context or {}
        
        # Get user information from session
        user_info = self._get_session_user(session_id)
        if not user_info:
            result = AccessResult(
                granted=False,
                reason="Invalid session",
                user_id="unknown",
                resource=resource,
                action=action,
                timestamp=current_time
            )
            self._log_access(result, ip_address)
            return result
        
        user_id = user_info['user_id']
        role = Role(user_info['role'])
        
        # Check session validity
        if not self._is_session_valid(session_id):
            result = AccessResult(
                granted=False,
                reason="Session expired",
                user_id=user_id,
                resource=resource,
                action=action,
                timestamp=current_time
            )
            self._log_access(result, ip_address)
            return result
        
        # Check basic permission
        has_permission = self._check_role_permission(role, action)
        
        # Check custom permissions
        if not has_permission:
            has_permission = self._check_custom_permission(user_id, action, resource)
        
        # Apply security policy checks
        policy_violations = []
        risk_score = 0
        
        if has_permission:
            # Check IP restrictions
            if not self._check_ip_restrictions(ip_address):
                has_permission = False
                policy_violations.append("IP address not allowed")
                risk_score += 30
            
            # Check file restrictions for file operations
            if action in [Permission.READ_FILE, Permission.WRITE_FILE, Permission.DELETE_FILE]:
                if not self._check_file_restrictions(resource):
                    has_permission = False
                    policy_violations.append("File type not allowed")
                    risk_score += 20
            
            # Check resource limits
            if not self._check_resource_limits(user_id, action, context):
                has_permission = False
                policy_violations.append("Resource limits exceeded")
                risk_score += 15
            
            # Calculate risk score based on various factors
            risk_score += self._calculate_risk_score(user_id, action, resource, ip_address, context)
        
        # Create result
        reason = "Access granted" if has_permission else "Access denied"
        if policy_violations:
            reason += f" - {', '.join(policy_violations)}"
        
        result = AccessResult(
            granted=has_permission,
            reason=reason,
            user_id=user_id,
            resource=resource,
            action=action,
            timestamp=current_time,
            policy_violations=policy_violations,
            risk_score=risk_score
        )
        
        # Log access attempt
        self._log_access(result, ip_address, context)
        
        # Update session activity
        self._update_session_activity(session_id)
        
        return result
    
    def _check_role_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has permission."""
        return permission in self.role_permissions.get(role, set())
    
    def _check_custom_permission(self, user_id: str, permission: Permission, resource: str) -> bool:
        """Check custom user permissions."""
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM custom_permissions 
                    WHERE user_id = ? AND permission = ? 
                    AND (resource_pattern IS NULL OR ? LIKE resource_pattern)
                    AND (expires_at IS NULL OR expires_at > ?)
                """, (user_id, permission.value, resource, time.time()))
                
                return cursor.fetchone()[0] > 0
                
        except Exception as e:
            logger.error(f"Error checking custom permissions: {e}")
            return False
    
    def _check_ip_restrictions(self, ip_address: Optional[str]) -> bool:
        """Check IP address restrictions."""
        if not ip_address:
            return True
        
        import ipaddress
        
        try:
            user_ip = ipaddress.ip_address(ip_address)
            
            # Check blocked ranges
            for blocked_range in self.policy.blocked_ip_ranges:
                if user_ip in ipaddress.ip_network(blocked_range, strict=False):
                    return False
            
            # Check allowed ranges (if specified)
            if self.policy.allowed_ip_ranges:
                for allowed_range in self.policy.allowed_ip_ranges:
                    if user_ip in ipaddress.ip_network(allowed_range, strict=False):
                        return True
                return False  # IP not in allowed ranges
            
            return True  # No restrictions
            
        except Exception as e:
            logger.warning(f"IP address validation error: {e}")
            return False
    
    def _check_file_restrictions(self, resource: str) -> bool:
        """Check file type restrictions."""
        resource_path = Path(resource)
        extension = resource_path.suffix.lower()
        
        # Check blocked extensions
        if extension in self.policy.blocked_file_extensions:
            return False
        
        # Check allowed extensions (if specified)
        if self.policy.allowed_file_extensions:
            return extension in self.policy.allowed_file_extensions
        
        return True
    
    def _check_resource_limits(self, user_id: str, action: Permission, 
                              context: Dict[str, Any]) -> bool:
        """Check resource usage limits."""
        # Check concurrent downloads
        if action == Permission.DOWNLOAD_MODEL:
            active_downloads = self._count_active_downloads(user_id)
            if active_downloads >= self.policy.max_concurrent_downloads:
                return False
        
        # Check file size limits
        file_size = context.get('file_size_mb', 0)
        if file_size > self.policy.max_file_size_mb:
            return False
        
        # Check disk usage
        current_usage = self._get_user_disk_usage(user_id)
        if current_usage > self.policy.max_disk_usage_mb:
            return False
        
        return True
    
    def _calculate_risk_score(self, user_id: str, action: Permission, resource: str,
                            ip_address: Optional[str], context: Dict[str, Any]) -> int:
        """Calculate risk score for access attempt."""
        risk = 0
        
        # High-risk actions
        if action in [Permission.DELETE_FILE, Permission.SYSTEM_ADMIN, Permission.MANAGE_USERS]:
            risk += 25
        
        # Unusual IP address
        if ip_address and not self._is_known_ip(user_id, ip_address):
            risk += 15
        
        # Off-hours access
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Outside 6 AM - 10 PM
            risk += 10
        
        # Large file operations
        file_size = context.get('file_size_mb', 0)
        if file_size > 100:
            risk += 10
        
        # Rapid successive requests
        if self._detect_rapid_requests(user_id):
            risk += 20
        
        return min(risk, 100)  # Cap at 100
    
    def _hash_password(self, password: str, salt: bytes) -> str:
        """Hash password with salt."""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()
    
    def _check_rate_limit(self, identifier: str, ip_address: Optional[str]) -> bool:
        """Check rate limiting for user or IP."""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Check user-based rate limit
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Clean old entries
        self.rate_limits[identifier] = [
            timestamp for timestamp in self.rate_limits[identifier]
            if timestamp > window_start
        ]
        
        # Check limit
        if len(self.rate_limits[identifier]) >= self.policy.rate_limit_requests_per_minute:
            return False
        
        # Add current request
        self.rate_limits[identifier].append(current_time)
        
        return True
    
    def _record_failed_attempt(self, username: str, ip_address: Optional[str], reason: str) -> None:
        """Record failed login attempt."""
        current_time = time.time()
        
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                
                # Update user failed attempts
                cursor.execute("""
                    UPDATE users SET failed_attempts = failed_attempts + 1
                    WHERE username = ?
                """, (username,))
                
                # Check if user should be locked
                cursor.execute("""
                    SELECT user_id, failed_attempts FROM users WHERE username = ?
                """, (username,))
                
                result = cursor.fetchone()
                if result:
                    user_id, failed_attempts = result
                    
                    if failed_attempts >= self.policy.max_login_attempts:
                        lockout_until = current_time + (self.policy.lockout_duration_minutes * 60)
                        cursor.execute("""
                            UPDATE users SET locked_until = ? WHERE user_id = ?
                        """, (lockout_until, user_id))
                        
                        self._log_security_event("user_locked", "critical", user_id, ip_address,
                                               f"User locked after {failed_attempts} failed attempts")
                    
                    self._log_security_event("login_failed", "warning", user_id, ip_address,
                                           f"Login failed: {reason}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error recording failed attempt: {e}")
    
    def _create_session(self, user_id: str, ip_address: Optional[str]) -> str:
        """Create user session."""
        import secrets
        
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()
        
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_sessions (session_id, user_id, ip_address)
                    VALUES (?, ?, ?)
                """, (session_id, user_id, ip_address))
                conn.commit()
            
            # Store in memory for quick access
            self.active_sessions[session_id] = {
                'user_id': user_id,
                'created_at': current_time,
                'last_activity': current_time,
                'ip_address': ip_address
            }
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    def _get_session_user(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user info from session."""
        # Check memory cache first
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            user_id = session_data['user_id']
            
            # Get user role from database
            try:
                with sqlite3.connect(self.access_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT role, active FROM users WHERE user_id = ?
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    if result and result[1]:  # User is active
                        return {
                            'user_id': user_id,
                            'role': result[0],
                            'session_data': session_data
                        }
            except Exception as e:
                logger.error(f"Error getting user from session: {e}")
        
        return None
    
    def _is_session_valid(self, session_id: str) -> bool:
        """Check if session is valid and not expired."""
        if session_id not in self.active_sessions:
            return False
        
        session_data = self.active_sessions[session_id]
        current_time = time.time()
        
        # Check session timeout
        session_age = current_time - session_data['last_activity']
        max_age = self.policy.session_timeout_minutes * 60
        
        if session_age > max_age:
            # Session expired
            self.logout_user(session_id)
            return False
        
        return True
    
    def _update_session_activity(self, session_id: str) -> None:
        """Update session last activity time."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['last_activity'] = time.time()
    
    def logout_user(self, session_id: str) -> bool:
        """Log out user and invalidate session."""
        try:
            # Remove from memory
            session_data = self.active_sessions.pop(session_id, None)
            
            # Mark as inactive in database
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions SET active = FALSE WHERE session_id = ?
                """, (session_id,))
                conn.commit()
            
            if session_data:
                self._log_security_event("logout", "info", session_data['user_id'], 
                                       session_data.get('ip_address'), "User logged out")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def _log_access(self, result: AccessResult, ip_address: Optional[str] = None,
                   context: Optional[Dict[str, Any]] = None) -> None:
        """Log access attempt."""
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO access_log 
                    (user_id, resource, action, granted, reason, ip_address, risk_score, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.user_id, result.resource, result.action.value,
                    result.granted, result.reason, ip_address, result.risk_score,
                    json.dumps(context) if context else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log access: {e}")
    
    def _log_security_event(self, event_type: str, severity: str, user_id: Optional[str],
                          ip_address: Optional[str], description: str, details: Optional[Dict] = None) -> None:
        """Log security event."""
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_events 
                    (event_type, severity, user_id, ip_address, description, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_type, severity, user_id, ip_address, description,
                    json.dumps(details) if details else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def require_permission(self, permission: Permission):
        """Decorator to require permission for function access."""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Extract session_id and resource from arguments
                session_id = kwargs.get('session_id')
                resource = kwargs.get('resource', func.__name__)
                
                if not session_id:
                    raise PermissionError("Session ID required")
                
                # Check access
                result = self.check_access(session_id, resource, permission)
                
                if not result.granted:
                    raise PermissionError(f"Access denied: {result.reason}")
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    # Utility methods for policy checks
    def _count_active_downloads(self, user_id: str) -> int:
        """Count active downloads for user."""
        # This would integrate with download manager
        return 0
    
    def _get_user_disk_usage(self, user_id: str) -> int:
        """Get user's current disk usage in MB."""
        # This would integrate with storage system
        return 0
    
    def _is_known_ip(self, user_id: str, ip_address: str) -> bool:
        """Check if IP address is known for user."""
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM user_sessions 
                    WHERE user_id = ? AND ip_address = ?
                    AND last_activity > ?
                """, (user_id, ip_address, time.time() - (7 * 86400)))  # Last 7 days
                
                return cursor.fetchone()[0] > 0
                
        except Exception:
            return False
    
    def _detect_rapid_requests(self, user_id: str) -> bool:
        """Detect rapid successive requests."""
        current_time = time.time()
        
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM access_log 
                    WHERE user_id = ? AND timestamp > ?
                """, (user_id, current_time - 60))  # Last minute
                
                return cursor.fetchone()[0] > 10
                
        except Exception:
            return False
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for dashboard."""
        cutoff_time = time.time() - (hours * 3600)
        
        try:
            with sqlite3.connect(self.access_db) as conn:
                cursor = conn.cursor()
                
                # Access attempts
                cursor.execute("""
                    SELECT granted, COUNT(*) FROM access_log 
                    WHERE timestamp >= ? GROUP BY granted
                """, (cutoff_time,))
                access_stats = dict(cursor.fetchall())
                
                # Security events
                cursor.execute("""
                    SELECT severity, COUNT(*) FROM security_events 
                    WHERE timestamp >= ? GROUP BY severity
                """, (cutoff_time,))
                security_events = dict(cursor.fetchall())
                
                # Active sessions
                active_sessions = len(self.active_sessions)
                
                # Failed login attempts
                cursor.execute("""
                    SELECT COUNT(*) FROM security_events 
                    WHERE event_type = 'login_failed' AND timestamp >= ?
                """, (cutoff_time,))
                failed_logins = cursor.fetchone()[0]
                
                return {
                    'period_hours': hours,
                    'access_attempts': {
                        'granted': access_stats.get(1, 0),
                        'denied': access_stats.get(0, 0),
                        'total': sum(access_stats.values())
                    },
                    'security_events': security_events,
                    'active_sessions': active_sessions,
                    'failed_logins': failed_logins,
                    'policy': self.policy.name
                }
                
        except Exception as e:
            logger.error(f"Failed to get security summary: {e}")
            return {}
    
    @staticmethod
    def create_default_policy() -> SecurityPolicy:
        """Create default security policy."""
        return SecurityPolicy(
            name="default",
            description="Default security policy",
            max_login_attempts=5,
            lockout_duration_minutes=30,
            session_timeout_minutes=60,
            password_min_length=8,
            require_2fa=False,
            rate_limit_requests_per_minute=60,
            audit_all_access=True,
            max_file_size_mb=1000,
            max_concurrent_downloads=3,
            max_disk_usage_mb=10000
        )
    
    @staticmethod 
    def create_strict_policy() -> SecurityPolicy:
        """Create strict security policy."""
        return SecurityPolicy(
            name="strict",
            description="Strict security policy for high-security environments",
            max_login_attempts=3,
            lockout_duration_minutes=60,
            session_timeout_minutes=30,
            password_min_length=12,
            require_2fa=True,
            rate_limit_requests_per_minute=30,
            audit_all_access=True,
            max_file_size_mb=500,
            allowed_file_extensions={'.safetensors'},
            blocked_file_extensions={'.exe', '.bat', '.sh', '.py', '.js'},
            max_concurrent_downloads=1,
            max_disk_usage_mb=5000
        )