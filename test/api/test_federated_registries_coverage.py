import json
import pytest
import uuid
from unittest import mock
from datetime import datetime, timezone
import httpx
from fastapi import BackgroundTasks, HTTPException, status
from app.api.routes.federated_registries import (
    list_federated_registries,
    add_federated_registry,
    sync_federated_registry,
    list_federated_registry_agents,
    sync_registry_agents,
)
from app.models.schemas import FederatedRegistryCreate


# Test listing federated registries with pagination
@pytest.mark.asyncio
async def test_list_federated_registries_pagination(monkeypatch):
    """Test listing federated registries with pagination support"""
    # Create mock registries
    mock_registries = [
        {
            "id": str(uuid.uuid4()),
            "name": f"Registry {i}",
            "url": f"https://registry-{i}.example.com",
            "api_key": f"key_{i}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_synced_at": None,
        }
        for i in range(1, 26)
    ]  # 25 registries

    # Mock database methods
    async def mock_count_registries():
        return len(mock_registries)

    async def mock_list_registries(limit=20, offset=0):
        return mock_registries[offset : offset + limit]

    # Apply mocks
    with (
        mock.patch(
            "app.db.client.Database.count_federated_registries", mock_count_registries
        ),
        mock.patch(
            "app.db.client.Database.list_federated_registries", mock_list_registries
        ),
    ):
        # Test first page
        result = await list_federated_registries(
            page=1, size=10, current_user={"id": "test-user"}
        )

        # Verify pagination metadata
        assert result.metadata.total == 25
        assert result.metadata.page == 1
        assert result.metadata.page_size == 10
        assert result.metadata.total_pages == 3  # 25 items with 10 per page = 3 pages

        # Verify we have the first 10 items
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Registry 1"
        assert result.items[9]["name"] == "Registry 10"

        # Test second page
        result = await list_federated_registries(
            page=2, size=10, current_user={"id": "test-user"}
        )

        # Verify second page
        assert result.metadata.page == 2
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Registry 11"

        # Test last page (with less than page size)
        result = await list_federated_registries(
            page=3, size=10, current_user={"id": "test-user"}
        )

        # Verify last page
        assert result.metadata.page == 3
        assert len(result.items) == 5  # Only 5 items left
        assert result.items[0]["name"] == "Registry 21"
        assert result.items[4]["name"] == "Registry 25"


# Test adding a new federated registry
@pytest.mark.asyncio
async def test_add_federated_registry_success(monkeypatch):
    """Test adding a new federated registry with successful validation"""
    # Create registry data
    registry = FederatedRegistryCreate(
        name="New Test Registry",
        url="https://valid-registry.example.com",
        api_key="valid_key",
    )

    # Mock HTTP client for URL validation
    class MockHTTPClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            # Simulate successful response
            response = mock.MagicMock()
            response.raise_for_status = mock.MagicMock()  # Does nothing (success)
            return response

    # Mock database method
    async def mock_add_registry(data):
        return {
            "id": str(uuid.uuid4()),
            **data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_synced_at": None,
        }

    # Apply mocks
    with (
        mock.patch("httpx.AsyncClient", return_value=MockHTTPClient()),
        mock.patch("app.db.client.Database.add_federated_registry", mock_add_registry),
    ):
        # Test adding registry
        result = await add_federated_registry(
            registry=registry, current_user={"id": "test-user"}
        )

        # Verify result
        assert result["name"] == "New Test Registry"
        assert result["url"] == "https://valid-registry.example.com"
        assert result["api_key"] == "valid_key"
        assert "id" in result
        assert "created_at" in result


@pytest.mark.asyncio
async def test_add_federated_registry_validation_failure(monkeypatch):
    """Test adding a federated registry with validation failure"""
    # Create registry data
    registry = FederatedRegistryCreate(
        name="Invalid Registry",
        url="https://invalid-registry.example.com",
        api_key="invalid_key",
    )

    # Mock HTTP client that raises an error during validation
    class MockHTTPClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            # Simulate connection error
            raise httpx.HTTPError("Failed to connect")

    # Apply mocks
    with mock.patch("httpx.AsyncClient", return_value=MockHTTPClient()):
        # Test adding invalid registry - should raise exception
        with pytest.raises(HTTPException) as excinfo:
            await add_federated_registry(
                registry=registry, current_user={"id": "test-user"}
            )

        # Verify exception
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Failed to connect" in excinfo.value.detail


@pytest.mark.asyncio
async def test_sync_federated_registry_background(monkeypatch):
    """Test syncing a federated registry in the background"""
    # Create a registry ID
    registry_id = str(uuid.uuid4())

    # Mock registry data
    mock_registry = {
        "id": registry_id,
        "name": "Test Registry",
        "url": "https://test-registry.example.com",
        "api_key": "test_key",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_synced_at": None,
    }

    # Mock get_federated_registry
    async def mock_get_registry(id):
        if id == registry_id:
            return mock_registry
        return None

    # Create a mock background tasks object
    background_tasks = BackgroundTasks()
    add_task_spy = mock.MagicMock()
    background_tasks.add_task = add_task_spy

    # Apply mocks
    with mock.patch("app.db.client.Database.get_federated_registry", mock_get_registry):
        # Test sync registry with background tasks
        result = await sync_federated_registry(
            registry_id=registry_id,
            background_tasks=background_tasks,
            current_user={"id": "test-user"},
        )

        # Verify result is successful and has a message
        assert result.success is True
        assert result.message is not None
        assert "Synchronization with Test Registry started" in result.message

        # Verify background task was added with correct parameters
        add_task_spy.assert_called_once()
        # Check that the function and registry were passed correctly
        call_args = add_task_spy.call_args[0]
        assert "sync_registry_agents" in str(call_args[0])
        # Check registry is in the arguments but don't do a direct comparison
        assert registry_id in str(call_args)


@pytest.mark.asyncio
async def test_sync_federated_registry_not_found(monkeypatch):
    """Test syncing a non-existent federated registry"""
    # Create a non-existent registry ID
    registry_id = str(uuid.uuid4())

    # Mock get_federated_registry to return None
    async def mock_get_registry(id):
        return None

    # Create a mock background tasks object
    background_tasks = BackgroundTasks()

    # Apply mocks
    with mock.patch("app.db.client.Database.get_federated_registry", mock_get_registry):
        # Test sync registry with non-existent ID - should raise exception
        with pytest.raises(HTTPException) as excinfo:
            await sync_federated_registry(
                registry_id=registry_id,
                background_tasks=background_tasks,
                current_user={"id": "test-user"},
            )

        # Verify exception
        assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Federated registry not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_list_federated_registry_agents_pagination(monkeypatch):
    """Test listing agents from a federated registry with pagination"""
    # Create registry ID and agent mocks
    registry_id = str(uuid.uuid4())

    # Mock registry data
    mock_registry = {
        "id": registry_id,
        "name": "Test Registry",
        "url": "https://test-registry.example.com",
        "api_key": "test_key",
    }

    # Create mock agents with verification data
    mock_agents = []
    for i in range(25):  # 25 agents to test pagination
        agent_id = str(uuid.uuid4())

        # Create a DID document for each agent
        did_document = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": f"did:hibiscus:agent{i}",
            "authentication": [
                {
                    "id": f"did:hibiscus:agent{i}#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": f"did:hibiscus:agent{i}",
                    "publicKeyBase58": f"public-key-{i}",
                }
            ],
        }

        # Create agent with proper verification data
        mock_agents.append(
            {
                "id": agent_id,
                "name": f"Agent {i}",
                "description": f"Description for Agent {i}",
                "capabilities": json.dumps([{"name": f"capability_{i}"}]),
                "tags": json.dumps([f"tag_{i}"]),
                "registry_id": registry_id,
                "is_federated": True,
                "federation_id": str(uuid.uuid4()),
                "did": f"did:hibiscus:agent{i}",
                "public_key": f"public-key-{i}",
                "did_document": json.dumps(did_document),
            }
        )

    # Mock database methods
    async def mock_get_registry(id):
        if id == registry_id:
            return mock_registry
        return None

    async def mock_count_agents(registry_id=None):
        return 25

    async def mock_list_agents(
        limit=20, offset=0, search_term=None, is_team=None, registry_id=None
    ):
        if registry_id != mock_registry["id"]:
            return []

        # Return paginated results
        agents_page = mock_agents[offset : offset + limit]
        return agents_page

    # Apply mocks
    with (
        mock.patch("app.db.client.Database.get_federated_registry", mock_get_registry),
        mock.patch("app.db.client.Database.count_agents", mock_count_agents),
        mock.patch("app.db.client.Database.list_agents", mock_list_agents),
    ):
        # Test first page
        result = await list_federated_registry_agents(
            registry_id=registry_id, page=1, size=10, current_user={"id": "test-user"}
        )

        # Verify pagination metadata
        assert result.metadata.total == 25
        assert result.metadata.page == 1
        assert result.metadata.page_size == 10
        assert result.metadata.total_pages == 3  # 25 items with 10 per page = 3 pages

        # Verify first page items
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Agent 0"

        # Test handling verification data
        assert "did" in result.items[0]
        assert "public_key" in result.items[0]
        assert result.items[0]["did"] == "did:hibiscus:agent0"

        # Test second page
        result = await list_federated_registry_agents(
            registry_id=registry_id, page=2, size=10, current_user={"id": "test-user"}
        )

        # Verify second page
        assert result.metadata.page == 2
        assert len(result.items) == 10
        assert result.items[0]["name"] == "Agent 10"


@pytest.mark.asyncio
async def test_list_federated_registry_agents_not_found(monkeypatch):
    """Test listing agents from a non-existent registry"""
    # Create a non-existent registry ID
    registry_id = str(uuid.uuid4())

    # Mock get_federated_registry to return None
    async def mock_get_registry(id):
        return None

    # Apply mocks
    with mock.patch("app.db.client.Database.get_federated_registry", mock_get_registry):
        # Test listing agents with non-existent registry - should raise exception
        with pytest.raises(HTTPException) as excinfo:
            await list_federated_registry_agents(
                registry_id=registry_id,
                page=1,
                size=10,
                current_user={"id": "test-user"},
            )

        # Verify exception
        assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Federated registry not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_sync_registry_agents_with_did_verification(monkeypatch):
    """Test syncing agents with DID verification from a federated registry"""
    # Create registry data
    registry_id = str(uuid.uuid4())
    registry = {
        "id": registry_id,
        "name": "DID Verification Registry",
        "url": "https://did-registry.example.com",
        "api_key": "did_key",
    }

    # Create remote agents with DIDs and verification data
    remote_agents = []
    for i in range(5):
        # Create verification data with DIDs and public keys
        verification = {
            "did": f"did:hibiscus:remote{i}",
            "public_key": f"pk-{i}",
            "did_document": {
                "@context": "https://www.w3.org/ns/did/v1",
                "id": f"did:hibiscus:remote{i}",
                "authentication": [
                    {
                        "id": f"did:hibiscus:remote{i}#keys-1",
                        "type": "Ed25519VerificationKey2018",
                        "controller": f"did:hibiscus:remote{i}",
                        "publicKeyBase58": f"pk-{i}",
                    }
                ],
            },
        }

        # Add agent with verification
        remote_agents.append(
            {
                "id": str(uuid.uuid4()),
                "name": f"Remote Agent {i}",
                "description": f"Remote agent with DID {i}",
                "verification": verification,
                "capabilities": [{"name": f"capability_{i}"}],
                "tags": [f"tag_{i}"],
            }
        )

    # Mock HTTP client for fetching remote agents
    class MockHTTPClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers=None, **kwargs):
            # Return paginated response with agents
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "items": remote_agents,
                "metadata": {
                    "total": len(remote_agents),
                    "page": 1,
                    "page_size": len(remote_agents),
                    "total_pages": 1,
                },
            }
            return response

    # Mock database methods
    get_agent_calls = []
    create_agent_calls = []
    update_sync_time_calls = []
    create_verification_calls = []

    async def mock_get_agent_by_federation_id(federation_id, registry_id):
        get_agent_calls.append((federation_id, registry_id))
        return None  # Assume agent doesn't exist

    async def mock_create_federated_agent(agent_data):
        create_agent_calls.append(agent_data)
        return {"id": str(uuid.uuid4()), **agent_data}

    async def mock_update_sync_time(registry_id):
        update_sync_time_calls.append(registry_id)
        return {
            "id": registry_id,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }

    async def mock_create_verification(verification_data):
        create_verification_calls.append(verification_data)
        return verification_data

    # Apply mocks
    with (
        mock.patch("httpx.AsyncClient", return_value=MockHTTPClient()),
        mock.patch(
            "app.db.client.Database.get_agent_by_federation_id",
            mock_get_agent_by_federation_id,
        ),
        mock.patch(
            "app.db.client.Database.create_federated_agent", mock_create_federated_agent
        ),
        mock.patch(
            "app.db.client.Database.update_federated_registry_sync_time",
            mock_update_sync_time,
        ),
        mock.patch(
            "app.db.client.Database.create_agent_verification", mock_create_verification
        ),
    ):
        # Run the sync function
        await sync_registry_agents(registry)

        # Verify agents were created
        assert len(create_agent_calls) == 5

        # Verify each agent has federation_id from remote and verification data was stored
        for i, agent_data in enumerate(create_agent_calls):
            # Check federation_id was set
            assert "federation_id" in agent_data
            assert agent_data["name"] == f"Remote Agent {i}"

            # Check verification data was correctly processed
            assert len(create_verification_calls) == 5
            verification = create_verification_calls[i]
            assert verification["did"] == f"did:hibiscus:remote{i}"
            assert verification["public_key"] == f"pk-{i}"
            assert "did_document" in verification

        # Verify sync time was updated
        assert len(update_sync_time_calls) == 1
        assert update_sync_time_calls[0] == registry_id
