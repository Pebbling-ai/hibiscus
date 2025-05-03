from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from math import ceil

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import (
    AgentHealthCreate, 
    AgentHealth, 
    AgentHealthSummary, 
    PaginatedResponse
)

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/ping", response_model=AgentHealth, status_code=status.HTTP_200_OK)
async def agent_health_ping(
    health_data: AgentHealthCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Record a health check ping from an agent.
    
    The agent must send its ID, server ID, and status. Each ping will extend the
    TTL of the health record for 1 day. If the agent doesn't ping within that period,
    the record will be automatically removed from the database.
    """
    try:
        # Create or update the health record
        health_record = await Database.record_agent_health(health_data.dict())
        return health_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/agents/{agent_id}", response_model=List[AgentHealth])
async def get_agent_health(agent_id: str):
    """
    Get the health status for a specific agent across all servers.
    """
    try:
        health_records = await Database.get_agent_health(agent_id)
        return health_records
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/", response_model=PaginatedResponse[AgentHealth])
async def list_agent_health(
    server_id: Optional[str] = Query(None, description="Filter by server ID"),
    page: int = Query(1, description="Page number", ge=1),
    size: int = Query(20, description="Page size", ge=1, le=100),
):
    """
    List health status for all agents, optionally filtered by server.
    """
    try:
        # Calculate offset from page and size
        offset = (page - 1) * size
        
        # Get the count first
        total_count = await Database.count_agent_health(server_id=server_id)
        
        # Then get the paginated results
        health_records = await Database.list_agent_health(
            limit=size,
            offset=offset,
            server_id=server_id
        )
        
        # Calculate pagination metadata
        total_pages = ceil(total_count / size)
        has_more = page < total_pages
        
        # Return paginated response
        return PaginatedResponse(
            items=health_records,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages,
            has_more=has_more
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/summary", response_model=List[AgentHealthSummary])
async def get_agent_health_summary():
    """
    Get a summary of agent health status grouped by agent.
    """
    try:
        summary = await Database.get_agent_health_summary()
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )