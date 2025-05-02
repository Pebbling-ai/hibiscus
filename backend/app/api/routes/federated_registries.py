from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import httpx

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import FederatedRegistry, FederatedRegistryCreate, ApiResponse

router = APIRouter(prefix="/federated-registries", tags=["federated-registries"])


@router.get("/", response_model=List[FederatedRegistry])
async def list_federated_registries(
    current_user = Depends(get_current_user_from_api_key),
):
    """
    List all federated registries (requires authentication).
    """
    try:
        registries = await Database.list_federated_registries()
        return registries
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
