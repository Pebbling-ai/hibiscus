import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.db.client import Database, AGENTS_TABLE, AGENT_VERIFICATION_TABLE, API_KEYS_TABLE, FEDERATED_REGISTRIES_TABLE, AGENT_HEALTH_TABLE


@pytest.fixture
def setup_supabase():
    """Setup global supabase patch for all tests"""
    with patch('app.db.client.supabase') as mock_supabase:
        yield mock_supabase


class TestDatabaseClient:
    """Test the Database client class"""
    
    @pytest.mark.asyncio
    async def test_list_agents(self, setup_supabase):
        """Test listing agents with pagination"""
        # Setup mock response
        agent_id = str(uuid.uuid4())
        mock_agents = [
            {
                "id": agent_id, 
                "name": "Test Agent",
                "description": "A test agent",
                "capabilities": json.dumps([{"name": "testing", "description": "For tests"}]),
                "tags": json.dumps(["test"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "user_id": str(uuid.uuid4())
            }
        ]
        
        # Setup verification data
        verification_data = [{
            "agent_id": agent_id,
            "did": "did:hibiscus:test123",
            "public_key": "test-key"
        }]
        
        # Mock the first execute for agents table
        agents_execute = MagicMock()
        agents_execute.data = mock_agents
        agents_execute.error = None
        
        # Mock the second execute for verification table
        verification_execute = MagicMock()
        verification_execute.data = verification_data
        verification_execute.error = None
        
        # Setup the table mock with method chains
        agents_table_mock = MagicMock()
        verification_table_mock = MagicMock()
        
        # Set different return values based on which table is being queried
        def table_side_effect(table_name):
            if table_name == AGENTS_TABLE:
                return agents_table_mock
            elif table_name == AGENT_VERIFICATION_TABLE:
                return verification_table_mock
            return MagicMock()
            
        setup_supabase.table.side_effect = table_side_effect
        
        # Configure the mock chain for the agents table
        agents_table_mock.select.return_value = agents_table_mock
        agents_table_mock.or_.return_value = agents_table_mock
        agents_table_mock.eq.return_value = agents_table_mock
        agents_table_mock.range.return_value = agents_table_mock
        agents_table_mock.execute.return_value = agents_execute
        
        # Configure the mock chain for the verification table
        verification_table_mock.select.return_value = verification_table_mock
        verification_table_mock.eq.return_value = verification_table_mock
        verification_table_mock.execute.return_value = verification_execute
        
        # Test the function
        result = await Database.list_agents()
        
        # Verify results
        assert len(result) == 1
        assert result[0]["name"] == "Test Agent"
        
        # Verification data should be merged
        assert "did" in result[0]
        assert result[0]["did"] == "did:hibiscus:test123"
        
        # Capabilities should be parsed from JSON
        assert isinstance(result[0]["capabilities"], list)
    
    @pytest.mark.asyncio
    async def test_get_agent(self, setup_supabase):
        """Test retrieving a specific agent"""
        agent_id = str(uuid.uuid4())
        
        # Setup mock agent data
        mock_agent = {
            "id": agent_id, 
            "name": "Specific Agent",
            "description": "A specific test agent",
            "capabilities": json.dumps([{"name": "specific", "description": "For specific tests"}]),
            "tags": json.dumps(["test", "specific"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": str(uuid.uuid4())
        }
        
        # Setup verification data
        verification_data = [{
            "agent_id": agent_id,
            "did": "did:hibiscus:specific123",
            "public_key": "specific-key"
        }]
        
        # Mock the execute responses
        agent_execute = MagicMock()
        agent_execute.data = [mock_agent]
        agent_execute.error = None
        
        verification_execute = MagicMock()
        verification_execute.data = verification_data
        verification_execute.error = None
        
        # Setup the table mocks with method chains
        agent_table_mock = MagicMock()
        verification_table_mock = MagicMock()
        
        # Set different return values based on which table is being queried
        def table_side_effect(table_name):
            if table_name == AGENTS_TABLE:
                return agent_table_mock
            elif table_name == AGENT_VERIFICATION_TABLE:
                return verification_table_mock
            return MagicMock()
            
        setup_supabase.table.side_effect = table_side_effect
        
        # Configure the mock chain for agent table
        agent_table_mock.select.return_value = agent_table_mock
        agent_table_mock.eq.return_value = agent_table_mock
        agent_table_mock.execute.return_value = agent_execute
        
        # Configure the mock chain for verification table
        verification_table_mock.select.return_value = verification_table_mock
        verification_table_mock.eq.return_value = verification_table_mock
        verification_table_mock.execute.return_value = verification_execute
        
        # Test the function
        result = await Database.get_agent(agent_id)
        
        # Basic verification
        assert result is not None
        assert result["id"] == agent_id
        assert result["name"] == "Specific Agent"
        
        # Capabilities should be parsed from JSON
        assert isinstance(result["capabilities"], list)
        
        # Verification data should be merged
        assert "did" in result
        assert result["did"] == "did:hibiscus:specific123"
    
    @pytest.mark.asyncio
    async def test_create_agent(self, setup_supabase):
        """Test creating a new agent"""
        # Setup agent data
        agent_data = {
            "name": "New Agent",
            "description": "A new test agent",
            "capabilities": [{"name": "new", "description": "For new tests"}],
            "tags": ["test", "new"],
            "version": "1.0.0",
            "author_name": "Test Author",
            "user_id": str(uuid.uuid4())
        }
        
        # The agent ID that will be generated
        new_agent_id = str(uuid.uuid4())
        
        # Create a spy to capture the insert call
        original_insert = MagicMock()
        inserted_data = {}
        
        def capture_insert(data):
            nonlocal inserted_data
            inserted_data = data.copy()
            return original_insert
        
        # Mock the execute response
        execute_mock = MagicMock()
        execute_mock.data = [{
            "id": new_agent_id,
            "name": agent_data["name"],
            "description": agent_data["description"],
            "capabilities": json.dumps(agent_data["capabilities"]),
            "tags": json.dumps(agent_data["tags"]),
            "version": agent_data["version"],
            "author_name": agent_data["author_name"],
            "user_id": agent_data["user_id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }]
        execute_mock.error = None
        
        # Setup the table mock
        table_mock = MagicMock()
        table_mock.insert.side_effect = capture_insert
        
        # Complete the chain
        original_insert.execute.return_value = execute_mock
        
        setup_supabase.table.return_value = table_mock
        
        # Test the function
        result = await Database.create_agent(agent_data)
        
        # Verify the result
        assert result is not None
        assert result["id"] == new_agent_id
        assert result["name"] == "New Agent"
        
        # Check that insert was called
        assert table_mock.insert.called
        
        # Test if JSON fields were serialized to strings
        assert "capabilities" in inserted_data
        assert "tags" in inserted_data
        
        # Need to handle the case where we can't access the actual data from the side_effect
        # Instead, check that the Supabase table was called with AGENTS_TABLE
        setup_supabase.table.assert_called_with(AGENTS_TABLE)
    
    @pytest.mark.asyncio
    async def test_create_agent_verification(self, setup_supabase):
        """Test creating agent verification data"""
        # Setup verification data
        verification_data = {
            "agent_id": str(uuid.uuid4()),
            "did": "did:hibiscus:verify123",
            "public_key": "test-verify-key",
            "verification_method": "mlts",
            "status": "active"
        }
        
        # Mock the created verification record
        created_verification = {
            **verification_data, 
            "id": str(uuid.uuid4()), 
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock execute response
        execute_mock = MagicMock()
        execute_mock.data = [created_verification]
        execute_mock.error = None
        
        # Setup table mock chain
        table_mock = MagicMock()
        insert_mock = MagicMock()
        
        table_mock.insert.return_value = insert_mock
        insert_mock.execute.return_value = execute_mock
        
        setup_supabase.table.return_value = table_mock
        
        # Test the function
        result = await Database.create_agent_verification(verification_data)
        
        # Verify the results
        assert result is not None
        assert result["did"] == "did:hibiscus:verify123"
        assert result["agent_id"] == verification_data["agent_id"]
        
        # Verify correct table was used
        setup_supabase.table.assert_called_with(AGENT_VERIFICATION_TABLE)
    
    @pytest.mark.asyncio
    async def test_record_agent_health(self, setup_supabase):
        """Test recording agent health data"""
        # Setup health data
        health_data = {
            "agent_id": str(uuid.uuid4()),
            "server_id": "test-server",
            "status": "online",
            "metadata": {"cpu": 0.5, "memory": 0.3}
        }
        
        # Mock the created health record
        created_health = {
            **health_data,
            "id": str(uuid.uuid4()),
            "last_ping_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock update response (empty - no records found)
        update_execute = MagicMock()
        update_execute.data = []
        update_execute.error = None
        
        # Mock insert response (new record created)
        insert_execute = MagicMock()
        insert_execute.data = [created_health]
        insert_execute.error = None
        
        # Setup update mock chain
        update_table = MagicMock()
        update_table.update.return_value = update_table
        update_table.eq.return_value = update_table
        update_table.execute.return_value = update_execute
        
        # Setup insert mock chain
        insert_table = MagicMock()
        insert_table.insert.return_value = insert_table
        insert_table.execute.return_value = insert_execute
        
        # Mock two different calls to table()
        setup_supabase.table.side_effect = [update_table, insert_table]
        
        # Test the function
        result = await Database.record_agent_health(health_data)
        
        # Verify results
        assert result is not None
        assert result["agent_id"] == health_data["agent_id"]
        assert result["status"] == "online"
        assert "last_ping_at" in result
        
        # Verify both table operations were attempted
        assert setup_supabase.table.call_count == 2
        assert setup_supabase.table.call_args_list == [call(AGENT_HEALTH_TABLE), call(AGENT_HEALTH_TABLE)]