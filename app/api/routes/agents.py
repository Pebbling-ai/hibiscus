from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from loguru import logger

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import Agent, AgentCreate, AgentUpdate, PaginatedResponse
from app.utils.typesense_utils import TypesenseClient
from app.utils.search_utils import (
    search_agents,
    create_agent_with_verification,
    update_agent_with_typesense,
    get_agent_by_id,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# Flag to track if startup event has already run
_startup_has_run = False


# Initialize Typesense collections on startup
@router.on_event("startup")
async def startup_event():
    """Initialize Typesense collections and sync agents on startup"""
    global _startup_has_run

    # Skip if already run
    if _startup_has_run:
        logger.debug("Startup event already executed, skipping duplicate run")
        return

    _startup_has_run = True

    try:
        # Initialize Typesense collections
        initialized = await TypesenseClient.initialize_collections()
        if initialized:
            # Get all agents from database for syncing
            async def fetch_agent(agent_id):
                return await Database.get_agent(agent_id)

            # Get all agent IDs first
            agents = await Database.list_agents(limit=1000, offset=0)
            agent_ids = [str(agent["id"]) for agent in agents if "id" in agent]

            if agent_ids:
                # Sync agents with Typesense
                results = await TypesenseClient.bulk_sync_agents(agent_ids, fetch_agent)
                success_count = sum(1 for success in results.values() if success)

                logger.info(
                    f"Startup sync: Processed {len(agent_ids)} agents, successfully synced {success_count}"
                )
            else:
                logger.info("No agents found to sync during startup")
    except Exception as e:
        logger.error(f"Error initializing Typesense or syncing agents: {str(e)}")


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
    try:
        # Convert Pydantic model to dict
        agent_data = agent.dict()

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
    """
    Update an existing agent (requires authentication and ownership).
    """
    try:
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in agent_update.dict().items() if v is not None}

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
