import os
import json
import secrets
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Table names
AGENTS_TABLE = "agents"
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"
FEDERATED_REGISTRIES_TABLE = "federated_registries"

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Warning: SUPABASE_URL and SUPABASE_KEY not set. Using mock database for development.")
    supabase = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

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
    ]
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
    async def list_agents(limit: int = 100, offset: int = 0, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all agents with optional filtering and deserialize JSON fields.
        """
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            
            # Apply search filter if provided
            if search_term:
                search_term = search_term.lower()
                filtered_agents = []
                for agent in agents:
                    if (
                        search_term in agent.get("name", "").lower() or
                        search_term in agent.get("description", "").lower() or
                        any(search_term in tag.lower() for tag in agent.get("tags", []) if isinstance(tag, str)) or
                        search_term in agent.get("documentation", "").lower() or
                        any(search_term in domain.lower() for domain in agent.get("domains", []) if isinstance(domain, str))
                    ):
                        filtered_agents.append(agent)
                agents = filtered_agents
            
            # Apply pagination
            paginated_agents = agents[offset:offset+limit]
            
            # Parse JSON fields
            return [Database._parse_agent_json_fields(agent) for agent in paginated_agents]
        
        # Use Supabase
        query = supabase.table(AGENTS_TABLE).select("*")
        
        # Apply search filter if provided
        if search_term:
            search_term = search_term.lower()
            query = query.or_(f"name.ilike.%{search_term}%,description.ilike.%{search_term}%,documentation.ilike.%{search_term}%")
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agents: {response.error.message}")
        
        return response.data

    @staticmethod
    async def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent by ID and deserialize JSON fields.
        """
        if supabase is None:
            # Use mock database
            agents = MOCK_DB.get(AGENTS_TABLE, [])
            for agent in agents:
                if agent["id"] == agent_id:
                    # Parse JSON fields that might be stored as strings
                    return Database._parse_agent_json_fields(agent)
            return None
        
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).select("*").eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agent: {response.error.message}")
        
        if not response.data:
            return None
        
        # Parse any JSON fields that might be stored as strings
        return Database._parse_agent_json_fields(response.data[0])

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
        now = datetime.utcnow().isoformat()
        
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
        
        if supabase is None:
            # Use mock database
            MOCK_DB.setdefault(AGENTS_TABLE, []).append(agent)
            return agent
        
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
        if supabase is None:
            # Use mock database
            key_data = None
            for key in MOCK_DB.get(API_KEYS_TABLE, []):
                if key.get("key") == api_key:
                    key_data = key
                    break
            
            if not key_data:
                return None
            
            # Check if the key is expired
            if key_data.get("expires_at") and datetime.fromisoformat(key_data["expires_at"]) < datetime.utcnow():
                return None
            
            # Get user data
            user_data = None
            for user in MOCK_DB.get(USERS_TABLE, []):
                if user.get("id") == key_data.get("user_id"):
                    user_data = user
                    break
            
            if not user_data:
                return None
            
            return {
                "api_key": key_data,
                "user": user_data,
            }
        
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE).select("*").eq("key", api_key).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error validating API key: {response.error.message}")
        
        if not response.data:
            return None
        
        key_data = response.data[0]
        
        # Check if the key is expired
        if key_data.get("expires_at") and datetime.fromisoformat(key_data["expires_at"]) < datetime.utcnow():
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
    async def list_api_keys(user_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user.
        """
        if supabase is None:
            # Use mock database
            return [key for key in MOCK_DB.get(API_KEYS_TABLE, []) if key.get("user_id") == user_id]
        
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE).select("*").eq("user_id", user_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching API keys: {response.error.message}")
        
        return response.data

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
    async def list_federated_registries() -> List[Dict[str, Any]]:
        """
        List all federated registries.
        """
        if supabase is None:
            # Use mock database
            return MOCK_DB.get(FEDERATED_REGISTRIES_TABLE, [])
        
        # Use Supabase
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).select("*").execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching federated registries: {response.error.message}")
        
        return response.data

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
