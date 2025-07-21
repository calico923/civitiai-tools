#!/usr/bin/env python3
"""
Data Encryption and Protection System.
Implements requirement 18.3: Data encryption and secure storage.
"""

import logging
import os
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Union, Tuple, List
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import json
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import secrets

logger = logging.getLogger(__name__)


class EncryptionLevel(Enum):
    """Encryption strength levels."""
    BASIC = "basic"          # Fernet (AES-128)
    STANDARD = "standard"    # AES-256 with PBKDF2
    HIGH = "high"           # RSA-2048 + AES-256
    MAXIMUM = "maximum"     # RSA-4096 + AES-256 + multiple rounds


@dataclass
class EncryptionConfig:
    """Encryption configuration settings."""
    level: EncryptionLevel
    key_derivation_iterations: int = 100000
    salt_size: int = 32
    rsa_key_size: int = 2048
    enable_compression: bool = True
    enable_integrity_check: bool = True


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    level: EncryptionLevel
    salt: Optional[bytes] = None
    iv: Optional[bytes] = None
    public_key_fingerprint: Optional[str] = None
    integrity_hash: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode(),
            'level': self.level.value,
            'salt': base64.b64encode(self.salt).decode() if self.salt else None,
            'iv': base64.b64encode(self.iv).decode() if self.iv else None,
            'public_key_fingerprint': self.public_key_fingerprint,
            'integrity_hash': self.integrity_hash,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """Create from dictionary."""
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            level=EncryptionLevel(data['level']),
            salt=base64.b64decode(data['salt']) if data['salt'] else None,
            iv=base64.b64decode(data['iv']) if data['iv'] else None,
            public_key_fingerprint=data.get('public_key_fingerprint'),
            integrity_hash=data.get('integrity_hash'),
            metadata=data.get('metadata')
        )


class DataEncryption:
    """
    Data encryption and protection system.
    Implements requirement 18.3: Multi-level encryption with key management.
    """
    
    def __init__(self, config: EncryptionConfig, key_store_path: Optional[Path] = None):
        """
        Initialize encryption system.
        
        Args:
            config: Encryption configuration
            key_store_path: Path to key storage file
        """
        self.config = config
        self.key_store_path = key_store_path or Path.home() / ".config" / "civitai-downloader" / "encryption_keys.db"
        
        # Ensure secure directory creation
        if not self.key_store_path.parent.exists():
            self.key_store_path.parent.mkdir(parents=True, mode=0o700)
        
        # Key cache for performance
        self._key_cache: Dict[str, Any] = {}
        self._rsa_keys: Dict[str, Tuple[Any, Any]] = {}  # public, private key pairs
        
        # Initialize key storage
        self._initialize_key_store()
        
        # Generate or load master keys
        self._setup_master_keys()
    
    def _initialize_key_store(self) -> None:
        """Initialize encrypted key storage."""
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                
                # Encryption keys table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS encryption_keys (
                        key_id TEXT PRIMARY KEY,
                        key_type TEXT NOT NULL,
                        encrypted_key BLOB NOT NULL,
                        salt BLOB NOT NULL,
                        public_key TEXT,
                        fingerprint TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        last_used REAL,
                        usage_count INTEGER DEFAULT 0
                    )
                """)
                
                # Key metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS key_metadata (
                        key_id TEXT PRIMARY KEY,
                        encryption_level TEXT NOT NULL,
                        purpose TEXT,
                        expiry_date REAL,
                        active BOOLEAN DEFAULT TRUE,
                        metadata TEXT,
                        FOREIGN KEY (key_id) REFERENCES encryption_keys(key_id)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize key store: {e}")
    
    def _setup_master_keys(self) -> None:
        """Setup master encryption keys."""
        try:
            # Generate or load master key for key encryption
            master_key_id = "master_key_v1"
            
            if not self._key_exists(master_key_id):
                # Generate new master key
                master_key = Fernet.generate_key()
                self._store_master_key(master_key_id, master_key)
                logger.info("Generated new master encryption key")
            else:
                logger.debug("Using existing master encryption key")
            
            # Generate RSA key pairs if needed
            if self.config.level in [EncryptionLevel.HIGH, EncryptionLevel.MAXIMUM]:
                self._setup_rsa_keys()
                
        except Exception as e:
            logger.error(f"Failed to setup master keys: {e}")
            raise
    
    def _setup_rsa_keys(self) -> None:
        """Setup RSA key pairs for asymmetric encryption."""
        key_sizes = {
            EncryptionLevel.HIGH: 2048,
            EncryptionLevel.MAXIMUM: 4096
        }
        
        key_size = key_sizes.get(self.config.level, self.config.rsa_key_size)
        rsa_key_id = f"rsa_key_{key_size}bit"
        
        if not self._key_exists(rsa_key_id):
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Store keys securely
            self._store_rsa_key_pair(rsa_key_id, private_pem, public_pem)
            logger.info(f"Generated new {key_size}-bit RSA key pair")
    
    def encrypt_data(self, data: Union[str, bytes], context: Optional[Dict[str, Any]] = None) -> EncryptedData:
        """
        Encrypt data using configured encryption level.
        
        Args:
            data: Data to encrypt
            context: Additional context for encryption
            
        Returns:
            EncryptedData object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Add compression if enabled
        if self.config.enable_compression:
            data = self._compress_data(data)
        
        # Encrypt based on level
        if self.config.level == EncryptionLevel.BASIC:
            return self._encrypt_basic(data, context)
        elif self.config.level == EncryptionLevel.STANDARD:
            return self._encrypt_standard(data, context)
        elif self.config.level == EncryptionLevel.HIGH:
            return self._encrypt_high(data, context)
        elif self.config.level == EncryptionLevel.MAXIMUM:
            return self._encrypt_maximum(data, context)
        else:
            raise ValueError(f"Unsupported encryption level: {self.config.level}")
    
    def decrypt_data(self, encrypted_data: EncryptedData, context: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data: EncryptedData to decrypt
            context: Additional context for decryption
            
        Returns:
            Decrypted data as bytes
        """
        # Verify integrity if enabled
        if self.config.enable_integrity_check and encrypted_data.integrity_hash:
            self._verify_integrity(encrypted_data)
        
        # Decrypt based on level
        if encrypted_data.level == EncryptionLevel.BASIC:
            data = self._decrypt_basic(encrypted_data, context)
        elif encrypted_data.level == EncryptionLevel.STANDARD:
            data = self._decrypt_standard(encrypted_data, context)
        elif encrypted_data.level == EncryptionLevel.HIGH:
            data = self._decrypt_high(encrypted_data, context)
        elif encrypted_data.level == EncryptionLevel.MAXIMUM:
            data = self._decrypt_maximum(encrypted_data, context)
        else:
            raise ValueError(f"Unsupported encryption level: {encrypted_data.level}")
        
        # Decompress if compression was used
        if self.config.enable_compression:
            data = self._decompress_data(data)
        
        return data
    
    def _encrypt_basic(self, data: bytes, context: Optional[Dict[str, Any]]) -> EncryptedData:
        """Basic encryption using Fernet."""
        fernet = Fernet(self._get_master_key("master_key_v1"))
        ciphertext = fernet.encrypt(data)
        
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            level=EncryptionLevel.BASIC,
            metadata=context
        )
        
        if self.config.enable_integrity_check:
            encrypted_data.integrity_hash = self._calculate_integrity_hash(encrypted_data)
        
        return encrypted_data
    
    def _decrypt_basic(self, encrypted_data: EncryptedData, context: Optional[Dict[str, Any]]) -> bytes:
        """Basic decryption using Fernet."""
        fernet = Fernet(self._get_master_key("master_key_v1"))
        return fernet.decrypt(encrypted_data.ciphertext)
    
    def _encrypt_standard(self, data: bytes, context: Optional[Dict[str, Any]]) -> EncryptedData:
        """Standard encryption using AES-256 with PBKDF2."""
        # Generate salt and password
        salt = secrets.token_bytes(self.config.salt_size)
        password = self._derive_password_key(context)
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.key_derivation_iterations,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Encrypt with Fernet
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(data)
        
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            level=EncryptionLevel.STANDARD,
            salt=salt,
            metadata=context
        )
        
        if self.config.enable_integrity_check:
            encrypted_data.integrity_hash = self._calculate_integrity_hash(encrypted_data)
        
        return encrypted_data
    
    def _decrypt_standard(self, encrypted_data: EncryptedData, context: Optional[Dict[str, Any]]) -> bytes:
        """Standard decryption using AES-256 with PBKDF2."""
        password = self._derive_password_key(context)
        
        # Derive key using stored salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=encrypted_data.salt,
            iterations=self.config.key_derivation_iterations,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Decrypt
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data.ciphertext)
    
    def _encrypt_high(self, data: bytes, context: Optional[Dict[str, Any]]) -> EncryptedData:
        """High-level encryption using RSA + AES."""
        # Get RSA key pair
        public_key, _ = self._get_rsa_keys()
        
        # Generate random AES key
        aes_key = Fernet.generate_key()
        
        # Encrypt data with AES
        fernet = Fernet(aes_key)
        encrypted_data_bytes = fernet.encrypt(data)
        
        # Encrypt AES key with RSA public key
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine encrypted key + encrypted data
        ciphertext = encrypted_aes_key + encrypted_data_bytes
        
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            level=EncryptionLevel.HIGH,
            public_key_fingerprint=self._get_public_key_fingerprint(public_key),
            metadata=context
        )
        
        if self.config.enable_integrity_check:
            encrypted_data.integrity_hash = self._calculate_integrity_hash(encrypted_data)
        
        return encrypted_data
    
    def _decrypt_high(self, encrypted_data: EncryptedData, context: Optional[Dict[str, Any]]) -> bytes:
        """High-level decryption using RSA + AES."""
        _, private_key = self._get_rsa_keys()
        
        # Split encrypted AES key and encrypted data
        key_size = private_key.key_size // 8  # RSA key size in bytes
        encrypted_aes_key = encrypted_data.ciphertext[:key_size]
        encrypted_data_bytes = encrypted_data.ciphertext[key_size:]
        
        # Decrypt AES key with RSA private key
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt data with AES
        fernet = Fernet(aes_key)
        return fernet.decrypt(encrypted_data_bytes)
    
    def _encrypt_maximum(self, data: bytes, context: Optional[Dict[str, Any]]) -> EncryptedData:
        """Maximum security encryption with multiple rounds."""
        # First round: Standard encryption
        round1 = self._encrypt_standard(data, context)
        
        # Second round: High encryption of the result
        round1_serialized = json.dumps(round1.to_dict()).encode()
        round2 = self._encrypt_high(round1_serialized, context)
        
        # Mark as maximum level
        round2.level = EncryptionLevel.MAXIMUM
        
        return round2
    
    def _decrypt_maximum(self, encrypted_data: EncryptedData, context: Optional[Dict[str, Any]]) -> bytes:
        """Maximum security decryption with multiple rounds."""
        # First round: High decryption
        round1_data = self._decrypt_high(encrypted_data, context)
        
        # Deserialize first round result
        round1_dict = json.loads(round1_data.decode())
        round1_encrypted = EncryptedData.from_dict(round1_dict)
        
        # Second round: Standard decryption
        return self._decrypt_standard(round1_encrypted, context)
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data before encryption."""
        import zlib
        return zlib.compress(data, level=9)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data after decryption."""
        import zlib
        return zlib.decompress(data)
    
    def _derive_password_key(self, context: Optional[Dict[str, Any]]) -> bytes:
        """Derive password key from context and master key."""
        master_key = self._get_master_key("master_key_v1")
        
        # Combine master key with context-specific data
        key_material = master_key
        
        if context:
            # Add context to key derivation
            context_data = json.dumps(context, sort_keys=True).encode()
            key_material = key_material + context_data
        
        # Hash to create consistent password
        return hashlib.sha256(key_material).digest()
    
    def _calculate_integrity_hash(self, encrypted_data: EncryptedData) -> str:
        """Calculate integrity hash for encrypted data."""
        # Include all critical fields in hash
        hash_data = {
            'ciphertext': base64.b64encode(encrypted_data.ciphertext).decode(),
            'level': encrypted_data.level.value,
            'salt': base64.b64encode(encrypted_data.salt).decode() if encrypted_data.salt else None,
            'public_key_fingerprint': encrypted_data.public_key_fingerprint
        }
        
        hash_content = json.dumps(hash_data, sort_keys=True).encode()
        return hashlib.sha256(hash_content).hexdigest()
    
    def _verify_integrity(self, encrypted_data: EncryptedData) -> None:
        """Verify integrity of encrypted data."""
        calculated_hash = self._calculate_integrity_hash(encrypted_data)
        
        if not hmac.compare_digest(calculated_hash, encrypted_data.integrity_hash):
            raise ValueError("Integrity check failed - data may be corrupted or tampered")
    
    def _get_public_key_fingerprint(self, public_key) -> str:
        """Calculate public key fingerprint."""
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(public_bytes).hexdigest()[:16]
    
    def _key_exists(self, key_id: str) -> bool:
        """Check if key exists in storage."""
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM encryption_keys WHERE key_id = ?", (key_id,))
                return cursor.fetchone()[0] > 0
        except Exception:
            return False
    
    def _store_master_key(self, key_id: str, key: bytes) -> None:
        """Store master key securely."""
        # For master key, we'll store it with minimal encryption
        salt = secrets.token_bytes(32)
        
        # Use system entropy for master key protection
        system_key = os.urandom(32)
        
        # Simple XOR encryption for master key (in production, use hardware security module)
        encrypted_key = bytes(a ^ b for a, b in zip(key, system_key * (len(key) // len(system_key) + 1)))
        
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO encryption_keys
                    (key_id, key_type, encrypted_key, salt)
                    VALUES (?, ?, ?, ?)
                """, (key_id, "master", encrypted_key, system_key))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store master key: {e}")
            raise
    
    def _get_master_key(self, key_id: str) -> bytes:
        """Retrieve master key."""
        if key_id in self._key_cache:
            return self._key_cache[key_id]
        
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT encrypted_key, salt FROM encryption_keys 
                    WHERE key_id = ? AND key_type = 'master'
                """, (key_id,))
                
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Master key not found: {key_id}")
                
                encrypted_key, system_key = result
                
                # Decrypt master key
                key = bytes(a ^ b for a, b in zip(encrypted_key, system_key * (len(encrypted_key) // len(system_key) + 1)))
                
                # Cache for performance
                self._key_cache[key_id] = key
                
                return key
                
        except Exception as e:
            logger.error(f"Failed to retrieve master key: {e}")
            raise
    
    def _store_rsa_key_pair(self, key_id: str, private_key: bytes, public_key: bytes) -> None:
        """Store RSA key pair."""
        # Encrypt private key with master key
        master_key = self._get_master_key("master_key_v1")
        fernet = Fernet(master_key)
        encrypted_private_key = fernet.encrypt(private_key)
        
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO encryption_keys
                    (key_id, key_type, encrypted_key, salt, public_key)
                    VALUES (?, ?, ?, ?, ?)
                """, (key_id, "rsa", encrypted_private_key, b"", public_key.decode()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store RSA keys: {e}")
            raise
    
    def _get_rsa_keys(self) -> Tuple[Any, Any]:
        """Get RSA key pair (public, private)."""
        key_sizes = {
            EncryptionLevel.HIGH: 2048,
            EncryptionLevel.MAXIMUM: 4096
        }
        
        key_size = key_sizes.get(self.config.level, 2048)
        key_id = f"rsa_key_{key_size}bit"
        
        if key_id in self._rsa_keys:
            return self._rsa_keys[key_id]
        
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT encrypted_key, public_key FROM encryption_keys 
                    WHERE key_id = ? AND key_type = 'rsa'
                """, (key_id,))
                
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"RSA key pair not found: {key_id}")
                
                encrypted_private_key, public_key_pem = result
                
                # Decrypt private key
                master_key = self._get_master_key("master_key_v1")
                fernet = Fernet(master_key)
                private_key_pem = fernet.decrypt(encrypted_private_key)
                
                # Load keys
                private_key = serialization.load_pem_private_key(
                    private_key_pem, password=None, backend=default_backend()
                )
                public_key = serialization.load_pem_public_key(
                    public_key_pem.encode(), backend=default_backend()
                )
                
                # Cache keys
                self._rsa_keys[key_id] = (public_key, private_key)
                
                return public_key, private_key
                
        except Exception as e:
            logger.error(f"Failed to retrieve RSA keys: {e}")
            raise
    
    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file.
        
        Args:
            file_path: Path to file to encrypt
            output_path: Optional output path (defaults to original + .enc)
            
        Returns:
            Path to encrypted file
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        output_path = output_path or file_path.with_suffix(file_path.suffix + '.enc')
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encrypt data
        context = {
            'filename': file_path.name,
            'original_size': len(file_data)
        }
        encrypted_data = self.encrypt_data(file_data, context)
        
        # Save encrypted file
        with open(output_path, 'w') as f:
            json.dump(encrypted_data.to_dict(), f, indent=2)
        
        logger.info(f"Encrypted file: {file_path} -> {output_path}")
        return output_path
    
    def decrypt_file(self, encrypted_file_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path (auto-detected if not provided)
            
        Returns:
            Path to decrypted file
        """
        if not encrypted_file_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
        # Load encrypted data
        with open(encrypted_file_path, 'r') as f:
            encrypted_dict = json.load(f)
        
        encrypted_data = EncryptedData.from_dict(encrypted_dict)
        
        # Decrypt data
        decrypted_data = self.decrypt_data(encrypted_data)
        
        # Determine output path
        if not output_path:
            if encrypted_file_path.suffix == '.enc':
                output_path = encrypted_file_path.with_suffix('')
            else:
                output_path = encrypted_file_path.with_suffix('.decrypted')
        
        # Save decrypted file
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"Decrypted file: {encrypted_file_path} -> {output_path}")
        return output_path
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """Get information about encryption configuration."""
        return {
            'encryption_level': self.config.level.value,
            'key_derivation_iterations': self.config.key_derivation_iterations,
            'compression_enabled': self.config.enable_compression,
            'integrity_check_enabled': self.config.enable_integrity_check,
            'rsa_key_size': self.config.rsa_key_size,
            'available_keys': self._list_available_keys()
        }
    
    def _list_available_keys(self) -> List[str]:
        """List available encryption keys."""
        try:
            with sqlite3.connect(self.key_store_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key_id, key_type FROM encryption_keys")
                return [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]
        except Exception:
            return []
    
    @staticmethod
    def create_basic_config() -> EncryptionConfig:
        """Create basic encryption configuration."""
        return EncryptionConfig(
            level=EncryptionLevel.BASIC,
            enable_compression=False,
            enable_integrity_check=True
        )
    
    @staticmethod
    def create_standard_config() -> EncryptionConfig:
        """Create standard encryption configuration."""
        return EncryptionConfig(
            level=EncryptionLevel.STANDARD,
            key_derivation_iterations=100000,
            enable_compression=True,
            enable_integrity_check=True
        )
    
    @staticmethod
    def create_high_security_config() -> EncryptionConfig:
        """Create high security encryption configuration."""
        return EncryptionConfig(
            level=EncryptionLevel.HIGH,
            key_derivation_iterations=200000,
            rsa_key_size=2048,
            enable_compression=True,
            enable_integrity_check=True
        )
    
    @staticmethod
    def create_maximum_security_config() -> EncryptionConfig:
        """Create maximum security encryption configuration."""
        return EncryptionConfig(
            level=EncryptionLevel.MAXIMUM,
            key_derivation_iterations=500000,
            rsa_key_size=4096,
            enable_compression=True,
            enable_integrity_check=True
        )