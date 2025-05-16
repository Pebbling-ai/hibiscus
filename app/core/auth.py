import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

from app.db.client import Database

# Load environment variables
load_dotenv()

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class Auth:
    @staticmethod
    async def get_api_key(api_key: str = Depends(API_KEY_HEADER)) -> Dict[str, Any]:
        """
        Validate API key and return associated user data.
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is missing",
            )
        
        # Validate API key against database
        key_data = await Database.validate_api_key(api_key)
        
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        
        # Update last_used_at timestamp
        # This would be implemented in the Database class
        
        return key_data

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return encoded_jwt

    @staticmethod
    async def generate_api_key(user_id: str, name: str, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a new API key for a user.
        """
        # Generate API key
        return await Database.create_api_key(user_id, name, expires_at.isoformat() if expires_at else None)


async def get_current_user_from_api_key(api_key_data: Dict[str, Any] = Depends(Auth.get_api_key)) -> Dict[str, Any]:
    """
    Get current user from API key.
    """
    return api_key_data["user"]
