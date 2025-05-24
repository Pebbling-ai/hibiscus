"""
Database client for accessing and managing data in Supabase.
This module provides an abstraction layer over the Supabase database.
"""
import os
import uuid
import json
import secrets
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Import Supabase utilities
from app.utils.supabase_utils import (
    SupabaseClient,
    AGENTS_TABLE,
    USERS_TABLE,
    API_KEYS_TABLE,
    FEDERATED_REGISTRIES_TABLE,
    AGENT_HEALTH_TABLE,
    AGENT_VERIFICATION_TABLE,
    parse_json_fields,
    serialize_json_fields
)

# Load environment variables
load_dotenv()

# Get Supabase client
supabase = SupabaseClient.get_client()

# Mock data for development without Supabase
MOCK_DB = {
    AGENTS_TABLE: [],
    USERS_TABLE: [],
    API_KEYS_TABLE: [],
    FEDERATED_REGISTRIES_TABLE: [],
    AGENT_HEALTH_TABLE: [],
    AGENT_VERIFICATION_TABLE: []
}


class Database:
    """Database client for accessing and managing data in Supabase."""

    @staticmethod
    async def _execute_query(table: str, query_fn=None) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Execute a query against Supabase or mock database.
        
        Args:
            table: The table to query
            query_fn: Function that takes a Supabase client and returns a query result
            
        Returns:
            Query results from Supabase or mock database
        """
        if supabase is None:
            # Use mock database
            if query_fn is None:
                return MOCK_DB.get(table, [])
            return query_fn(MOCK_DB.get(table, []))
        
        # Use real Supabase client
        return query_fn(supabase)
    
    # ===== Agent Methods =====
    
    @staticmethod
    async def list_agents(
        limit: int = 100, 
        offset: int = 0, 
        is_team: Optional[bool] = None,
        agent_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all agents with optional filtering and pagination.
        Include verification and health data from related tables.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip (for pagination)
            is_team: Optional filter for teams
            agent_ids: Optional list of agent IDs to filter by
        
        Returns:
            List of agent data dictionaries
        """
        # Use Supabase
        query = supabase.table(AGENTS_TABLE).select("*")
        
        # Apply team filter if provided
        if is_team is not None:
            query = query.eq("is_team", is_team)
        
        # Apply agent_ids filter if provided
        if agent_ids:
            if len(agent_ids) == 1:
                # Simple equality for single ID
                query = query.eq("id", agent_ids[0])
            else:
                # Use 'in' filter for multiple IDs
                query = query.in_("id", agent_ids)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agents: {response.error.message}")
        
        # Parse JSON fields for each agent
        parsed_agents = []
        for agent in response.data:
            # Parse agent JSON fields
            parsed_agent = parse_json_fields(agent)
            
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
            
            # Fetch health data for this agent
            health_data = await Database._fetch_agent_health_data(agent["id"])
            parsed_agent.update(health_data)
            
            parsed_agents.append(parsed_agent)
            
        # Sort agents to prioritize healthy ones
        sorted_agents = sorted(parsed_agents, 
                              key=lambda x: (
                                  0 if x.get("health_status") == "active" else
                                  1 if x.get("health_status") == "degraded" else
                                  2 if x.get("health_status") == "inactive" else 3
                              ))
            
        return sorted_agents

    @staticmethod
    async def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent by ID and deserialize JSON fields.
        Include verification data from agent_verification table.
        
        Args:
            agent_id: UUID of the agent to retrieve
            
        Returns:
            Agent data dictionary or None if not found
        """
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).select("*").eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching agent: {response.error.message}")
        
        if not response.data:
            return None
        
        # Parse JSON fields
        agent = parse_json_fields(response.data[0])
        
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
        
        # Fetch health data for this agent
        health_data = await Database._fetch_agent_health_data(agent_id)
        agent.update(health_data)
        
        return agent

    @staticmethod
    async def create_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent with the given data.
        
        Args:
            agent_data: Dictionary containing agent data
            
        Returns:
            Created agent data
        """
        agent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Handle json serialization for complex fields
        agent_data_copy = serialize_json_fields(agent_data)
        
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
        Update an existing agent with the given data.
        
        Args:
            agent_id: UUID of the agent to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated agent data
        """
        # Make a copy so we don't modify the original
        update_data_copy = update_data.copy()
        update_data_copy["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Use the utility function to serialize JSON fields
        update_data_copy = serialize_json_fields(update_data_copy)
        
        # Use Supabase
        response = supabase.table(AGENTS_TABLE).update(update_data_copy).eq("id", agent_id).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error updating agent: {response.error.message}")
        
        if not response.data:
            raise Exception(f"Agent with ID {agent_id} not found")
        
        return parse_json_fields(response.data[0])

    @staticmethod
    async def count_agents(registry_id: Optional[str] = None) -> int:
        """
        Count agents with optional filtering by registry_id.
        
        Args:
            registry_id: Optional registry ID to filter by
            
        Returns:
            Count of matching agents
        """
        # Use Supabase
        query = supabase.table(AGENTS_TABLE).select("count", count="exact")
        
        if registry_id:
            query = query.eq("registry_id", registry_id)
            
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting agents: {response.error.message}")
        
        return response.count
    
    # ===== Authentication Methods =====
    
    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return associated user data.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Dictionary with API key and user data, or None if invalid
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
    async def create_api_key(
        user_id: str, 
        name: str, 
        expires_at: Optional[str] = None, 
        description: Optional[str] = None
    ) -> Dict[str, Any]:
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
        now = datetime.now(timezone.utc).isoformat()
        
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
        
        # Use Supabase
        response = supabase.table(API_KEYS_TABLE).insert(key_data).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error creating API key: {response.error.message}")
        
        return response.data[0]

    @staticmethod
    async def count_api_keys(user_id: str) -> int:
        """
        Count the total number of API keys for a user.
        """   
        # Use Supabase
        query = supabase.table(API_KEYS_TABLE).select("id", count="exact").eq("user_id", user_id)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error counting API keys: {response.error.message}")
        
        return response.count
    

    @staticmethod
    async def create_user(email: str, full_name: str, session_id: str) -> Dict[str, Any]:
        """
        Create a new user and associate the Clerk session ID as an API key.
        
        Args:
            email: User's email address
            full_name: User's full name
            session_id: Clerk session ID to use as API key
            
        Returns:
            Dictionary with user data and API key information
        """
        # Generate a UUID for the user
        user_id = str(uuid.uuid4())
        
        # Get current timestamp
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if user with this email already exists
        user_response = (
            supabase.table(USERS_TABLE)
            .select("*")
            .eq("email", email)
            .execute()
        )
        
        if hasattr(user_response, "error") and user_response.error:
            raise Exception(f"Error checking existing user: {user_response.error.message}")
        
        existing_user = None
        if user_response.data:
            existing_user = user_response.data[0]
            user_id = existing_user["id"]
        
        # If user doesn't exist, create new user
        if not existing_user:
            user_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "created_at": now,
                "updated_at": now,
            }
            
            user_response = (
                supabase.table(USERS_TABLE)
                .insert(user_data)
                .execute()
            )
            
            if hasattr(user_response, "error") and user_response.error:
                raise Exception(f"Error creating user: {user_response.error.message}")
            
            user = user_response.data[0] if user_response.data else user_data
        else:
            # Update existing user if needed
            user_data = {
                "full_name": full_name,
                "updated_at": now,
            }
            
            user_response = (
                supabase.table(USERS_TABLE)
                .update(user_data)
                .eq("id", user_id)
                .execute()
            )
            
            if hasattr(user_response, "error") and user_response.error:
                raise Exception(f"Error updating user: {user_response.error.message}")
            
            user = user_response.data[0] if user_response.data else {**existing_user, **user_data}
        
        # Check if this session ID already exists as an API key
        key_response = (
            supabase.table(API_KEYS_TABLE)
            .select("*")
            .eq("key", session_id)
            .execute()
        )
        
        if hasattr(key_response, "error") and key_response.error:
            raise Exception(f"Error checking existing API key: {key_response.error.message}")
        
        # If this session ID is already registered, return the existing data
        if key_response.data:
            existing_key = key_response.data[0]
            
            # Update last_used_at timestamp
            key_update = (
                supabase.table(API_KEYS_TABLE)
                .update({"last_used_at": now})
                .eq("id", existing_key["id"])
                .execute()
            )
            
            if hasattr(key_update, "error") and key_update.error:
                logger.error(f"Error updating API key last_used_at: {key_update.error.message}")
            
            return {
                "user": user,
                "api_key": existing_key,
            }
        
        # Create a new API key entry for the session ID
        key_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "clerk_session",
            "key": session_id,
            "created_at": now,
            "last_used_at": now,
            "is_active": True,
        }
        
        key_response = (
            supabase.table(API_KEYS_TABLE)
            .insert(key_data)
            .execute()
        )
        
        if hasattr(key_response, "error") and key_response.error:
            raise Exception(f"Error creating API key: {key_response.error.message}")
        
        api_key = key_response.data[0] if key_response.data else key_data
        
        return {
            "user": user,
            "api_key": api_key,
        }

    @staticmethod
    async def list_api_keys(user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all API keys for a user with pagination.
        """        
        # Use Supabase
        query = supabase.table(API_KEYS_TABLE).select("*").eq("user_id", user_id)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching API keys: {response.error.message}")
        
        return response.data

    @staticmethod
    async def delete_api_key(key_id: str, user_id: str) -> bool:
        """
        Mark an API key as inactive instead of deleting it.
        
        Args:
            key_id: The ID of the API key to mark as inactive
            user_id: The ID of the user who owns the key
            
        Returns:
            True if the key was updated, False if not found
        """
        try:
            # Update the status to inactive instead of deleting
            response = supabase.table(API_KEYS_TABLE).update({"status": "inactive"})\
                .eq("id", key_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if hasattr(response, "error") and response.error:
                raise Exception(f"Error updating API key status: {response.error.message}")
            
            # Return True if at least one row was affected
            return len(response.data) > 0
        except Exception as e:
            # Log the error and re-raise
            print(f"Error marking API key as inactive: {str(e)}")
            raise e
        
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by their email address.
        
        Args:
            email: The email address to look up
            
        Returns:
            User data dictionary or None if not found
        """
        # Use Supabase to query the users table by email
        response = supabase.table(USERS_TABLE).select("*").eq("email", email).execute()
        
        if hasattr(response, "error") and response.error:
            raise Exception(f"Error fetching user by email: {response.error.message}")
        
        # Return None if no user was found with this email
        if not response.data:
            return None
            
        # Return the first user with this email
        return response.data[0]
    
    @staticmethod
    async def create_user(email: str, full_name: str, session_id: str) -> Dict[str, Any]:
        """
        Register a new user with Clerk session ID.
        
        This method:
        1. Creates a new user in the users table using the User model
        2. Creates an API key record for the session in the api_keys table
        
        Args:
            email: User's email address
            full_name: User's full name
            session_id: Clerk session ID from the X-API-Key header
            
        Returns:
            Dictionary with user data
        
        Raises:
            Exception: If a user with this email already exists
        """
        # Import here to avoid circular imports
        from app.models.schemas import User
        
        # Check if a user with this email already exists
        existing_user = await Database.get_user_by_email(email)
        if existing_user:
            raise Exception(f"User with email '{email}' already exists")
        
        # Generate a new user ID
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create the user using the User model
        user_model = User(
            id=user_id,
            email=email,
            full_name=full_name,
            created_at=now,
            updated_at=now
        )
        
        # Convert to dict for database insertion
        user = user_model.model_dump()
        
        try:
            # Insert the user into the database
            user_response = supabase.table(USERS_TABLE).insert(user).execute()
            
            if hasattr(user_response, "error") and user_response.error:
                raise Exception(f"Error creating user: {user_response.error.message}")
            
            # Create an API key record for the session using the ApiKey model
            api_key_model = ApiKey(
                id=str(uuid.uuid4()),
                user_id=user_id,
                key=session_id,
                name="session",
                created_at=now,
                last_used_at=now,
                expires_at=None,  # Session keys don't expire
                status="active"
            )
            
            # Convert to dict for database insertion
            api_key = api_key_model.model_dump()
            
            # Insert the API key into the database
            key_response = supabase.table(API_KEYS_TABLE).insert(api_key).execute()
            
            if hasattr(key_response, "error") and key_response.error:
                # If API key creation fails, attempt to delete the user
                supabase.table(USERS_TABLE).delete().eq("id", user_id).execute()
                raise Exception(f"Error creating API key: {key_response.error.message}")
        except Exception as e:
            # If any error occurs, attempt to clean up by deleting the user
            try:
                supabase.table(USERS_TABLE).delete().eq("id", user_id).execute()
            except:
                pass  # Ignore cleanup errors
            raise e  # Re-raise the original exception
        
        return {
            "user_id": user_id,
            "email": email,
            "full_name": full_name
        }
    
    # ===== Health Monitoring Methods =====
    
    @staticmethod
    async def record_agent_health(health_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a health check ping from an agent.
        
        Args:
            health_data: Dictionary containing health check data
            
        Returns:
            Saved health record
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
        
        Args:
            agent_id: UUID of the agent
            
        Returns:
            List of health status records
        """
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
    
    # ===== Agent Verification Methods =====
    
    @staticmethod
    async def create_agent_verification(verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent verification record.
        
        Args:
            verification_data: Dictionary containing verification information
                
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

    @staticmethod
    async def _fetch_agent_health_data(agent_id: str) -> Dict[str, Any]:
        """
        Fetch health data for a specific agent.
        
        Args:
            agent_id: ID of the agent to fetch health data for
            
        Returns:
            Dict containing health data fields
        """
        health_data = {
            "health_status": "unknown",
            "last_health_check": None,
            "server_id": None,
            "response_time": None,
            "availability": None,
            "health_details": None
        }
        
        try:
            # Fetch health data from database
            health_query = supabase.table(AGENT_HEALTH_TABLE).select("*").eq("agent_id", agent_id).execute()
            
            if not hasattr(health_query, "error") and health_query.data:
                health = health_query.data[0]
                
                # Add health fields to agent data
                health_data["health_status"] = health.get("status")
                health_data["last_health_check"] = health.get("last_ping_at")
                health_data["server_id"] = health.get("server_id")
                
                # Add additional health metadata if available
                if health.get("metadata"):
                    metadata = health.get("metadata")
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            pass
                    
                    if isinstance(metadata, dict):
                        health_data["response_time"] = metadata.get("response_time")
                        health_data["availability"] = metadata.get("availability")
                        health_data["health_details"] = metadata
        except Exception as e:
            logger.error(f"Error fetching health data for agent {agent_id}: {str(e)}")
            
        return health_data
