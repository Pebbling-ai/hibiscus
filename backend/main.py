import os
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import httpx
import asyncio
import uuid

# Load environment variables
load_dotenv()

# Import local modules
from db import Database
from federation import get_federated_agents, get_federated_agent

# Initialize FastAPI app
app = FastAPI(
    title="Hibiscus Agent Registry API",
    description="Backend API for Hibiscus Agent Registry",
    version="0.1.0",
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# Models (imported from schemas.py but included here for simplicity)
class AgentBase(BaseModel):
    name: str
    description: str
    category: str
    capabilities: List[str]
    api_endpoint: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_federated: bool = False
    federation_source: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class Agent(AgentBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class FederatedRegistryBase(BaseModel):
    name: str
    url: str
    api_key: Optional[str] = None


class FederatedRegistryCreate(FederatedRegistryBase):
    pass


class FederatedRegistry(FederatedRegistryBase):
    id: str
    created_at: datetime
    last_synced_at: Optional[datetime] = None


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApiResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


# Authentication dependencies
async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
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
    
    return key_data


async def get_current_user(api_key_data: Dict[str, Any] = Depends(get_api_key)):
    return api_key_data["user"]


# Error handling
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": f"An unexpected error occurred: {str(exc)}",
        },
    )


# Routes

@app.get("/", response_model=ApiResponse)
async def root():
    return {
        "success": True,
        "message": "Welcome to Hibiscus Agent Registry API",
        "data": {
            "version": "0.1.0",
            "documentation": "/docs",
        }
    }


# Agent routes

@app.get("/agents", response_model=List[Agent])
async def list_agents(
    search: Optional[str] = None,
    category: Optional[str] = None,
    include_federated: bool = True,
    skip: int = 0,
    limit: int = 100,
):
    """
    List all agents with optional filtering.
    """
    # Get local agents
    local_agents = await Database.list_agents(
        search=search,
        category=category,
        include_federated=False,  # We'll handle federated agents separately
        skip=skip,
        limit=limit,
    )
    
    # Get federated agents if requested
    federated_agents = []
    if include_federated:
        federated_agents = await get_federated_agents(
            search=search,
            category=category,
            skip=skip,
            limit=limit,
        )
    
    # Combine and limit results
    all_agents = local_agents + federated_agents
    
    # Simple sorting by creation date
    all_agents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return all_agents[:limit]


@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, federation_source: Optional[str] = None):
    """
    Get a specific agent by ID.
    """
    # If federation_source is provided, get the agent from the federated registry
    if federation_source:
        federated_agent = await get_federated_agent(agent_id, federation_source)
        if not federated_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with id {agent_id} not found in federated registry {federation_source}",
            )
        return federated_agent
    
    # Otherwise, get the agent from the local database
    agent = await Database.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    
    return agent


@app.post("/agents", response_model=Agent)
async def create_agent(
    agent: AgentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new agent (requires authentication).
    """
    # Ensure the agent is not marked as federated
    agent_data = agent.dict()
    agent_data["is_federated"] = False
    agent_data["federation_source"] = None
    
    # Create the agent
    try:
        created_agent = await Database.create_agent(
            agent_data=agent_data,
            owner_id=current_user["id"],
        )
        return created_agent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Federated registry routes

@app.get("/federated-registries", response_model=List[FederatedRegistry])
async def list_federated_registries(
    current_user: Dict[str, Any] = Depends(get_current_user),
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


@app.post("/federated-registries", response_model=FederatedRegistry)
async def add_federated_registry(
    registry: FederatedRegistryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
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


# API Key routes

@app.post("/user/tokens", response_model=ApiKeyResponse)
async def create_api_token(
    api_key_data: ApiKeyCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new API token for the authenticated user.
    """
    try:
        # Calculate expiry date if provided
        expires_at = None
        if api_key_data.expires_in_days:
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


@app.get("/user/tokens", response_model=List[ApiKeyResponse])
async def list_api_tokens(
    current_user: Dict[str, Any] = Depends(get_current_user),
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


@app.delete("/user/tokens/{token_id}", response_model=ApiResponse)
async def delete_api_token(
    token_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
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


@app.get("/user/profile", response_model=ApiResponse)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
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


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run("main:app", host=host, port=port, reload=True)
