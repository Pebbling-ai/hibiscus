from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import Agent, AgentCreate, ApiResponse
from app.services.federation import get_federated_agents, get_federated_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[Agent])
async def list_agents(
    search: Optional[str] = None,
    category: Optional[str] = None,
    include_federated: bool = True,
    skip: int = 0,
    limit: int = 100,
):
    """
    List all agents with optional filtering.
    """
    # Get local agents
    local_agents = await Database.list_agents(
        search=search,
        category=category,
        include_federated=False,  # We'll handle federated agents separately
        skip=skip,
        limit=limit,
    )
    
    # Get federated agents if requested
    federated_agents = []
    if include_federated:
        federated_agents = await get_federated_agents(
            search=search,
            category=category,
            skip=skip,
            limit=limit,
        )
    
    # Combine and limit results
    all_agents = local_agents + federated_agents
    
    # Simple sorting by creation date
    all_agents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return all_agents[:limit]


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, federation_source: Optional[str] = None):
    """
    Get a specific agent by ID.
    """
    # If federation_source is provided, get the agent from the federated registry
    if federation_source:
        federated_agent = await get_federated_agent(agent_id, federation_source)
        if not federated_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with id {agent_id} not found in federated registry {federation_source}",
            )
        return federated_agent
    
    # Otherwise, get the agent from the local database
    agent = await Database.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    
    return agent


@router.post("/", response_model=Agent)
async def create_agent(
    agent: AgentCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Create a new agent (requires authentication).
    """
    # Ensure the agent is not marked as federated
    agent_data = agent.dict()
    agent_data["is_federated"] = False
    agent_data["federation_source"] = None
    
    # Create the agent
    try:
        created_agent = await Database.create_agent(
            agent_data=agent_data,
            owner_id=current_user["id"],
        )
        return created_agent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
