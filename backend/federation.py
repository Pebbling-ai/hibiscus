import httpx
import asyncio
from typing import Dict, List, Any, Optional
from db import Database

class FederatedRegistryClient:
    """
    Client for interacting with federated agent registries.
    """
    
    def __init__(self, registry_url: str, api_key: Optional[str] = None):
        self.registry_url = registry_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def list_agents(
        self, 
        search: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch agents from a federated registry.
        """
        url = f"{self.registry_url}/agents"
        
        params = {
            "skip": skip,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        if category:
            params["category"] = category
        
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        try:
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            agents = response.json()
            
            # Mark agents as federated and add source
            for agent in agents:
                agent["is_federated"] = True
                agent["federation_source"] = self.registry_url
            
            return agents
            
        except httpx.HTTPError as e:
            print(f"Error fetching agents from federated registry {self.registry_url}: {str(e)}")
            return []
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific agent from a federated registry.
        """
        url = f"{self.registry_url}/agents/{agent_id}"
        
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            agent = response.json()
            agent["is_federated"] = True
            agent["federation_source"] = self.registry_url
            
            return agent
            
        except httpx.HTTPError as e:
            print(f"Error fetching agent from federated registry {self.registry_url}: {str(e)}")
            return None


async def get_federated_agents(
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get agents from all federated registries.
    """
    federated_registries = await Database.list_federated_registries()
    
    clients = [
        FederatedRegistryClient(
            registry["url"],
            registry.get("api_key")
        )
        for registry in federated_registries
    ]
    
    # Calculate how many agents to get from each registry
    # This is a simple approach - more sophisticated pagination would be needed for production
    per_registry_limit = max(limit // len(clients), 10) if clients else 0
    
    # Fetch agents from all registries in parallel
    federated_results = await asyncio.gather(
        *[
            client.list_agents(
                search=search,
                category=category,
                skip=skip,
                limit=per_registry_limit
            )
            for client in clients
        ],
        return_exceptions=True
    )
    
    all_federated_agents = []
    
    for result in federated_results:
        if isinstance(result, Exception):
            continue
        all_federated_agents.extend(result)
    
    # Sort and limit the combined results
    # This is a basic approach - more sophisticated ranking would be needed for production
    all_federated_agents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return all_federated_agents[:limit]


async def get_federated_agent(agent_id: str, federation_source: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific federated agent by ID and source.
    """
    federated_registries = await Database.list_federated_registries()
    
    # Find the matching registry
    matching_registry = None
    for registry in federated_registries:
        if registry["url"] == federation_source:
            matching_registry = registry
            break
    
    if not matching_registry:
        return None
    
    client = FederatedRegistryClient(
        matching_registry["url"],
        matching_registry.get("api_key")
    )
    
    return await client.get_agent(agent_id)
