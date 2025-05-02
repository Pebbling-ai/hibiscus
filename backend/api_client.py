import os
import json
from typing import Dict, List, Optional, Any
import httpx

class HibiscusClient:
    """
    API client for interacting with the Hibiscus Agent Registry API.
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def _make_request(self, method: str, path: str, **kwargs):
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{path}"
        
        # Add API key if provided
        if self.api_key:
            headers = kwargs.get('headers', {})
            headers['X-API-Key'] = self.api_key
            kwargs['headers'] = headers
        
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    # Agent endpoints
    
    async def list_agents(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        include_federated: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all agents with optional filtering."""
        params = {
            'skip': skip,
            'limit': limit,
            'include_federated': include_federated
        }
        
        if search:
            params['search'] = search
        
        if category:
            params['category'] = category
        
        return await self._make_request('GET', '/agents', params=params)
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get a specific agent by ID."""
        return await self._make_request('GET', f'/agents/{agent_id}')
    
    async def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent (requires authentication)."""
        return await self._make_request('POST', '/agents', json=agent_data)
    
    # Federated registry endpoints
    
    async def list_federated_registries(self) -> List[Dict[str, Any]]:
        """List all federated registries (requires authentication)."""
        return await self._make_request('GET', '/federated-registries')
    
    async def add_federated_registry(self, registry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new federated registry (requires authentication)."""
        return await self._make_request('POST', '/federated-registries', json=registry_data)
    
    # User endpoints
    
    async def get_user_token(self) -> Dict[str, Any]:
        """Get user information based on API token."""
        return await self._make_request('GET', '/user/token')


# Example usage:
# client = HibiscusClient("http://localhost:8000", api_key="your-api-key")
# 
# # List agents
# agents = await client.list_agents(search="assistant")
# 
# # Close client when done
# await client.close()
