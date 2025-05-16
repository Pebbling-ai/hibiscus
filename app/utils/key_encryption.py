"""
Utility for securely encrypting and decrypting private keys.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class KeyEncryption:
    """Helper class for encrypting and decrypting private keys."""
    
    def __init__(self, master_key=None):
        """
        Initialize with a master key or get from environment variable.
        
        Args:
            master_key (str, optional): Master encryption key. If not provided,
                                        it will be read from MASTER_ENCRYPTION_KEY env var.
        """
        self.master_key = master_key or os.environ.get("MASTER_ENCRYPTION_KEY")
        if not self.master_key:
            raise ValueError("Master encryption key must be provided or set in environment")
    
    def _derive_key(self, salt):
        """
        Derive an encryption key from the master key using PBKDF2.
        
        Args:
            salt (bytes): Random salt for key derivation
            
        Returns:
            bytes: Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(self.master_key.encode())
    
    def encrypt_private_key(self, private_key):
        """
        Encrypt a private key using AES-256-GCM.
        
        Args:
            private_key (str): Private key in PEM format
            
        Returns:
            dict: Dictionary containing:
                - encrypted_key: Base64-encoded encrypted private key
                - salt: Base64-encoded salt used for key derivation
                - nonce: Base64-encoded nonce used for encryption
        """
        # Generate random salt and nonce
        salt = os.urandom(16)
        nonce = os.urandom(12)
        
        # Derive encryption key from master key
        key = self._derive_key(salt)
        
        # Encrypt the private key
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, private_key.encode(), None)
        
        # Return the encrypted data and metadata
        return {
            "encrypted_key": base64.b64encode(ciphertext).decode(),
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "method": "AES-256-GCM"
        }
    
    def decrypt_private_key(self, encrypted_data):
        """
        Decrypt an encrypted private key.
        
        Args:
            encrypted_data (dict): Dictionary containing encryption metadata:
                - encrypted_key: Base64-encoded encrypted private key
                - salt: Base64-encoded salt used for key derivation
                - nonce: Base64-encoded nonce used for encryption
                
        Returns:
            str: Decrypted private key in PEM format
        """
        # Decode encrypted data and metadata
        ciphertext = base64.b64decode(encrypted_data["encrypted_key"])
        salt = base64.b64decode(encrypted_data["salt"])
        nonce = base64.b64decode(encrypted_data["nonce"])
        
        # Derive encryption key from master key
        key = self._derive_key(salt)
        
        # Decrypt the private key
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode()
