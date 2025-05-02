import os
import json
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(supabase_url, supabase_key)

# Database tables
AGENTS_TABLE = "agents"
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"
FEDERATED_REGISTRIES_TABLE = "federated_registries"


class Database:
    @staticmethod
    async def list_agents(
        search: Optional[str] = None,
        category: Optional[str] = None,
        include_federated: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List agents with optional filtering.
        """
        query = supabase.table(AGENTS_TABLE).select("*")

        # Apply filters
        if search:
            query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")
        
        if category:
            query = query.eq("category", category)
        
        if not include_federated:
            query = query.eq("is_federated", False)
        
        # Apply pagination
        query = query.range(skip, skip + limit - 1)
        
        # Execute query
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agents: {response.error.message}")
        
        return response.data

    @staticmethod
    async def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific agent by ID.
        """
        response = supabase.table(AGENTS_TABLE).select("*").eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agent: {response.error.message}")
        
        if not response.data:
            return None
        
        return response.data[0]

    @staticmethod
    async def create_agent(agent_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """
        Create a new agent.
        """
        now = datetime.utcnow().isoformat()
        
        agent_record = {
            **agent_data,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        
        response = supabase.table(AGENTS_TABLE).insert(agent_record).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating agent: {response.error.message}")
        
        return response.data[0]

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return associated user data.
        """
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
    async def create_api_key(user_id: str, name: str, expires_at: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new API key for a user.
        """
        import secrets
        
        key = secrets.token_hex(32)
        now = datetime.utcnow().isoformat()
        
        key_data = {
            "user_id": user_id,
            "key": key,
            "name": name,
            "created_at": now,
            "last_used_at": None,
            "expires_at": expires_at,
        }
        
        response = supabase.table(API_KEYS_TABLE).insert(key_data).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating API key: {response.error.message}")
        
        return response.data[0]

    @staticmethod
    async def list_federated_registries() -> List[Dict[str, Any]]:
        """
        List all federated registries.
        """
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).select("*").execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching federated registries: {response.error.message}")
        
        return response.data

    @staticmethod
    async def add_federated_registry(registry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new federated registry.
        """
        response = supabase.table(FEDERATED_REGISTRIES_TABLE).insert(registry_data).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating federated registry: {response.error.message}")
        
        return response.data[0]
