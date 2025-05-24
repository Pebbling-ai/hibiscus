"""
Supabase utilities for connecting to and interacting with Supabase database.
This module provides a client and constants for working with Supabase.
"""
import os
from typing import Dict, List, Optional, Any, Union, Callable
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Table names
AGENTS_TABLE = "agents"
USERS_TABLE = "users"
API_KEYS_TABLE = "api_keys"
FEDERATED_REGISTRIES_TABLE = "federated_registries"
AGENT_HEALTH_TABLE = "agent_health"
AGENT_VERIFICATION_TABLE = "agent_verification"

class SupabaseClient:
    """
    A wrapper around the Supabase client to provide standardized access
    to the database with proper error handling and connection management.
    """
    
    def __init__(self):
        """Initialize the Supabase client with credentials from environment variables."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        
        self.client = create_client(supabase_url, supabase_key)
    
    def table(self, table_name: str) -> Client:
        """
        Get a reference to a table in the Supabase database.
        
        Args:
            table_name: The name of the table to access
            
        Returns:
            A Supabase query builder for the specified table
        """
        return self.client.table(table_name)
    
    def execute_query(self, table_name: str, query_fn: Callable[[Client], Any]) -> Any:
        """
        Execute a query against a Supabase table using a query function.
        
        Args:
            table_name: The name of the table to query
            query_fn: A function that takes a Supabase query builder and returns a query result
            
        Returns:
            The result of the query function
        """
        table = self.table(table_name)
        return query_fn(table)
    
    def insert(self, table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Insert data into a Supabase table.
        
        Args:
            table_name: The name of the table to insert into
            data: Dictionary or list of dictionaries containing the data to insert
            
        Returns:
            The inserted data with any server-generated fields
        """
        return self.table(table_name).insert(data).execute()
    
    def select(self, table_name: str, columns: str = "*") -> Client:
        """
        Begin a SELECT query on a Supabase table.
        
        Args:
            table_name: The name of the table to select from
            columns: Comma-separated string of columns to select
            
        Returns:
            A Supabase query builder for further query construction
        """
        return self.table(table_name).select(columns)
    
    def update(self, table_name: str, data: Dict[str, Any]) -> Client:
        """
        Begin an UPDATE query on a Supabase table.
        
        Args:
            table_name: The name of the table to update
            data: Dictionary containing the data to update
            
        Returns:
            A Supabase query builder for further query construction
        """
        return self.table(table_name).update(data)
    
    def delete(self, table_name: str) -> Client:
        """
        Begin a DELETE query on a Supabase table.
        
        Args:
            table_name: The name of the table to delete from
            
        Returns:
            A Supabase query builder for further query construction
        """
        return self.table(table_name).delete()
    
    def rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a PostgreSQL stored procedure.
        
        Args:
            function_name: The name of the function to call
            params: Dictionary of parameters to pass to the function
            
        Returns:
            The result of the function call
        """
        return self.client.rpc(function_name, params or {}).execute()