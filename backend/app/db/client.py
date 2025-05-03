import os
import json
import secrets
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Table names
AGENTS_TABLE = "agents"
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"
FEDERATED_REGISTRIES_TABLE = "federated_registries"
AGENT_HEALTH_TABLE = "agent_health"
AGENT_VERIFICATION_TABLE = "agent_verification"

# Initialize Supabase client
superbase_url = os.getenv("SUPERBASE_URL")
superbase_key = os.getenv("SUPERBASE_SERVICE_ROLE_KEY", os.getenv("SUPERBASE_KEY"))

if not superbase_url or not superbase_key:
    print("Warning: SUPERBASE_URL and SUPERBASE_KEY not set. Using mock database for development.")
    supabase = None
else:
    supabase: Client = create_client(superbase_url, superbase_key)

# Mock data for development without a Supabase connection
MOCK_DB = {
    AGENTS_TABLE: [
        {
            "id": "74a0d5e0-3b8c-4199-84fc-adcb1bc25e76",
            "name": "Text Generation Assistant",
            "description": "AI assistant for generating and editing text content",
            "category": "text",
            "capabilities": ["text_generation", "editing", "summarization"],
            "api_endpoint": "https://api.example.com/text-assistant",
            "website_url": "https://example.com/text-assistant",
            "logo_url": "https://example.com/logos/text-assistant.png",
            "is_federated": False,
            "federation_source": None,
            "owner_id": "6c84fb90-12c4-11e1-840d-7b25c5ee775a",
            "created_at": "2023-01-15T12:00:00",
            "updated_at": "2023-01-15T12:00:00"
        },
        {
            "id": "8f7e6d5c-4b3a-2c1d-0e9f-8a7b6c5d4e3f",
            "name": "Image Generator",
            "description": "AI agent for generating images from text descriptions",
            "category": "image",
            "capabilities": ["image_generation", "style_transfer"],
            "api_endpoint": "https://api.example.com/image-generator",
            "website_url": "https://example.com/image-generator",
            "logo_url": "https://example.com/logos/image-generator.png",
            "is_federated": False,
            "federation_source": None,
            "owner_id": "6c84fb90-12c4-11e1-840d-7b25c5ee775a",
            "created_at": "2023-02-20T15:30:00",
            "updated_at": "2023-02-20T15:30:00"
        }
    ],
    USERS_TABLE: [
        {
            "id": "6c84fb90-12c4-11e1-840d-7b25c5ee775a",
            "email": "user@example.com",
            "full_name": "Demo User",
            "created_at": "2023-01-01T10:00:00",
            "updated_at": None
        }
    ],
    API_KEYS_TABLE: [
        {
            "id": "abcdef12-3456-7890-abcd-ef1234567890",
            "user_id": "6c84fb90-12c4-11e1-840d-7b25c5ee775a",
            "key": "test_api_key_12345",
            "name": "Test API Key",
            "created_at": "2023-01-05T11:00:00",
            "last_used_at": None,
            "expires_at": None
        }
    ],
    FEDERATED_REGISTRIES_TABLE: [
        {
            "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
            "name": "Partner Registry",
            "url": "https://partner-registry.example.com",
            "api_key": "partner_api_key_67890",
            "created_at": "2023-03-10T09:15:00",
            "last_synced_at": "2023-05-01T14:30:00"
        }
    ],
    AGENT_HEALTH_TABLE: [],
    AGENT_VERIFICATION_TABLE: []
}


class Database:
    @staticmethod
    async def _execute_query(table: str, query_fn=None) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Execute a query against Supabase or mock database.
        """
        if supabase is None:
            # Use mock database
            if query_fn is None:
                return MOCK_DB.get(table, [])
            return query_fn(MOCK_DB.get(table, []))
        
        # Use real Supabase client
        return query_fn(supabase)
    
    @staticmethod
    async def list_agents(limit: int = 100, offset: int = 0, search_term: Optional[str] = None, is_team: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        List all agents with optional filtering and deserialize JSON fields.
        Include verification data from agent_verification table.
        """
        # Use Supabase
        query = supabase.table(AGENTS_TABLE).select("*")
        
        # Apply search filter if provided
        if search_term:
            search_term = search_term.lower()
            query = query.or_(f"name.ilike.%{search_term}%,description.ilike.%{search_term}%,documentation.ilike.%{search_term}%")
        
        # Apply team filter if provided
        if is_team is not None:
            query = query.eq("is_team", is_team)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agents: {response.error.message}")
        
        # Parse JSON fields for each agent
        parsed_agents = []
        for agent in response.data:
            parsed_agent = Database._parse_agent_json_fields(agent)
            
            # Fetch verification data for this agent
            verification_query = supabase.table(AGENT_VERIFICATION_TABLE).select("*").eq("agent_id", agent["id"]).execute()
            
            if not hasattr(verification_query, "error") and verification_query.data:
                verification = verification_query.data[0]
                
                # Add verification fields to agent data
                parsed_agent["did"] = verification.get("did")
                parsed_agent["public_key"] = verification.get("public_key")
                
                # Parse did_document if it exists
                if verification.get("did_document"):
                    if isinstance(verification["did_document"], str):
                        try:
                            parsed_agent["did_document"] = json.loads(verification["did_document"])
                        except json.JSONDecodeError:
                            parsed_agent["did_document"] = verification["did_document"]
                    else:
                        parsed_agent["did_document"] = verification["did_document"]
            
            parsed_agents.append(parsed_agent)
            
        return parsed_agents

    @staticmethod
    async def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent by ID and deserialize JSON fields.
        Include verification data from agent_verification table.
        """
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).select("*").eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agent: {response.error.message}")
        
        if not response.data:
            return None
        
        # Parse JSON fields
        agent = Database._parse_agent_json_fields(response.data[0])
        
        # Fetch verification data for this agent
        verification_query = supabase.table(AGENT_VERIFICATION_TABLE).select("*").eq("agent_id", agent_id).execute()
        
        if not hasattr(verification_query, "error") and verification_query.data:
            verification = verification_query.data[0]
            
            # Add verification fields to agent data
            agent["did"] = verification.get("did")
            agent["public_key"] = verification.get("public_key")
            
            # Parse did_document if it exists
            if verification.get("did_document"):
                if isinstance(verification["did_document"], str):
                    try:
                        agent["did_document"] = json.loads(verification["did_document"])
                    except json.JSONDecodeError:
                        agent["did_document"] = verification["did_document"]
                else:
                    agent["did_document"] = verification["did_document"]
        
        return agent

    @staticmethod
    def _parse_agent_json_fields(agent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON fields that might be stored as strings.
        """
        # Parse JSON fields that might be stored as strings
        for field in ['capabilities', 'metadata', 'links', 'dependencies']:
            if field in agent and isinstance(agent[field], str):
                agent[field] = json.loads(agent[field])
        
        return agent

    @staticmethod
    async def create_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent with the given data following the Agent Communication Protocol standard.
        
        The agent_data should include:
        - name: RFC 1123 DNS-label compatible name
        - description: Human-readable description
        - documentation: (Optional) Full markdown documentation
        - capabilities: (Optional) List of capability objects with name and description
        - domains: (Optional) List of domain strings
        - tags: (Optional) List of tag strings
        - metadata: (Optional) Object containing framework, programming_language, license, etc.
        - links: (Optional) List of link objects with type and URL
        - dependencies: (Optional) List of dependency objects
        - version: Version string
        - author_name: Name of the agent's author
        - author_url: (Optional) URL for the author
        - api_endpoint: (Optional) URL for the agent's API
        - website_url: (Optional) URL for the agent's website
        - logo_url: (Optional) URL for the agent's logo
        - is_federated: Boolean indicating if the agent is from a federated registry
        - federation_source: (Optional) Source registry of a federated agent
        - user_id: ID of the user creating the agent
        """
        agent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Handle json serialization for complex fields
        agent_data_copy = agent_data.copy()
        
        # Convert capabilities, metadata, links, and dependencies to JSON if they exist
        for field in ['capabilities', 'metadata', 'links', 'dependencies']:
            if field in agent_data_copy and agent_data_copy[field] is not None:
                agent_data_copy[field] = json.dumps(agent_data_copy[field])
        
        # Prepare the agent data
        agent = {
            "id": agent_id,
            "created_at": now,
            "updated_at": now,
            **agent_data_copy
        }
        
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).insert(agent).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating agent: {response.error.message}")
        
        return response.data[0] if response.data else agent
        
    @staticmethod
    async def update_agent(agent_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing agent with the given data following the Agent Communication Protocol standard.
        
        The update_data can include any subset of fields from AgentUpdate model:
        - name: RFC 1123 DNS-label compatible name
        - description: Human-readable description
        - documentation: Full markdown documentation
        - capabilities: List of capability objects with name and description
        - domains: List of domain strings
        - tags: List of tag strings
        - metadata: Object containing framework, programming_language, license, etc.
        - links: List of link objects with type and URL
        - dependencies: List of dependency objects
        - version: Version string
        - author_name: Name of the agent's author
        - author_url: URL for the author
        - api_endpoint: URL for the agent's API
        - website_url: URL for the agent's website
        - logo_url: URL for the agent's logo
        """
        # Make a copy so we don't modify the original
        update_data_copy = update_data.copy()
        update_data_copy["updated_at"] = datetime.utcnow().isoformat()
        
        # Convert capabilities, metadata, links, and dependencies to JSON if they exist
        for field in ['capabilities', 'metadata', 'links', 'dependencies']:
            if field in update_data_copy and update_data_copy[field] is not None:
                update_data_copy[field] = json.dumps(update_data_copy[field])
        
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            for i, agent in enumerate(agents):
                if agent["id"] == agent_id:
                    agents[i] = {**agent, **update_data_copy}
                    return Database._parse_agent_json_fields(agents[i])
            raise Exception(f"Agent with ID {agent_id} not found")
        
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).update(update_data_copy).eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error updating agent: {response.error.message}")
        
        if not response.data:
            raise Exception(f"Agent with ID {agent_id} not found")
        
        return Database._parse_agent_json_fields(response.data[0])

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return associated user data.
        """
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE).select("*").eq("key", api_key).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error validating API key: {response.error.message}")
        
        if not response.data:
            return None
        
        key_data = response.data[0]
        
        # Check if the key is expired
        if key_data.get("expires_at") and datetime.fromisoformat(key_data["expires_at"]) < datetime.now(timezone.utc):
            return None
        
        # Get user data
        user_response = supabase.table(USERS_TABLE).select("*").eq("id", key_data["user_id"]).execute()
        
        if hasattr(user_response, "error") and user_response.error:
            raise Exception(f"Error fetching user: {user_response.error.message}")
        
        if not user_response.data:
            return None
        
        return {
            "api_key": key_data,
            "user": user_response.data[0],
        }

    @staticmethod
    async def create_api_key(user_id: str, name: str, expires_at: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new API key for a user.
        
        Args:
            user_id: The ID of the user who owns the key
            name: A user-friendly name for the key
            expires_at: Optional ISO-format datetime string when the key expires
            description: Optional description of what the key is used for
            
        Returns:
            The created API key data
        """
        key = secrets.token_hex(32)
        now = datetime.utcnow().isoformat()
        
        key_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "key": key,
            "name": name,
            "description": description,
            "created_at": now,
            "last_used_at": None,
            "expires_at": expires_at,
        }
        
        if supabase is None:
            # Use mock database
            MOCK_DB.setdefault(API_KEYS_TABLE, []).append(key_data)
            return key_data
        
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE).insert(key_data).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating API key: {response.error.message}")
        
        return response.data[0]

    @staticmethod
    async def list_api_keys(user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all API keys for a user with pagination.
        """
        if supabase is None:
            # Use mock database
            api_keys = [
                key for key in MOCK_DB.get(API_KEYS_TABLE, [])
                if key.get("user_id") == user_id
            ]
            
            # Apply pagination
            paginated_keys = api_keys[offset:offset+limit]
            
            return paginated_keys
        
        # Use Supabase
        query = supabase.table(API_KEYS_TABLE).select("*").eq("user_id", user_id)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching API keys: {response.error.message}")
        
        return response.data

    @staticmethod
    async def count_api_keys(user_id: str) -> int:
        """
        Count the total number of API keys for a user.
        """
        if supabase is None:
            # Use mock database
            api_keys = [
                key for key in MOCK_DB.get(API_KEYS_TABLE, [])
                if key.get("user_id") == user_id
            ]
            return len(api_keys)
        
        # Use Supabase
        query = supabase.table(API_KEYS_TABLE).select("id", count="exact").eq("user_id", user_id)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting API keys: {response.error.message}")
        
        return response.count

    @staticmethod
    async def delete_api_key(key_id: str, user_id: str) -> bool:
        """
        Delete an API key.
        """
        if supabase is None:
            # Use mock database
            keys = MOCK_DB.get(API_KEYS_TABLE, [])
            for i, key in enumerate(keys):
                if key.get("id") == key_id and key.get("user_id") == user_id:
                    keys.pop(i)
                    return True
            return False
        
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE)\
            .delete()\
            .eq("id", key_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error deleting API key: {response.error.message}")
        
        return len(response.data) > 0

    @staticmethod
    async def list_federated_registries(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all federated registries with pagination.
        """
        if supabase is None:
            # Use mock database
            registries = MOCK_DB.get(FEDERATED_REGISTRIES_TABLE, [])
            
            # Apply pagination
            paginated_registries = registries[offset:offset+limit]
            
            return paginated_registries
        
        # Use Supabase
        query = supabase.table(FEDERATED_REGISTRIES_TABLE).select("*")
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching federated registries: {response.error.message}")
        
        return response.data

    @staticmethod
    async def count_federated_registries() -> int:
        """
        Count the total number of federated registries.
        """
        if supabase is None:
            # Use mock database
            registries = MOCK_DB.get(FEDERATED_REGISTRIES_TABLE, [])
            return len(registries)
        
        # Use Supabase
        query = supabase.table(FEDERATED_REGISTRIES_TABLE).select("id", count="exact")
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting federated registries: {response.error.message}")
        
        return response.count

    @staticmethod
    async def add_federated_registry(registry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new federated registry.
        """
        now = datetime.utcnow().isoformat()
        
        registry_record = {
            **registry_data,
            "id": str(uuid.uuid4()),
            "created_at": now,
            "last_synced_at": None,
        }
        
        if supabase is None:
            # Use mock database
            MOCK_DB.setdefault(FEDERATED_REGISTRIES_TABLE, []).append(registry_record)
            return registry_record
        
        # Use Supabase
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).insert(registry_record).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating federated registry: {response.error.message}")
        
        return response.data[0]

    @staticmethod
    async def record_agent_health(health_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a health check ping from an agent.
        """
        # Add timestamps
        now = datetime.now(timezone.utc)
        health_data["last_ping_at"] = now.isoformat()
        
        # Use Supabase
        # First try to update existing record
        update_query = (
            supabase.table(AGENT_HEALTH_TABLE)
            .update(health_data)
            .eq("agent_id", health_data["agent_id"])
            .eq("server_id", health_data["server_id"])
            .execute()
        )
        
        if hasattr(update_query, "error") and update_query.error:
            raise Exception(f"Error updating agent health: {update_query.error.message}")
        
        # If we updated a record, return it
        if update_query.data and len(update_query.data) > 0:
            return update_query.data[0]
        
        # Otherwise insert a new record
        insert_query = supabase.table(AGENT_HEALTH_TABLE).insert(health_data).execute()
        
        if hasattr(insert_query, "error") and insert_query.error:
            raise Exception(f"Error inserting agent health: {insert_query.error.message}")
        
        return insert_query.data[0]
    
    @staticmethod
    async def get_agent_health(agent_id: str) -> List[Dict[str, Any]]:
        """
        Get the health status for a specific agent across all servers.
        """
        if supabase is None:
            # Use mock database
            return [
                record for record in MOCK_DB.get(AGENT_HEALTH_TABLE, [])
                if record.get("agent_id") == agent_id
            ]
        
        # Use Supabase
        query = (
            supabase.table(AGENT_HEALTH_TABLE)
            .select("*")
            .eq("agent_id", agent_id)
            .execute()
        )
        
        if hasattr(query, "error") and query.error:
            raise Exception(f"Error fetching agent health: {query.error.message}")
        
        return query.data
    
    @staticmethod
    async def list_agent_health(
        limit: int = 100, 
        offset: int = 0,
        server_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List health status for all agents, optionally filtered by server.
        """
        if supabase is None:
            # Use mock database
            records = MOCK_DB.get(AGENT_HEALTH_TABLE, [])
            
            # Filter by server_id if provided
            if server_id:
                records = [r for r in records if r.get("server_id") == server_id]
            
            # Apply pagination
            return records[offset:offset+limit]
        
        # Use Supabase
        query = supabase.table(AGENT_HEALTH_TABLE).select("*")
        
        # Filter by server_id if provided
        if server_id:
            query = query.eq("server_id", server_id)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error listing agent health: {response.error.message}")
        
        return response.data
    
    @staticmethod
    async def count_agent_health(server_id: Optional[str] = None) -> int:
        """
        Count the total number of agent health records.
        """
        if supabase is None:
            # Use mock database
            records = MOCK_DB.get(AGENT_HEALTH_TABLE, [])
            
            # Filter by server_id if provided
            if server_id:
                records = [r for r in records if r.get("server_id") == server_id]
            
            return len(records)
        
        # Use Supabase
        query = supabase.table(AGENT_HEALTH_TABLE).select("id", count="exact")
        
        # Filter by server_id if provided
        if server_id:
            query = query.eq("server_id", server_id)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting agent health: {response.error.message}")
        
        return response.count
    
    @staticmethod
    async def get_agent_health_summary() -> List[Dict[str, Any]]:
        """
        Get a summary of agent health status grouped by agent.
        This requires joining with the agents table to get agent names.
        """
        if supabase is None:
            # Use mock database
            summary = {}
            
            # Get all health records
            health_records = MOCK_DB.get(AGENT_HEALTH_TABLE, [])
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            
            # Group by agent_id
            for record in health_records:
                agent_id = record.get("agent_id")
                if agent_id not in summary:
                    # Find agent name
                    agent_name = "Unknown"
                    for agent in agents:
                        if agent.get("id") == agent_id:
                            agent_name = agent.get("name", "Unknown")
                            break
                    
                    summary[agent_id] = {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "servers": [],
                        "status": "inactive",
                        "last_ping_at": None
                    }
                
                # Add server info
                server_info = {
                    "server_id": record.get("server_id"),
                    "status": record.get("status"),
                    "last_ping_at": record.get("last_ping_at"),
                    "metadata": record.get("metadata", {})
                }
                summary[agent_id]["servers"].append(server_info)
                
                # Update summary status and last_ping_at
                if record.get("status") == "active":
                    summary[agent_id]["status"] = "active"
                
                if (summary[agent_id]["last_ping_at"] is None or
                    record.get("last_ping_at") > summary[agent_id]["last_ping_at"]):
                    summary[agent_id]["last_ping_at"] = record.get("last_ping_at")
            
            return list(summary.values())
        
        # For Supabase, we need a more sophisticated query
        # This requires a join between agent_health and agents
        # Since this functionality is complex in Supabase, we'll fetch data and process in Python
        
        # Get all health records
        health_query = supabase.table(AGENT_HEALTH_TABLE).select("*").execute()
        
        if hasattr(health_query, "error") and health_query.error:
            raise Exception(f"Error getting health records: {health_query.error.message}")
        
        health_records = health_query.data
        
        # Get all agents for mapping IDs to names
        agents_query = supabase.table(AGENTS_TABLE).select("id,name").execute()
        
        if hasattr(agents_query, "error") and agents_query.error:
            raise Exception(f"Error getting agents: {agents_query.error.message}")
        
        # Create a mapping of agent_id to name
        agent_names = {agent["id"]: agent["name"] for agent in agents_query.data}
        
        # Group by agent_id
        summary = {}
        for record in health_records:
            agent_id = record.get("agent_id")
            if agent_id not in summary:
                summary[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": agent_names.get(agent_id, "Unknown"),
                    "servers": [],
                    "status": "inactive",
                    "last_ping_at": None
                }
            
            # Add server info
            server_info = {
                "server_id": record.get("server_id"),
                "status": record.get("status"),
                "last_ping_at": record.get("last_ping_at"),
                "metadata": record.get("metadata", {})
            }
            summary[agent_id]["servers"].append(server_info)
            
            # Update summary status and last_ping_at
            if record.get("status") == "active":
                summary[agent_id]["status"] = "active"
            
            last_ping = record.get("last_ping_at")
            if (summary[agent_id]["last_ping_at"] is None or
                (last_ping and last_ping > summary[agent_id]["last_ping_at"])):
                summary[agent_id]["last_ping_at"] = last_ping
        
        return list(summary.values())

    @staticmethod
    async def get_federated_registry(registry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a federated registry by ID.
        """
        if supabase is None:
            # Use mock database
            registries = MOCK_DB.get(FEDERATED_REGISTRIES_TABLE, [])
            for registry in registries:
                if registry["id"] == registry_id:
                    return registry
            return None
        
        # Use Supabase
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).select("*").eq("id", registry_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching federated registry: {response.error.message}")
        
        if not response.data:
            return None
        
        return response.data[0]
    
    @staticmethod
    async def get_agent_by_federation_id(federation_id: str, registry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an agent by its federation ID and registry ID.
        """
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            for agent in agents:
                if (agent.get("federation_id") == federation_id and 
                    agent.get("registry_id") == registry_id):
                    return Database._parse_agent_json_fields(agent)
            return None
        
        # Use Supabase
        response = (supabase.table(AGENTS_TABLE)
                   .select("*")
                   .eq("federation_id", federation_id)
                   .eq("registry_id", registry_id)
                   .execute())
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agent by federation ID: {response.error.message}")
        
        if not response.data:
            return None
        
        return Database._parse_agent_json_fields(response.data[0])
    
    @staticmethod
    async def create_federated_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new federated agent.
        """
        # Ensure the agent is marked as federated
        agent_data["is_federated"] = True
        
        # Store original ID as federation_id if present
        if "id" in agent_data:
            agent_data["federation_id"] = agent_data["id"]
            # Generate new ID for our system
            agent_data["id"] = str(uuid.uuid4())
        else:
            agent_data["id"] = str(uuid.uuid4())
            agent_data["federation_id"] = agent_data["id"]
        
        if supabase is None:
            # Use mock database
            agent_data["created_at"] = datetime.now(timezone.utc).isoformat()
            agent_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            MOCK_DB.setdefault(AGENTS_TABLE, []).append(agent_data)
            return Database._parse_agent_json_fields(agent_data)
        
        # Use Supabase
        # Add timestamps
        agent_data["created_at"] = datetime.now(timezone.utc).isoformat()
        agent_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        response = supabase.table(AGENTS_TABLE).insert(agent_data).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating federated agent: {response.error.message}")
        
        return Database._parse_agent_json_fields(response.data[0])
    
    @staticmethod
    async def update_federated_agent(agent_id: str, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a federated agent.
        """
        # Ensure the agent remains marked as federated
        agent_data["is_federated"] = True
        agent_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Don't overwrite our internal ID
        if "id" in agent_data:
            agent_data["federation_id"] = agent_data["id"]
            del agent_data["id"]
        
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            for i, agent in enumerate(agents):
                if agent["id"] == agent_id:
                    agents[i] = {**agent, **agent_data}
                    return Database._parse_agent_json_fields(agents[i])
            raise Exception(f"Federated agent with ID {agent_id} not found")
        
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).update(agent_data).eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error updating federated agent: {response.error.message}")
        
        if not response.data:
            raise Exception(f"Federated agent with ID {agent_id} not found")
        
        return Database._parse_agent_json_fields(response.data[0])
    
    @staticmethod
    async def update_federated_registry_sync_time(registry_id: str) -> Dict[str, Any]:
        """
        Update the last_synced_at timestamp for a federated registry.
        """
        sync_data = {
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        
        if supabase is None:
            # Use mock database
            registries = MOCK_DB.get(FEDERATED_REGISTRIES_TABLE, [])
            for i, registry in enumerate(registries):
                if registry["id"] == registry_id:
                    registries[i] = {**registry, **sync_data}
                    return registries[i]
            raise Exception(f"Federated registry with ID {registry_id} not found")
        
        # Use Supabase
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).update(sync_data).eq("id", registry_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error updating federation sync time: {response.error.message}")
        
        if not response.data:
            raise Exception(f"Federated registry with ID {registry_id} not found")
        
        return response.data[0]
    
    @staticmethod
    async def count_agents(registry_id: Optional[str] = None) -> int:
        """
        Count agents with optional filtering by registry_id.
        """
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            
            if registry_id:
                agents = [agent for agent in agents if agent.get("registry_id") == registry_id]
                
            return len(agents)
        
        # Use Supabase
        query = supabase.table(AGENTS_TABLE).select("count", count="exact")
        
        if registry_id:
            query = query.eq("registry_id", registry_id)
            
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting agents: {response.error.message}")
        
        return response.count

    @staticmethod
    async def create_agent_verification(verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent verification record.
        
        Args:
            verification_data: Dictionary containing verification information:
                - agent_id: ID of the agent
                - did: Decentralized Identifier
                - public_key: Public key in PEM format
                - verification_method: Method used for verification (e.g., 'mlts')
                - status: Verification status ('active', 'revoked', etc.)
                - last_verified: Timestamp of last verification (if any)
                
        Returns:
            Created verification record
        """
        # Add metadata
        verification_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Create a copy to avoid modifying the original
        verification_data_copy = verification_data.copy()
        
        # Convert JSON fields to strings for database storage
        if "did_document" in verification_data_copy and verification_data_copy["did_document"] is not None:
            verification_data_copy["did_document"] = json.dumps(verification_data_copy["did_document"])
        
        verification_record = {
            "id": verification_id,
            "created_at": now,
            "updated_at": now,
            **verification_data_copy
        }
        
        # Use encryption for sensitive fields if configured
        if "private_key" in verification_data and hasattr(Database, "key_encryption"):
            # Encrypt private key if present
            verification_record["private_key"] = Database.key_encryption.encrypt(
                verification_data["private_key"]
            )
            # Store encryption metadata
            verification_record["encryption_type"] = "AES-256-GCM"
            verification_record["key_reference"] = "master_key"
        
        # Use Supabase
        response = supabase.table(AGENT_VERIFICATION_TABLE).insert(verification_record).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating agent verification: {response.error.message}")
        
        # Parse the response data to convert JSON strings back to objects
        result = response.data[0] if response.data else verification_record
        
        # Parse the JSON fields back to objects
        if isinstance(result.get("did_document"), str):
            try:
                result["did_document"] = json.loads(result["did_document"])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if parsing fails
                
        return result
