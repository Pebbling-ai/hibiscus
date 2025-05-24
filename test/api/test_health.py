import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import uuid


# Keep the existing test for the main health endpoint
def test_health_endpoint(client):
    """Test the basic health endpoint works correctly"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


# Test the agent health API endpoints
@pytest.mark.asyncio
@patch("app.api.routes.health.Database")
async def test_agent_health_ping(mock_db, test_app, mock_current_user):
    """Test recording agent health ping"""
    from fastapi.testclient import TestClient
    from app.api.routes.health import router
    from app.core.auth import get_current_user_from_api_key

    # Configure test app and override auth dependency
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_user_from_api_key] = (
        lambda: mock_current_user
    )

    # Setup TestClient
    client = TestClient(test_app)

    # Setup mocks
    timestamp = datetime.now(timezone.utc)
    health_id = str(uuid.uuid4())

    mock_record = {
        "id": health_id,
        "agent_id": "agent123",
        "server_id": "server456",
        "status": "online",
        "last_ping_at": timestamp,
        "metadata": {"cpu_usage": 0.2, "memory_usage": 0.4},
    }
    mock_db.record_agent_health = AsyncMock(return_value=mock_record)

    # Test successful ping
    response = client.post(
        "/health/ping",
        json={
            "agent_id": "agent123",
            "server_id": "server456",
            "status": "online",
            "metadata": {"cpu_usage": 0.2, "memory_usage": 0.4},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == health_id
    assert data["agent_id"] == "agent123"
    assert data["status"] == "online"

    # Test with database error
    mock_db.record_agent_health = AsyncMock(side_effect=Exception("Test error"))
    response = client.post(
        "/health/ping",
        json={"agent_id": "agent123", "server_id": "server456", "status": "online"},
    )
    assert response.status_code == 500


@pytest.mark.asyncio
@patch("app.api.routes.health.Database")
async def test_get_agent_health(mock_db, test_app):
    """Test retrieving health status for a specific agent"""
    from fastapi.testclient import TestClient
    from app.api.routes.health import router

    # Configure test app
    test_app.include_router(router)
    client = TestClient(test_app)

    # Setup mocks
    timestamp = datetime.now(timezone.utc)
    mock_records = [
        {
            "id": str(uuid.uuid4()),
            "agent_id": "agent123",
            "server_id": "server456",
            "status": "online",
            "last_ping_at": timestamp,
            "metadata": {},
        }
    ]
    mock_db.get_agent_health = AsyncMock(return_value=mock_records)

    # Test successful retrieval
    response = client.get("/health/agents/agent123")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agent_id"] == "agent123"
    assert "id" in data[0]
    assert "last_ping_at" in data[0]

    # Test with no records found
    mock_db.get_agent_health = AsyncMock(return_value=[])
    response = client.get("/health/agents/nonexistent")
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Test with database error
    mock_db.get_agent_health = AsyncMock(side_effect=Exception("Test error"))
    response = client.get("/health/agents/agent123")
    assert response.status_code == 500


@pytest.mark.asyncio
@patch("app.api.routes.health.Database")
async def test_list_agent_health(mock_db, test_app):
    """Test listing health status for all agents with pagination"""
    from fastapi.testclient import TestClient
    from app.api.routes.health import router

    # Configure test app
    test_app.include_router(router)
    client = TestClient(test_app)

    # Setup mocks
    timestamp = datetime.now(timezone.utc)
    mock_records = [
        {
            "id": str(uuid.uuid4()),
            "agent_id": "agent1",
            "server_id": "server1",
            "status": "online",
            "last_ping_at": timestamp,
            "metadata": {},
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "agent2",
            "server_id": "server1",
            "status": "offline",
            "last_ping_at": timestamp,
            "metadata": {},
        },
    ]
    mock_db.list_agent_health = AsyncMock(return_value=mock_records)
    mock_db.count_agent_health = AsyncMock(return_value=2)

    # Test default pagination
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["metadata"]["total"] == 2
    assert "id" in data["items"][0]
    assert "last_ping_at" in data["items"][0]

    # Test custom pagination
    response = client.get("/health/?page=2&size=1")
    assert response.status_code == 200

    # Test server filter
    mock_db.list_agent_health = AsyncMock(return_value=[mock_records[0]])
    mock_db.count_agent_health = AsyncMock(return_value=1)
    response = client.get("/health/?server_id=server1")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    # Test with database error
    mock_db.list_agent_health = AsyncMock(side_effect=Exception("Test error"))
    response = client.get("/health/")
    assert response.status_code == 500


@pytest.mark.asyncio
@patch("app.api.routes.health.Database")
async def test_get_agent_health_summary(mock_db, test_app):
    """Test retrieving agent health summary"""
    from fastapi.testclient import TestClient
    from app.api.routes.health import router

    # Configure test app
    test_app.include_router(router)
    client = TestClient(test_app)

    # Setup mocks
    timestamp = datetime.now(timezone.utc)
    mock_summary = [
        {
            "agent_id": "agent1",
            "agent_name": "Test Agent 1",
            "status": "online",
            "servers": [
                {"server_id": "server1", "status": "online", "last_ping_at": timestamp}
            ],
            "last_ping_at": timestamp,
        }
    ]
    mock_db.get_agent_health_summary = AsyncMock(return_value=mock_summary)

    # Test successful retrieval
    response = client.get("/health/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agent_id"] == "agent1"
    assert "servers" in data[0]
    assert "status" in data[0]
    assert "last_ping_at" in data[0]

    # Test with no records
    mock_db.get_agent_health_summary = AsyncMock(return_value=[])
    response = client.get("/health/summary")
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Test with database error
    mock_db.get_agent_health_summary = AsyncMock(side_effect=Exception("Test error"))
    response = client.get("/health/summary")
    assert response.status_code == 500
