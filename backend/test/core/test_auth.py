import pytest
import uuid
from unittest import mock
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt

from app.core.auth import Auth, get_current_user_from_api_key, JWT_SECRET, JWT_ALGORITHM


@pytest.mark.asyncio
async def test_get_api_key_success():
    """Test validating a valid API key"""
    # Create mock user and API key
    user_id = str(uuid.uuid4())
    mock_user = {
        "id": user_id,
        "email": "test@example.com",
        "full_name": "Test User",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    mock_key_data = {
        "id": str(uuid.uuid4()),
        "key": "test_api_key_123",
        "user": mock_user
    }
    
    # Mock the validate_api_key method
    async def mock_validate_api_key(api_key):
        if api_key == "test_api_key_123":
            return mock_key_data
        return None
    
    # Apply mock
    with mock.patch('app.db.client.Database.validate_api_key', mock_validate_api_key):
        # Test with valid key
        result = await Auth.get_api_key(api_key="test_api_key_123")
        
        # Verify result
        assert result == mock_key_data
        assert result["user"]["id"] == user_id


@pytest.mark.asyncio
async def test_get_api_key_missing():
    """Test validating a missing API key"""
    # Apply mock - not strictly needed since the function should fail before this
    with mock.patch('app.db.client.Database.validate_api_key', return_value=None):
        # Test with missing key
        with pytest.raises(HTTPException) as excinfo:
            await Auth.get_api_key(api_key=None)
        
        # Verify exception
        assert excinfo.value.status_code == 401
        assert "API key is missing" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_api_key_invalid():
    """Test validating an invalid API key"""
    # Mock the validate_api_key method to return None (invalid key)
    async def mock_validate_api_key(api_key):
        return None
    
    # Apply mock
    with mock.patch('app.db.client.Database.validate_api_key', mock_validate_api_key):
        # Test with invalid key
        with pytest.raises(HTTPException) as excinfo:
            await Auth.get_api_key(api_key="invalid_key")
        
        # Verify exception
        assert excinfo.value.status_code == 401
        assert "Invalid API key" in excinfo.value.detail


def test_create_access_token():
    """Test creating a JWT access token"""
    # Create test data
    user_data = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com"
    }
    
    # Create token with default expiry
    token = Auth.create_access_token(data=user_data)
    
    # Verify token can be decoded
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert decoded["sub"] == user_data["sub"]
    assert decoded["email"] == user_data["email"]
    assert "exp" in decoded
    
    # Create token with custom expiry
    custom_expiry = timedelta(minutes=30)
    token = Auth.create_access_token(data=user_data, expires_delta=custom_expiry)
    
    # Verify token with custom expiry
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert decoded["sub"] == user_data["sub"]
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_generate_api_key():
    """Test generating a new API key"""
    # Create test data
    user_id = str(uuid.uuid4())
    name = "Test API Key"
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    # Mock the create_api_key method
    mock_api_key = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "key": "generated_api_key_" + str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat()
    }
    
    async def mock_create_api_key(user_id, name, expires_at=None, description=None):
        return mock_api_key
    
    # Apply mock
    with mock.patch('app.db.client.Database.create_api_key', mock_create_api_key):
        # Test with expiry
        result = await Auth.generate_api_key(
            user_id=user_id,
            name=name,
            expires_at=expires_at
        )
        
        # Verify result
        assert result == mock_api_key
        
        # Test without expiry
        result = await Auth.generate_api_key(
            user_id=user_id,
            name=name
        )
        
        # Verify result
        assert result == mock_api_key


@pytest.mark.asyncio
async def test_get_current_user_from_api_key():
    """Test extracting the user data from an API key"""
    # Create mock user and API key data
    user_id = str(uuid.uuid4())
    mock_user = {
        "id": user_id,
        "email": "test@example.com",
        "full_name": "Test User"
    }
    
    mock_key_data = {
        "id": str(uuid.uuid4()),
        "key": "test_api_key_123",
        "user": mock_user
    }
    
    # Test the function
    result = await get_current_user_from_api_key(api_key_data=mock_key_data)
    
    # Verify result
    assert result == mock_user
    assert result["id"] == user_id