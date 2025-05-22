from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from datetime import datetime, timezone
import uuid

from app.db.client import Database
from app.models.schemas import ApiResponse, User
from app.utils.supabase_utils import SupabaseClient, USERS_TABLE, API_KEYS_TABLE

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=ApiResponse)
async def register_user(request: Request) -> ApiResponse:
    """
    Register a new user with Clerk session ID.
    
    This endpoint receives user details from Clerk and:
    1. Saves the user details to the users table
    2. Saves the session ID to the api_keys table with name 'session'
    
    The frontend should send:
    - User details (email, full_name)
    - Clerk session ID in the X-API-Key header
    """
    try:
        # Get the session ID from the header
        session_id = request.headers.get("X-API-Key")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID is required in X-API-Key header"
            )
        
        # Get the user data from the request body
        user_data = await request.json()
        if not user_data.get("email") or not user_data.get("full_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and full_name are required"
            )
        
        # Generate a new user ID
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Create the user record
        user = {
            "id": user_id,
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "created_at": now,
            "updated_at": now
        }
        
        # Get the Supabase client
        supabase = SupabaseClient.get_client()
        if not supabase:
            raise Exception("Supabase client not initialized")
            
        # Insert the user into the database
        client = supabase.table(USERS_TABLE).insert(user).execute()
        
        if hasattr(client, "error") and client.error:
            raise Exception(f"Error creating user: {client.error.message}")
        
        # Create an API key record for the session
        api_key = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "key": session_id,
            "name": "session",
            "created_at": now,
            "last_used_at": now,
            "expires_at": None  # Session keys don't expire
        }
        
        # Insert the API key into the database
        key_client = supabase.table(API_KEYS_TABLE).insert(api_key).execute()
        
        if hasattr(key_client, "error") and key_client.error:
            # If API key creation fails, attempt to delete the user
            supabase.table(USERS_TABLE).delete().eq("id", user_id).execute()
            raise Exception(f"Error creating API key: {key_client.error.message}")
        
        return ApiResponse(
            success=True,
            message="User registered successfully",
            data={
                "user_id": user_id,
                "email": user_data.get("email"),
                "full_name": user_data.get("full_name")
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
