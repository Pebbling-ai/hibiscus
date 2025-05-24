"""API routes for agent management and operations."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.auth import get_current_user_from_api_key
from app.models.schemas import Agent, AgentCreate, AgentUpdate, PaginatedResponse
from app.utils.search_utils import (
    search_agents,
    create_agent_with_verification,
    update_agent_with_typesense,
    get_agent_by_id,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# Note: The startup initialization has been moved to the lifespan context manager in main.py
# This eliminates the deprecated on_event usage and improves code organization


@router.get("/", response_model=PaginatedResponse[Agent])
async def list_agents(
    search: Optional[str] = None,
    is_team: Optional[bool] = None,
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100),
):
    """List agents with pagination and optional filtering."""
    try:
        response = await search_agents(
            search=search, is_team=is_team, page=page, page_size=page_size
        )
        return response
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    try:
        return await get_agent_by_id(agent_id)
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent: {str(e)}",
        )


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user=Depends(get_current_user_from_api_key),
):
    """Create a new agent with the provided data.

    Args:
        agent: The agent data to create
        current_user: The authenticated user creating the agent

    Returns:
        The created agent data
    """
    try:
        # Convert Pydantic model to dict
        agent_data = agent.model_dump()

        # Use the utility function
        result = await create_agent_with_verification(agent_data, current_user["id"])

        # Return JSONResponse if private key is present
        if isinstance(result, dict) and "private_key" in result:
            return JSONResponse(content=result)

        return result
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_from_api_key),
):
    """Update an existing agent (requires authentication and ownership)."""
    try:
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in agent_update.model_dump().items() if v is not None}

        # Use the utility function for agent update with Typesense sync
        updated_agent = await update_agent_with_typesense(
            agent_id=agent_id,
            update_data=update_data,
            current_user_id=current_user["id"],
        )

        return updated_agent
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
