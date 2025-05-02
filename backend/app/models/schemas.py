from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# User Models
class UserBase(BaseModel):
    email: str
    full_name: str

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# API Key Models
class ApiKeyBase(BaseModel):
    name: str
    expires_at: Optional[datetime] = None

class ApiKey(ApiKeyBase):
    id: str
    user_id: str
    key: str
    created_at: datetime
    last_used_at: Optional[datetime] = None

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyResponse(ApiKeyBase):
    id: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None

# Agent Models
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

    class Config:
        from_attributes = True

# Federated Registry Models
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

    class Config:
        from_attributes = True

# Response Models
class ApiResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
