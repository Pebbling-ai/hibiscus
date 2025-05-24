from typing import List, Optional, Dict, Any, Literal, Generic, TypeVar
from pydantic import BaseModel
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
    status: str = "active"


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None
    description: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    status: str = "active"


# Agent Models
class Capability(BaseModel):
    name: str
    description: str


class AgentLink(BaseModel):
    type: str  # 'source-code', 'container-image', 'homepage', 'documentation'
    url: str


class AgentDependency(BaseModel):
    type: str  # 'agent', 'tool', 'model'
    name: str
    version: Optional[str] = None


class AgentMetadata(BaseModel):
    framework: Optional[str] = None  # BeeAI, crewAI, Autogen, AG2, etc.
    programming_language: Optional[str] = None  # Python, JavaScript, etc.
    license: Optional[str] = None  # SPDX license ID
    supported_languages: Optional[List[str]] = None  # ISO 639-1 codes
    deployment_type: Optional[str] = (
        None  # 'fly', 'tunnel', 'docker', 'serverless', etc.
    )
    deployment_url: Optional[str] = None  # URL of deployment if available
    deployment_region: Optional[str] = None  # Region of deployment if applicable


class AgentBase(BaseModel):
    name: str  # RFC 1123 DNS-label compatible
    description: str
    documentation: Optional[str] = None  # Full markdown documentation
    capabilities: Optional[List[Capability]] = None
    domains: Optional[List[str]] = None  # e.g. ['finance', 'healthcare']
    tags: Optional[List[str]] = None
    metadata: Optional[AgentMetadata] = None
    links: Optional[List[AgentLink]] = None
    dependencies: Optional[List[AgentDependency]] = None
    version: str
    author_name: str
    author_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_federated: bool = False
    federation_source: Optional[str] = None
    registry_id: Optional[str] = None  # UUID of the federated registry
    is_team: bool = False
    members: Optional[List[str]] = None
    mode: Optional[Literal["collaborate", "coordinate", "route"]] = None


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    documentation: Optional[str] = None
    capabilities: Optional[List[Capability]] = None
    domains: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[AgentMetadata] = None
    links: Optional[List[AgentLink]] = None
    dependencies: Optional[List[AgentDependency]] = None
    version: Optional[str] = None
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_team: Optional[bool] = None
    members: Optional[List[str]] = None
    mode: Optional[Literal["collaborate", "coordinate", "route"]] = None


class Agent(AgentBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Include verification data from agent_verification table
    did: Optional[str] = None
    public_key: Optional[str] = None
    did_document: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Agent Health Models
class AgentHealthBase(BaseModel):
    agent_id: str
    server_id: str
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class AgentHealthCreate(AgentHealthBase):
    pass


class AgentHealth(AgentHealthBase):
    id: str
    last_ping_at: datetime

    class Config:
        from_attributes = True


class AgentHealthSummary(BaseModel):
    agent_id: str
    agent_name: str
    servers: List[Dict[str, Any]]
    status: str
    last_ping_at: datetime


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


# Generic type for pagination
T = TypeVar("T")


# Pagination Models
class PaginationMetadata(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    metadata: PaginationMetadata
