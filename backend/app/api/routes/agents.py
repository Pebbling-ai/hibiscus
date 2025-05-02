from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import Agent, AgentCreate, AgentUpdate, ApiResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[Agent])
async def list_agents(
    search: Optional[str] = Query(None, description="Search term to filter agents by name, description, or documentation"),
    limit: int = Query(100, description="Maximum number of agents to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of agents to skip", ge=0),
):
    """List all agents with optional filtering."""
    try:
        agents = await Database.list_agents(
            search_term=search,
            limit=limit,
            offset=offset
        )
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    
    # Otherwise, get the agent from the local database
    agent = await Database.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    
    return agent


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Create a new agent following the Agent Communication Protocol (requires authentication).
    """
    # Prepare agent data
    agent_data = agent.dict()
    agent_data["is_federated"] = False
    agent_data["federation_source"] = None
    agent_data["user_id"] = current_user["id"]
    
    # Create the agent
    try:
        created_agent = await Database.create_agent(agent_data)
        return created_agent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Update an existing agent (requires authentication and ownership).
    """
    try:
        # Check if agent exists and belongs to the current user
        existing_agent = await Database.get_agent(agent_id)
        if not existing_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with id {agent_id} not found",
            )
        
        if existing_agent["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this agent",
            )
        
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in agent_update.dict().items() if v is not None}
        
        # Update the agent
        updated_agent = await Database.update_agent(agent_id, update_data)
        return updated_agent
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
