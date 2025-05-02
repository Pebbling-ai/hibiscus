from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import ApiKeyCreate, ApiKeyResponse, ApiResponse

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/tokens", response_model=ApiKeyResponse)
async def create_api_token(
    api_key_data: ApiKeyCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Create a new API token for the authenticated user.
    """
    try:
        # Calculate expiry date if provided
        expires_at = None
        if api_key_data.expires_at:
            expires_at = api_key_data.expires_at
        elif getattr(api_key_data, "expires_in_days", None):
            expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_in_days)
        
        # Create the API key
        new_api_key = await Database.create_api_key(
            user_id=current_user["id"],
            name=api_key_data.name,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        
        return ApiKeyResponse(
            id=new_api_key["id"],
            name=new_api_key["name"],
            key=new_api_key["key"],
            created_at=new_api_key["created_at"],
            expires_at=new_api_key.get("expires_at"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tokens", response_model=List[ApiKeyResponse])
async def list_api_tokens(
    current_user = Depends(get_current_user_from_api_key),
):
    """
    List all API tokens for the authenticated user.
    """
    try:
        # Get the API keys for the user
        api_keys = await Database.list_api_keys(user_id=current_user["id"])
        
        # Convert to response format
        return [
            ApiKeyResponse(
                id=api_key["id"],
                name=api_key["name"],
                key=api_key["key"],
                created_at=api_key["created_at"],
                expires_at=api_key.get("expires_at"),
            )
            for api_key in api_keys
        ]
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
