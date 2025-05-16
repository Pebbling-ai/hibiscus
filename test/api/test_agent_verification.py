import pytest
import uuid
from unittest import mock
from datetime import datetime, timezone

def test_basic():
    """Simple test to ensure pytest is working"""
    assert True

@pytest.fixture
def mock_verification_db(monkeypatch):
    verifications = []
    
    async def mock_create_agent_verification(verification_data):
        new_verification = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
            **verification_data
        }
        verifications.append(new_verification)
        return new_verification
    
    from app.db.client import Database
    monkeypatch.setattr(Database, "create_agent_verification", mock_create_agent_verification)
    
    return verifications

@pytest.mark.asyncio
async def test_agent_verification_creation(mock_database):
    """Test creating an agent verification record"""
    # Test DID data
    verification_data = {
        "agent_id": str(uuid.uuid4()),
        "did": "did:mlts:example123",
        "public_key": "-----BEGIN PUBLIC KEY-----\nSample Key Content\n-----END PUBLIC KEY-----",
        "verification_method": "mlts",
        "status": "active",
        "did_document": {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:mlts:example123",
            "authentication": ["did:mlts:example123#keys-1"],
            "verificationMethod": [{
                "id": "did:mlts:example123#keys-1",
                "type": "Ed25519VerificationKey2020",
                "controller": "did:mlts:example123",
                "publicKeyMultibase": "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
            }]
        }
    }
    
    # Create verification
    result = await mock_database.create_agent_verification(verification_data)
    
    # Verify the result
    assert result["agent_id"] == verification_data["agent_id"]
    assert result["did"] == verification_data["did"]
    assert result["public_key"] == verification_data["public_key"]
    assert result["verification_method"] == verification_data["verification_method"]
    assert result["status"] == verification_data["status"]
    assert "did_document" in result
    assert "id" in result
    assert "created_at" in result