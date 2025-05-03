import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.api.routes.agents import router
from app.models.schemas import Agent, AgentCreate, AgentUpdate, PaginatedResponse
from app.core.auth import get_current_user_from_api_key

# Mock user for auth dependency
mock_user = {"id": "user123", "email": "test@example.com"}

# Setup auth override
async def override_auth_dependency():
    return mock_user

# Create test app with the agents router
app = FastAPI()
app.include_router(router)

# Override the auth dependency
app.dependency_overrides[get_current_user_from_api_key] = override_auth_dependency
client = TestClient(app)

# Mock agent data
mock_agent = {
    "id": "agent123",
    "name": "Test Agent",
    "description": "Test description",
    "category": "AI",
    "capabilities": [{"name": "testing", "description": "For testing purposes"}],
    "tags": ["test"],
    "version": "1.0.0",
    "author_name": "Test Author",
    "api_endpoint": "https://api.example.com/agent",
    "website_url": "https://example.com/agent",
    "is_team": False,
    "members": [],
    "mode": None,
    "user_id": "user123",
    "created_at": datetime.now().isoformat(),
    "updated_at": None
}

mock_team_agent = {
    "id": "team123",
    "name": "Test Team",
    "description": "Test team description",
    "category": "AI",
    "capabilities": [{"name": "collaboration", "description": "Team collaboration"}],
    "tags": ["team"],
    "version": "1.0.0", 
    "author_name": "Test Author",
    "api_endpoint": "https://api.example.com/team",
    "website_url": "https://example.com/team",
    "is_team": True,
    "members": ["agent1", "agent2"],
    "mode": "collaborate",
    "user_id": "user123",
    "created_at": datetime.now().isoformat(),
    "updated_at": None
}

# Mock verification data
mock_verification = {
    "agent_id": "agent123",
    "did": "did:hibiscus:123456789abcdef",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w==\n-----END PUBLIC KEY-----",
    "verification_method": "mlts",
    "status": "active",
    "deployment_type": "fly.io"
}

# Test for listing agents with pagination
@pytest.mark.asyncio
@patch("app.api.routes.agents.Database")
async def test_list_agents(mock_db):
    # Setup mocks
    mock_db.list_agents = AsyncMock(return_value=[mock_agent, mock_team_agent])
    mock_db.count_agents = AsyncMock(return_value=2)
    
    # Test default list agents
    response = client.get("/agents/")
    assert response.status_code == 200
    data = response.json()
    
    # Check paginated response structure
    assert "items" in data
    assert "metadata" in data
    assert len(data["items"]) == 2
    assert data["metadata"]["total"] == 2
    assert data["metadata"]["page"] == 1
    
    # Test with pagination parameters
    response = client.get("/agents/?page=2&page_size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["page"] == 2
    assert data["metadata"]["page_size"] == 1
    
    # Test with team filter
    mock_db.list_agents = AsyncMock(return_value=[mock_team_agent])
    mock_db.count_agents = AsyncMock(return_value=1)
    
    response = client.get("/agents/?is_team=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["is_team"] == True

# Test for getting a specific agent
@pytest.mark.asyncio
@patch("app.api.routes.agents.Database")
async def test_get_agent(mock_db):
    # Setup mocks
    mock_db.get_agent = AsyncMock(return_value=mock_agent)
    
    # Test successful agent retrieval
    response = client.get("/agents/agent123")
    assert response.status_code == 200
    assert response.json()["id"] == "agent123"
    
    # Test agent not found
    mock_db.get_agent = AsyncMock(return_value=None)
    response = client.get("/agents/nonexistent")
    assert response.status_code == 404

# Test for creating a new agent
@pytest.mark.asyncio
@patch("app.api.routes.agents.Database")
async def test_create_agent(mock_db):
    # Setup mocks
    mock_db.create_agent = AsyncMock(return_value=mock_agent)
    mock_db.create_agent_verification = AsyncMock(return_value=mock_verification)
    mock_db.get_agent = AsyncMock(return_value=None)  # No existing agent with same name
    
    # Create agent data
    new_agent = {
        "name": "New Test Agent",
        "description": "New test description",
        "category": "AI",
        "capabilities": [{"name": "testing", "description": "For testing purposes"}],
        "tags": ["test"],
        "version": "1.0.0",
        "author_name": "Test Author",
        "api_endpoint": "https://api.example.com/agent",
        "website_url": "https://example.com/agent",
        "is_team": False,
        "members": [],
        "mode": None,
        "verification": {
            "did": "did:hibiscus:123456789abcdef",
            "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w==\n-----END PUBLIC KEY-----"
        }
    }
    
    # Test successful agent creation
    response = client.post("/agents/", json=new_agent)
    assert response.status_code == 200
    
    # Test creating a team agent with members
    new_team = {
        "name": "New Team",
        "description": "New team description",
        "category": "AI",
        "capabilities": [{"name": "collaboration", "description": "Team collaboration"}],
        "tags": ["team"],
        "version": "1.0.0",
        "author_name": "Test Author",
        "api_endpoint": "https://api.example.com/team",
        "website_url": "https://example.com/team",
        "is_team": True,
        "members": ["agent1", "agent2"],
        "mode": "collaborate"
    }
    
    mock_db.create_agent = AsyncMock(return_value=mock_team_agent)
    mock_db.get_agent = AsyncMock(return_value={"id": "agent1"})  # For member validation
    
    response = client.post("/agents/", json=new_team)
    assert response.status_code == 200

# Test for updating an agent
@pytest.mark.asyncio
@patch("app.api.routes.agents.Database")
async def test_update_agent(mock_db):
    # Setup mocks
    mock_db.get_agent = AsyncMock(return_value=mock_agent)  # Include user_id for ownership check
    updated_agent = dict(mock_agent)
    updated_agent["description"] = "Updated description"
    mock_db.update_agent = AsyncMock(return_value=updated_agent)
    
    # Update data
    update_data = {
        "description": "Updated description"
    }
    
    # Test successful update - Using PATCH since that's what FastAPI routes typically use
    response = client.patch("/agents/agent123", json=update_data)
    assert response.status_code == 200
    
    # Test updating an agent that doesn't exist
    mock_db.get_agent = AsyncMock(return_value=None)
    response = client.patch("/agents/nonexistent", json=update_data)
    assert response.status_code == 404
    
    # Test updating an agent that belongs to another user
    different_user_agent = dict(mock_agent)
    different_user_agent["user_id"] = "another_user"
    mock_db.get_agent = AsyncMock(return_value=different_user_agent)
    response = client.patch("/agents/agent123", json=update_data)
    assert response.status_code == 403