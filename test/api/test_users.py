import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import uuid
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock the Supabase client for testing."""
    with patch("app.utils.supabase_utils.SupabaseClient.get_client", return_value=MagicMock()) as mock_get_client:
        # Create a mock Supabase client instance
        mock_client = MagicMock()
        
        # Mock the insert execution for users table
        users_insert = MagicMock()
        users_insert.execute.return_value = MagicMock(
            data=[{
                "id": "test-user-id",
                "email": "test@example.com",
                "full_name": "Test User",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }],
            error=None
        )
        
        # Mock the insert execution for api_keys table
        api_keys_insert = MagicMock()
        api_keys_insert.execute.return_value = MagicMock(
            data=[{
                "id": "test-key-id",
                "user_id": "test-user-id",
                "key": "test-session-id",
                "name": "session",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_used_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": None
            }],
            error=None
        )
        
        # Set up the table method to return the mock insert
        mock_client.table.return_value.insert.side_effect = [users_insert, api_keys_insert]
        
        # Make get_client return our mock client
        mock_get_client.return_value = mock_client
        
        yield mock_client


def test_register_user_success(mock_supabase):
    """Test successful user registration."""
    response = client.post(
        "/users/register",
        json={
            "email": "test@example.com",
            "full_name": "Test User"
        },
        headers={"X-API-Key": "test-session-id"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "User registered successfully" in response.json()["message"]
    assert response.json()["data"]["email"] == "test@example.com"
    assert response.json()["data"]["full_name"] == "Test User"
    
    # Verify Supabase was called correctly
    mock_supabase.table.assert_any_call("users")
    mock_supabase.table.assert_any_call("api_keys")
    assert mock_supabase.table.return_value.insert.call_count == 2


def test_register_user_missing_session_id():
    """Test user registration with missing session ID."""
    response = client.post(
        "/users/register",
        json={
            "email": "test@example.com",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 400
    assert "Session ID is required" in response.json()["detail"]


def test_register_user_missing_data():
    """Test user registration with missing user data."""
    response = client.post(
        "/users/register",
        json={
            "email": "test@example.com"
            # Missing full_name
        },
        headers={"X-API-Key": "test-session-id"}
    )
    
    assert response.status_code == 400
    assert "Email and full_name are required" in response.json()["detail"]


@pytest.mark.parametrize("error_table", ["users", "api_keys"])
def test_register_user_database_error(mock_supabase, error_table):
    """Test user registration with database errors."""
    # Reset any previous side effects
    mock_supabase.table.return_value.insert.side_effect = None
    
    # Configure the mock to return an error
    if error_table == "users":
        # First insert (users) fails
        users_insert = MagicMock()
        users_insert.execute.return_value = MagicMock(
            data=None,
            error={"message": "Database error"}
        )
        mock_supabase.table.return_value.insert.side_effect = [users_insert]
    else:
        # First insert (users) succeeds, second insert (api_keys) fails
        users_insert = MagicMock()
        users_insert.execute.return_value = MagicMock(
            data=[{"id": "test-user-id"}],
            error=None
        )
        
        api_keys_insert = MagicMock()
        api_keys_insert.execute.return_value = MagicMock(
            data=None,
            error={"message": "Database error"}
        )
        
        # Mock the delete operation for cleanup
        delete_op = MagicMock()
        delete_op.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "test-user-id"}],
            error=None
        )
        mock_supabase.table.return_value.delete.return_value = delete_op
        
        mock_supabase.table.return_value.insert.side_effect = [users_insert, api_keys_insert]
    
    response = client.post(
        "/users/register",
        json={
            "email": "test@example.com",
            "full_name": "Test User"
        },
        headers={"X-API-Key": "test-session-id"}
    )
    
    assert response.status_code == 500
    assert "Error creating" in response.json()["detail"]
