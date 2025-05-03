import pytest
import os
import base64
from unittest.mock import patch

from app.utils.key_encryption import KeyEncryption

# Sample test data
TEST_MASTER_KEY = "super_secret_test_key_12345"
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDHWRxLu7aAgbSP
4jRH3SHR+ZMgEgsFQS6IIm9Mz9NxwIpMrA4XCBCj/dn2WH0xLxhjmQEXUEK/fRzb
J/0xcRYSj1OD0XnM0xGmxzFK7yViYKSkE/X1yQTPWC+CyQMcOKqDONDkNKdPeUEY
VtmQIDFQ3SUQwHxDmCKj0AIpF8cvmVDzY9opltKfoMjf1RuCxYq2XMxygAOvZLoF
tYLiSsDOapA0bswcXWTtWUELIWIs+OGLc6oa4BbG2D3y6GEDfBgJGYH5QFPdl56h
CXTzr3nMEC5M1K9+M1TmLUmTB98qnQTx/xUP+TkgPdJGrHLn7KFq87ArcutDm8M9
vK3d0F1TAgMBAAECggEAZ9CczlX45kIRUTKJSQ3BHrUrgVkXsXQwvzMfSQH+96d6
Y/1W3EgGjY8xO9UpFE0wXvoztXN9nTq5S/74ARucBXmKQ3Z83K2wsCOXVQXs45KN
tSfd42xAqMs2ObP9UH8yqVbrvqP1jQY0NViy46oZ5La+MlFRHuFPLPBGcODf5/JT
vGNEFhjvKq2I8xqHHXjwGYZWa4XM7K/UcuUJbdEFP9y+IlX0s88kg3tFgDdwZ8As
W2vwGQh1E7mjHukzVx5nQwVKhLs2o8J52Ryan1NWMjxkSJsgkF9gO2tQDJ0GfYJl
EUkLpUDwspRBGgD1gCVoweVS4/FQTtOQYfv3KsCXKQKBgQDrNYYwUm1Mjk7sSgDg
fMyXoqyPqK5cC5OVktGfJ4goGNBUBFjpQNIGBAeuCbeUcxZPF38YzxFgPiKPskKE
ZQIaTPZ6XaKK+cELSnu+KpQxTsCI9KPWp2ItQKN+gOHsdpXpw/OGEXNQJSN+zjfn
7Vgj/9SFGaxBNR5Cxx++WOSKFQKBgQDY+dc9YWSrAmxtmr7vwjXNY5F+jBghxjMV
dQnTGEh3iZE5Iu6QXPLTqZzKms6eGzJJ4QauPUoMQQGkIq1lTlQXiYCYoGxzj0vN
BsiRJww3QpPJTQq0IeUT5fwQYV7C+inTYwJ2JL8hdXRj1tQ7PYYt6mJJ2TbwDCJD
QEzEEQHVNwKBgQDqnxZfCTmiFBmkRgHXTUYKpMKAUO8s4Lu/F/dxnzRnhx0SDO0N
glpCbGxHBxQQgpRMbLVi6iNj9yR3jkDKvqkwz9MJtG3WcRLTxHQRtfYjOCCLPWyI
pbsR0V+ZWTwUHOJQhUzw1VfFAEfF9xzb/xwRo9SeKB80R9D9Pru2o+UwdQKBgQCL
oeJiYpg9DQvQDIWxFKWEAOiUzLxQqsARjuJuZkYX3BwXrV+YQf6yiWWZpnO57OSb
ZBLdjkYM+Pl5K3IFO4MC9RjGjbKvH8zOWjNVdOqYTYNJBXFbQXzEjvxOH4drbwTs
FPNh5BWJeqafV38WTtf5T8jLI4AyBhG/4ftsdygYKQKBgHnEqOi4V5VW5d94xyFV
dNn9m1KRmSF7SU3pMzzwvrTFRrFY0eL7lH12BBpJxdK6WASWkKLEzPQXsaDkIDE0
L81KGfZbouNihxgO5gIItXJunRytoJsRuT0PExJOOfiVgEUJ8J5yPxhQ1Bcp8ioG
gn9GX6QGO07MCi+UVsG8JXNf
-----END PRIVATE KEY-----"""


class TestKeyEncryption:
    def test_initialization_with_provided_key(self):
        """Test initializing with an explicitly provided key"""
        encryptor = KeyEncryption(master_key=TEST_MASTER_KEY)
        assert encryptor.master_key == TEST_MASTER_KEY
    
    def test_initialization_with_env_var(self):
        """Test initializing with a key from environment variable"""
        with patch.dict(os.environ, {"MASTER_ENCRYPTION_KEY": TEST_MASTER_KEY}):
            encryptor = KeyEncryption()
            assert encryptor.master_key == TEST_MASTER_KEY
    
    def test_initialization_error_no_key(self):
        """Test that initialization fails when no key is provided"""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(ValueError) as excinfo:
                KeyEncryption()
            assert "Master encryption key must be provided" in str(excinfo.value)
    
    def test_encrypt_decrypt_cycle(self):
        """Test a full encrypt-decrypt cycle"""
        encryptor = KeyEncryption(master_key=TEST_MASTER_KEY)
        
        # Encrypt the test private key
        encrypted_data = encryptor.encrypt_private_key(TEST_PRIVATE_KEY)
        
        # Verify the encrypted data structure
        assert "encrypted_key" in encrypted_data
        assert "salt" in encrypted_data
        assert "nonce" in encrypted_data
        assert "method" in encrypted_data
        assert encrypted_data["method"] == "AES-256-GCM"
        
        # Verify the data is actually encrypted
        encrypted_key = base64.b64decode(encrypted_data["encrypted_key"])
        assert TEST_PRIVATE_KEY.encode() != encrypted_key
        
        # Decrypt the private key
        decrypted_key = encryptor.decrypt_private_key(encrypted_data)
        
        # Verify the decrypted key matches the original
        assert decrypted_key == TEST_PRIVATE_KEY
    
    def test_encrypt_decrypt_different_keys(self):
        """Test that encryption/decryption fails with different keys"""
        # Encrypt with one key
        encryptor1 = KeyEncryption(master_key=TEST_MASTER_KEY)
        encrypted_data = encryptor1.encrypt_private_key(TEST_PRIVATE_KEY)
        
        # Try to decrypt with a different key
        encryptor2 = KeyEncryption(master_key="different_key")
        
        # This should raise an exception during decryption
        with pytest.raises(Exception):
            encryptor2.decrypt_private_key(encrypted_data)
    
    def test_derive_key(self):
        """Test key derivation produces consistent results"""
        encryptor = KeyEncryption(master_key=TEST_MASTER_KEY)
        salt = b"test_salt_12345678"
        
        # Derive key twice with the same salt
        key1 = encryptor._derive_key(salt)
        key2 = encryptor._derive_key(salt)
        
        # Keys should be identical when using the same salt
        assert key1 == key2
        
        # Keys should be different with different salts
        different_salt = b"different_salt_123"
        key3 = encryptor._derive_key(different_salt)
        assert key1 != key3
    
    def test_encryption_consistency(self):
        """Test that encryption with the same key and nonce is consistent"""
        encryptor = KeyEncryption(master_key=TEST_MASTER_KEY)
        
        # Mock the random functions to return consistent values
        fixed_salt = b"fixed_salt_value_1"
        fixed_nonce = b"fixed_nonce_1"
        
        with patch('os.urandom', side_effect=[fixed_salt, fixed_nonce]):
            # First encryption
            encrypted_data1 = encryptor.encrypt_private_key(TEST_PRIVATE_KEY)
        
        with patch('os.urandom', side_effect=[fixed_salt, fixed_nonce]):
            # Second encryption with same salt/nonce
            encrypted_data2 = encryptor.encrypt_private_key(TEST_PRIVATE_KEY)
        
        # The encrypted data should be identical
        assert encrypted_data1["encrypted_key"] == encrypted_data2["encrypted_key"]