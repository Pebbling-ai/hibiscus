from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from math import ceil

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import ApiKeyCreate, ApiKeyResponse, ApiResponse, PaginatedResponse, PaginationMetadata

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/tokens", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_token(
    api_key_data: ApiKeyCreate,
    current_user = Depends(get_current_user_from_api_key),
    response: Response = None,
):
    """
    Create a new API token for the authenticated user.
    
    This endpoint allows frontend users to generate personal access tokens for API usage.
    Tokens can be set to expire after a specified number of days, or they can be permanent.
    """
    try:
        # Calculate expiry date if provided
        expires_at = None
        if hasattr(api_key_data, "expires_at") and api_key_data.expires_at is not None:
            expires_at = api_key_data.expires_at
        elif api_key_data.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=api_key_data.expires_in_days)
        
        # Create the API key
        new_api_key = await Database.create_api_key(
            user_id=current_user["id"],
            name=api_key_data.name,
            expires_at=expires_at.isoformat() if expires_at else None,
            description=api_key_data.description if hasattr(api_key_data, "description") else None,
        )
        
        # Set CORS headers to allow the frontend to access this endpoint
        if response:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        
        return ApiKeyResponse(
            id=new_api_key["id"],
            name=new_api_key["name"],
            key=new_api_key["key"],
            created_at=new_api_key["created_at"],
            expires_at=new_api_key.get("expires_at"),
            description=new_api_key.get("description"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tokens", response_model=PaginatedResponse[ApiKeyResponse])
async def list_api_tokens(
    page: int = Query(1, description="Page number", ge=1),
    size: int = Query(20, description="Page size", ge=1, le=100),
    current_user = Depends(get_current_user_from_api_key),
):
    """
    List all API tokens for the authenticated user (paginated).
    """
    try:
        # Calculate offset from page and size
        offset = (page - 1) * size
        
        # Get the count first
        total_count = await Database.count_api_keys(user_id=current_user["id"])
        
        # Then get the paginated results
        tokens = await Database.list_api_keys(
            user_id=current_user["id"],
            limit=size,
            offset=offset
        )
        
        # Calculate pagination metadata
        total_pages = ceil(total_count / size)
        
        # Return paginated response with updated structure
        return PaginatedResponse(
            items=tokens,
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


@router.delete("/tokens/{token_id}", response_model=ApiResponse)
async def delete_api_token(
    token_id: str,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Delete an API token.
    """
    try:
        # Delete the API key
        success = await Database.delete_api_key(
            key_id=token_id,
            user_id=current_user["id"],
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API token not found",
            )
        
        return ApiResponse(
            success=True,
            message="API token deleted successfully",
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/profile", response_model=ApiResponse)
async def get_user_profile(
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Get the profile of the authenticated user.
    """
    return ApiResponse(
        success=True,
        data={
            "id": current_user["id"],
            "email": current_user["email"],
            "full_name": current_user["full_name"],
        },
    )
