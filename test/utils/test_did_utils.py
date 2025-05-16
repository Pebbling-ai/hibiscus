import pytest
from app.utils.did_utils import DIDManager, MltsProtocolHandler

def test_did_generation():
    # Test that DIDs are generated with the correct format
    did = DIDManager.generate_did()
    assert did.startswith(f"did:{DIDManager.DID_METHOD}:")
    assert len(did) > 10  # Basic length check

def test_did_generation_with_key():
    # Test generation with a public key
    test_key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo
    4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u
    +qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh
    kd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ
    0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg
    cKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc
    mwIDAQAB
    -----END PUBLIC KEY-----"""
    
    did = DIDManager.generate_did(test_key)
    assert did.startswith(f"did:{DIDManager.DID_METHOD}:")
    assert len(did) > 10
    
    # The same key should generate the same DID
    did2 = DIDManager.generate_did(test_key)
    assert did == did2

def test_did_document_creation():
    # Test that a DID document is created with correct structure
    public_key = "sample_public_key_data"
    did = f"did:{DIDManager.DID_METHOD}:sample123"
    
    document = DIDManager.generate_did_document(did, public_key)
    
    assert document["id"] == did
    assert "verificationMethod" in document
    assert len(document["verificationMethod"]) > 0
    assert document["verificationMethod"][0]["controller"] == did

def test_did_parsing():
    # Test DID parsing functionality
    did = f"did:{DIDManager.DID_METHOD}:sample456"
    
    parsed = DIDManager.parse_did(did)
    assert parsed["did"] == did
    assert parsed["method"] == DIDManager.DID_METHOD
    assert parsed["identifier"] == "sample456"
    
    # Test invalid DID
    with pytest.raises(ValueError):
        DIDManager.parse_did("invalid:did")

def test_mlts_protocol_key_generation():
    # Test the MLTS protocol key generation
    handler = MltsProtocolHandler()
    
    # Test key generation
    public_key, private_key = handler.generate_keys()
    assert public_key is not None
    assert private_key is not None
    assert "BEGIN PUBLIC KEY" in public_key
    assert "BEGIN PRIVATE KEY" in private_key

def test_mlts_protocol_signing():
    # Test the MLTS protocol message signing
    handler = MltsProtocolHandler()
    _, private_key = handler.generate_keys()
    
    # Test message signing
    test_message = {"action": "test", "payload": "hello world"}
    signed_message = handler.sign_message(test_message, private_key)
    
    # Check signature was added
    assert "signature" in signed_message
    assert "value" in signed_message["signature"]