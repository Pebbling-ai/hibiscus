from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from math import ceil
import httpx
import json
from datetime import datetime

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import FederatedRegistry, FederatedRegistryCreate, ApiResponse, PaginatedResponse, PaginationMetadata, Agent

router = APIRouter(prefix="/federated-registries", tags=["federated-registries"])


@router.get("/", response_model=PaginatedResponse[FederatedRegistry])
async def list_federated_registries(
    page: int = Query(1, description="Page number", ge=1),
    size: int = Query(20, description="Page size", ge=1, le=100),
    current_user = Depends(get_current_user_from_api_key),
):
    """
    List all federated registries (requires authentication, paginated).
    """
    try:
        # Calculate offset from page and size
        offset = (page - 1) * size
        
        # Get the count first
        total_count = await Database.count_federated_registries()
        
        # Then get the paginated results
        registries = await Database.list_federated_registries(limit=size, offset=offset)
        
        # Calculate pagination metadata
        total_pages = ceil(total_count / size)
        
        # Return paginated response with updated structure
        return PaginatedResponse(
            items=registries,
            metadata=PaginationMetadata(
                total=total_count,
                page=page,
                page_size=size,
                total_pages=total_pages
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/", response_model=FederatedRegistry)
async def add_federated_registry(
    registry: FederatedRegistryCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Add a new federated registry (requires authentication).
    """
    try:
        # Validate the registry URL by making a request to it
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{registry.url.rstrip('/')}/")
                response.raise_for_status()
            except httpx.HTTPError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to connect to the federated registry",
                )
        
        # Create the federated registry
        registry_data = registry.dict()
        created_registry = await Database.add_federated_registry(registry_data)
        return created_registry
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{registry_id}/sync", response_model=ApiResponse)
async def sync_federated_registry(
    registry_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Synchronize agents from a federated registry.
    """
    try:
        # Get the federated registry
        registry = await Database.get_federated_registry(registry_id)
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Federated registry not found",
            )
        
        # Start background synchronization task
        background_tasks.add_task(sync_registry_agents, registry)
        
        return ApiResponse(
            success=True,
            message=f"Synchronization with {registry['name']} started",
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{registry_id}/agents", response_model=PaginatedResponse[Agent])
async def list_federated_registry_agents(
    registry_id: str,
    page: int = Query(1, description="Page number", ge=1),
    size: int = Query(20, description="Page size", ge=1, le=100),
    current_user = Depends(get_current_user_from_api_key),
):
    """
    List all agents from a specific federated registry.
    """
    try:
        # Calculate offset from page and size
        offset = (page - 1) * size
        
        # Get the federated registry
        registry = await Database.get_federated_registry(registry_id)
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Federated registry not found",
            )
        
        # Get the count first
        total_count = await Database.count_agents(registry_id=registry_id)
        
        # Then get the paginated results
        agents = await Database.list_agents(
            limit=size,
            offset=offset,
            registry_id=registry_id
        )
        
        # Calculate pagination metadata
        total_pages = ceil(total_count / size)
        
        # Return paginated response with updated structure
        return PaginatedResponse(
            items=agents,
            metadata=PaginationMetadata(
                total=total_count,
                page=page,
                page_size=size,
                total_pages=total_pages
            )
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Helper function for background synchronization
async def sync_registry_agents(registry):
    """
    Synchronize agents from a federated registry.
    """
    try:
        # Make request to the federated registry to get agents
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            
            # Add API key if available
            if registry.get("api_key"):
                headers["X-API-Key"] = registry["api_key"]
            
            # Get agents from the federated registry
            response = await client.get(
                f"{registry['url'].rstrip('/')}/agents",
                headers=headers
            )
            
            # Check if successful
            if response.status_code != 200:
                print(f"Failed to sync with {registry['name']}: Status {response.status_code}")
                return
            
            # Parse response
            agents_data = response.json()
            
            # Process each agent
            for agent_data in agents_data.get("items", []):
                # Add federation metadata
                agent_data["is_federated"] = True
                agent_data["federation_source"] = registry["url"]
                agent_data["registry_id"] = registry["id"]
                
                # Check if agent already exists (by name or unique identifier)
                existing_agent = None
                if "id" in agent_data:
                    existing_agent = await Database.get_agent_by_federation_id(
                        federation_id=agent_data["id"], 
                        registry_id=registry["id"]
                    )
                
                if existing_agent:
                    # Update existing agent
                    await Database.update_federated_agent(existing_agent["id"], agent_data)
                else:
                    # Create new federated agent
                    await Database.create_federated_agent(agent_data)
        
        # Update last synced timestamp
        await Database.update_federated_registry_sync_time(registry["id"])
        
    except Exception as e:
        print(f"Error synchronizing with {registry['name']}: {str(e)}")
