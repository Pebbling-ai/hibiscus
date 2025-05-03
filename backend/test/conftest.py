import asyncio
import json
import os
import pytest
import uuid
from datetime import datetime, timezone
from unittest import mock
import sys

# Mock the Supabase client
sys.modules['supabase'] = mock.MagicMock()
sys.modules['supabase.client'] = mock.MagicMock()

# Mock dependencies that might not be installed
sys_modules_patcher = mock.patch.dict('sys.modules', {
    'jose': mock.MagicMock(),
    'jose.jwt': mock.MagicMock(),
})
sys_modules_patcher.start()

# Now we can safely import from app
with mock.patch('fastapi.Depends'):
    from app.models.schemas import User, ApiKey

# Test fixtures that will be used across multiple test files
@pytest.fixture
def mock_current_user():
    return User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        full_name="Test User",
        created_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def mock_api_key():
    return ApiKey(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        key="test_api_key",
        name="Test Key",
        created_at=datetime.now(timezone.utc),
        expires_at=None
    )

# Create a proper mock for FastAPI app without importing the actual app
@pytest.fixture
def test_app():
    # Mock FastAPI app
    from fastapi import FastAPI
    app = FastAPI()
    
    # Set up some basic routes for testing
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "test", "timestamp": datetime.now().isoformat()}
    
    return app

# Create a test client
@pytest.fixture
def client(test_app):
    from fastapi.testclient import TestClient
    return TestClient(test_app)

# Mock database responses
@pytest.fixture
def mock_database():
    # Sample data for tests
    federated_registries = [
        {
            "id": str(uuid.uuid4()),
            "name": "Test Registry",
            "url": "https://test-registry.example.com",
            "api_key": "test_key_123",
            "created_at": datetime.now(timezone.utc),
            "last_synced_at": None
        }
    ]
    
    agents = [
        {
            "id": str(uuid.uuid4()),
            "name": "Test Agent",
            "description": "Test agent description",
            "version": "1.0.0",
            "author_name": "Test Author",
            "is_federated": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "user_id": str(uuid.uuid4())
        }
    ]
    
    # Mock database class
    class MockDatabase:
        @staticmethod
        async def list_federated_registries(*args, **kwargs):
            limit = kwargs.get('limit', 100)
            offset = kwargs.get('offset', 0)
            return federated_registries[offset:offset+limit]
        
        @staticmethod
        async def count_federated_registries(*args, **kwargs):
            return len(federated_registries)
        
        @staticmethod
        async def add_federated_registry(registry_data):
            new_registry = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc),
                **registry_data
            }
            federated_registries.append(new_registry)
            return new_registry
        
        @staticmethod
        async def get_federated_registry(registry_id):
            for registry in federated_registries:
                if registry["id"] == registry_id:
                    return registry
            return None
        
        @staticmethod
        async def list_agents(*args, **kwargs):
            limit = kwargs.get('limit', 100)
            offset = kwargs.get('offset', 0)
            registry_id = kwargs.get('registry_id')
            
            if registry_id:
                filtered_agents = [a for a in agents if a.get('registry_id') == registry_id]
                return filtered_agents[offset:offset+limit]
            return agents[offset:offset+limit]
        
        @staticmethod
        async def count_agents(*args, **kwargs):
            registry_id = kwargs.get('registry_id')
            if registry_id:
                return len([a for a in agents if a.get('registry_id') == registry_id])
            return len(agents)
        
        @staticmethod
        async def get_agent_by_federation_id(federation_id, registry_id):
            for agent in agents:
                if agent.get('federation_id') == federation_id and agent.get('registry_id') == registry_id:
                    return agent
            return None
        
        @staticmethod
        async def create_federated_agent(agent_data):
            new_agent = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                **agent_data
            }
            agents.append(new_agent)
            return new_agent
        
        @staticmethod
        async def update_federated_agent(agent_id, agent_data):
            for i, agent in enumerate(agents):
                if agent["id"] == agent_id:
                    agents[i] = {**agent, **agent_data, "updated_at": datetime.now(timezone.utc)}
                    return agents[i]
            return None
        
        @staticmethod
        async def update_federated_registry_sync_time(registry_id):
            for i, registry in enumerate(federated_registries):
                if registry["id"] == registry_id:
                    federated_registries[i]["last_synced_at"] = datetime.now(timezone.utc)
                    return federated_registries[i]
            return None
        
        @staticmethod
        async def create_agent_verification(verification_data):
            return {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc),
                **verification_data
            }
    
    return MockDatabase

@pytest.fixture
def mock_auth_dependency(mock_current_user):
    # Return a mock auth dependency function
    async def mock_get_current_user(*args, **kwargs):
        return mock_current_user
    
    return mock_get_current_user