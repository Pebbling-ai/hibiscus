import os
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from supabase import create_client, Client
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Table names
AGENTS_TABLE = "agents"
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"
FEDERATED_REGISTRIES_TABLE = "federated_registries"
AGENT_HEALTH_TABLE = "agent_health"
AGENT_VERIFICATION_TABLE = "agent_verification"

# JSON fields that need parsing/serialization
AGENT_JSON_FIELDS = ['capabilities', 'metadata', 'links', 'dependencies']

# Initialize Supabase client
class SupabaseClient:
    _instance = None
    _client = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get the initialized Supabase client instance.
        Uses the Singleton pattern to ensure only one client exists.
        
        Returns:
            Client: The Supabase client instance or None if not configured
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._client
    
    def __init__(self):
        """Initialize the Supabase client using environment variables."""
        if SupabaseClient._instance is not None:
            raise Exception("This class is a singleton, use get_client() instead")
        
        SupabaseClient._instance = self
        
        # Get credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY"))
        
        if not supabase_url or not supabase_key:
            logger.warning("SUPABASE_URL and SUPABASE_KEY not set. Database operations will fail.")
            SupabaseClient._client = None
        else:
            try:
                SupabaseClient._client = create_client(supabase_url, supabase_key)
                logger.info(f"Supabase client initialized with URL: {supabase_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                SupabaseClient._client = None


def parse_json_fields(data: Dict[str, Any], fields: List[str] = AGENT_JSON_FIELDS) -> Dict[str, Any]:
    """
    Parse JSON fields that might be stored as strings.
    
    Args:
        data: The data dictionary containing potential JSON fields
        fields: List of field names that should be parsed as JSON
        
    Returns:
        Dict with JSON fields properly parsed
    """
    result = data.copy()
    
    for field in fields:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                # Keep as string if parsing fails
                pass
                
    return result


def serialize_json_fields(data: Dict[str, Any], fields: List[str] = AGENT_JSON_FIELDS) -> Dict[str, Any]:
    """
    Serialize fields to JSON strings for storage in Supabase.
    
    Args:
        data: The data dictionary containing fields to serialize
        fields: List of field names that should be serialized to JSON
        
    Returns:
        Dict with fields serialized to JSON strings
    """
    result = data.copy()
    
    for field in fields:
        if field in result and result[field] is not None:
            if not isinstance(result[field], str):
                result[field] = json.dumps(result[field])
                
    return result


def execute_query(query_fn: Callable, error_message: str = "Database query failed"):
    """
    Execute a Supabase query and handle common error cases.
    
    Args:
        query_fn: Function that takes a Supabase client and returns a query
        error_message: Custom error message prefix for exceptions
        
    Returns:
        The query response
        
    Raises:
        Exception: If the query fails
    """
    client = SupabaseClient.get_client()
    if client is None:
        raise Exception("Supabase client not initialized")
        
    response = query_fn(client)
    
    if hasattr(response, "error") and response.error:
        raise Exception(f"{error_message}: {response.error.message}")
        
    return responseå