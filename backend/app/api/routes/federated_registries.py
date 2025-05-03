from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from math import ceil
import httpx

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import FederatedRegistry, FederatedRegistryCreate, ApiResponse, PaginatedResponse

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
        has_more = page < total_pages
        
        # Return paginated response
        return PaginatedResponse(
            items=registries,
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
