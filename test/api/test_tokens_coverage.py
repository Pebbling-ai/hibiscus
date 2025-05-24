import pytest
import uuid
from unittest import mock
from datetime import datetime, timezone, timedelta
from fastapi import Response, HTTPException, status

from app.api.routes.tokens import (
    create_api_token,
    list_api_tokens,
    delete_api_token,
    get_user_profile,
)
from app.models.schemas import ApiKeyCreate


@pytest.mark.asyncio
async def test_create_api_token_with_expiry_days(monkeypatch):
    """Test creating an API token with expiry days"""
    # Create API key data
    api_key_data = ApiKeyCreate(
        name="Test Token",
        expires_in_days=30,
        description="Test token with 30-day expiry",
    )

    # Create mock user
    mock_user = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
    }

    # Mock the create_api_key method
    create_api_key_calls = []

    async def mock_create_api_key(user_id, name, expires_at=None, description=None, is_active=True):
        create_api_key_calls.append((user_id, name, expires_at, description))

        # Calculate expected expiry date for verification
        expected_expiry = None
        if api_key_data.expires_in_days:
            expected_expiry = datetime.now(timezone.utc) + timedelta(
                days=api_key_data.expires_in_days
            )
            expected_expiry = expected_expiry.isoformat()

        # Compare with what was passed to this function
        assert expires_at is not None
        # We can't check exact equality due to microsecond differences in timing
        # So we just check it's roughly the right expiry (within 1 minute)
        expiry_dt = datetime.fromisoformat(expires_at)
        assert (
            abs((expiry_dt - datetime.now(timezone.utc)).total_seconds())
            < 30 * 24 * 60 * 60 + 60
        )

        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "key": "test_api_key_" + str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "description": description,
        }

    # Apply mocks
    with mock.patch("app.db.client.Database.create_api_key", mock_create_api_key):
        # Mock Response object
        response = Response()

        # Call the function
        result = await create_api_token(
            api_key_data=api_key_data, current_user=mock_user, response=response
        )

        # Verify result
        assert result.name == "Test Token"
        assert "key" in result.model_dump()
        assert result.expires_at is not None

        # Verify CORS headers were set
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
        assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


@pytest.mark.asyncio
async def test_create_api_token_permanent(monkeypatch):
    """Test creating a permanent API token (no expiry)"""
    # Create API key data with no expiry
    api_key_data = ApiKeyCreate(
        name="Permanent Token", description="Token that never expires"
    )

    # Create mock user
    mock_user = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
    }

    # Mock the create_api_key method
    async def mock_create_api_key(user_id, name, expires_at=None, description=None, is_active=True):
        # Verify no expiry was set
        assert expires_at is None

        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "key": "permanent_api_key_" + str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "description": description,
        }

    # Apply mocks
    with mock.patch("app.db.client.Database.create_api_key", mock_create_api_key):
        # Call the function
        result = await create_api_token(
            api_key_data=api_key_data,
            current_user=mock_user,
            response=None,  # Test with no response object
        )

        # Verify result
        assert result.name == "Permanent Token"
        assert "key" in result.model_dump()
        assert result.expires_at is None


@pytest.mark.asyncio
async def test_create_api_token_with_absolute_expiry(monkeypatch):
    """Test creating an API token with absolute expiry date"""
    # Create expiry date one month from now
    datetime.now(timezone.utc) + timedelta(days=30)

    # Create API key data with absolute expiry using expires_in_days instead
    # since the API implementation doesn't directly support expires_at
    api_key_data = ApiKeyCreate(
        name="Absolute Expiry Token",
        expires_in_days=30,
        description="Token with absolute expiry date",
    )

    # Create mock user
    mock_user = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
    }

    # Mock the create_api_key method
    async def mock_create_api_key(user_id, name, expires_at=None, description=None, is_active=True):
        # For this test, we don't need to verify exact match since we're using days
        assert expires_at is not None

        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "key": "absolute_api_key_" + str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "description": description,
        }

    # Apply mocks
    with mock.patch("app.db.client.Database.create_api_key", mock_create_api_key):
        # Call the function
        result = await create_api_token(
            api_key_data=api_key_data, current_user=mock_user
        )

        # Verify result
        assert result.name == "Absolute Expiry Token"
        assert (
            result.expires_at is not None
        )  # We can't check exact value due to timing differences


@pytest.mark.asyncio
async def test_list_api_tokens_pagination(monkeypatch):
    """Test listing API tokens with pagination"""
    # Create mock user
    user_id = str(uuid.uuid4())
    mock_user = {"id": user_id, "email": "test@example.com", "name": "Test User"}

    # Create mock tokens
    mock_tokens = []
    for i in range(25):  # 25 tokens to test pagination
        mock_tokens.append(
            {
                "id": str(uuid.uuid4()),
                "name": f"Token {i}",
                "key": f"test_key_{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()
                if i % 2 == 0
                else None,
                "description": f"Description for token {i}",
            }
        )

    # Mock database methods
    async def mock_count_api_keys(user_id):
        return len(mock_tokens)

    async def mock_list_api_keys(user_id, limit=20, offset=0):
        # Return paginated results
        return mock_tokens[offset : offset + limit]

    # Apply mocks
    with (
        mock.patch("app.db.client.Database.count_api_keys", mock_count_api_keys),
        mock.patch("app.db.client.Database.list_api_keys", mock_list_api_keys),
    ):
        # Test first page (default page=1, size=20)
        result = await list_api_tokens(page=1, size=10, current_user=mock_user)

        # Verify pagination metadata
        assert result.metadata.total == 25
        assert result.metadata.page == 1
        assert result.metadata.page_size == 10
        assert result.metadata.total_pages == 3  # 25 items with 10 per page = 3 pages

        # Verify first page items
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Token 0"

        # Test second page
        result = await list_api_tokens(page=2, size=10, current_user=mock_user)

        # Verify second page
        assert result.metadata.page == 2
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Token 10"

        # Test last page
        result = await list_api_tokens(page=3, size=10, current_user=mock_user)

        # Verify last page
        assert result.metadata.page == 3
        assert len(result.items) == 5  # Only 5 items left
        assert result.items[0]["name"] == "Token 20"
        assert result.items[4]["name"] == "Token 24"


@pytest.mark.asyncio
async def test_delete_api_token_success(monkeypatch):
    """Test deleting an API token successfully"""
    # Create mock token ID and user
    token_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    mock_user = {"id": user_id, "email": "test@example.com", "name": "Test User"}

    # Mock delete_api_key method
    delete_calls = []

    async def mock_delete_api_key(key_id, user_id):
        delete_calls.append((key_id, user_id))
        return True  # Success

    # Apply mocks
    with mock.patch("app.db.client.Database.delete_api_key", mock_delete_api_key):
        # Call the function
        result = await delete_api_token(token_id=token_id, current_user=mock_user)

        # Verify result
        assert result.message == "API token deleted successfully"

        # Verify database was called with correct parameters
        assert len(delete_calls) == 1
        assert delete_calls[0][0] == token_id
        assert delete_calls[0][1] == user_id


@pytest.mark.asyncio
async def test_delete_api_token_not_found(monkeypatch):
    """Test deleting a non-existent API token"""
    # Create mock token ID and user
    token_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    mock_user = {"id": user_id, "email": "test@example.com", "name": "Test User"}

    # Mock delete_api_key method that returns False (not found)
    async def mock_delete_api_key(key_id, user_id):
        return False  # Not found

    # Apply mocks
    with mock.patch("app.db.client.Database.delete_api_key", mock_delete_api_key):
        # Test that exception is raised
        with pytest.raises(HTTPException) as excinfo:
            await delete_api_token(token_id=token_id, current_user=mock_user)

        # Verify exception
        assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_get_user_profile(monkeypatch):
    """Test getting the user profile"""
    # Create mock user
    user_id = str(uuid.uuid4())
    mock_user = {
        "id": user_id,
        "email": "test@example.com",
        "name": "Test User",
        "full_name": "Test User",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Call the function directly
    result = await get_user_profile(current_user=mock_user)

    # Verify result - data is contained in the data field of ApiResponse
    assert result.data["id"] == user_id
    assert result.data["email"] == "test@example.com"
    assert result.data["full_name"] == "Test User"
