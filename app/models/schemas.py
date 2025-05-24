"""Data schemas for the Hibiscus application."""

from typing import List, Optional, Dict, Any, Literal, TypeVar, Generic
from pydantic import BaseModel
from datetime import datetime


# User Models
class UserBase(BaseModel):
    """Base model for user data."""

    email: str
    full_name: str


class User(UserBase):
    """Complete user model with database fields."""

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# API Key Models
class ApiKeyBase(BaseModel):
    """Base model for API key data.

    This model contains the basic attributes of an API key.
    """

    name: str
    expires_at: Optional[datetime] = None


class ApiKey(ApiKeyBase):
    """Complete API key model with database fields.

    This model extends the ApiKeyBase model with additional fields used in the database.
    """

    id: str
    user_id: str
    key: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    status: str = "active"


class ApiKeyCreate(BaseModel):
    """Model for creating API keys."""

    name: str
    expires_in_days: Optional[int] = None
    description: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """Response model for API key data returned to clients."""

    id: str
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    status: str = "active"


# Agent Models
class Capability(BaseModel):
    """Model for agent capabilities."""

    name: str
    description: str


class AgentLink(BaseModel):
    """Model for links associated with an agent."""

    type: str  # 'source-code', 'container-image', 'homepage', 'documentation'
    url: str


class AgentDependency(BaseModel):
    """Model for agent dependencies."""

    type: str  # 'agent', 'tool', 'model'
    name: str
    version: Optional[str] = None


class AgentMetadata(BaseModel):
    """Model for additional metadata about an agent."""

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
    """Base model for agent data."""

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
    """Model for creating a new agent."""

    pass


class AgentUpdate(BaseModel):
    """Model for updating an existing agent."""

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
    """Complete agent model with database fields."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Include verification data from agent_verification table
    did: Optional[str] = None
    public_key: Optional[str] = None
    did_document: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic configuration for the model."""

        from_attributes = True


# Agent Health Models
class AgentHealthBase(BaseModel):
    """Base model for agent health data."""

    agent_id: str
    server_id: str
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class AgentHealthCreate(AgentHealthBase):
    """Model for creating agent health records."""

    pass


class AgentHealth(AgentHealthBase):
    """Complete agent health model with database fields."""

    id: str
    last_ping_at: datetime

    class Config:
        """Pydantic configuration for the model."""

        from_attributes = True


class AgentHealthSummary(BaseModel):
    """Summary of agent health status across servers."""

    agent_id: str
    agent_name: str
    servers: List[Dict[str, Any]]
    status: str
    last_ping_at: datetime


# Federated Registry Models
class FederatedRegistryBase(BaseModel):
    """Base model for federated registry data."""

    name: str
    url: str
    api_key: Optional[str] = None


class FederatedRegistryCreate(FederatedRegistryBase):
    """Model for creating federated registry records."""

    pass


class FederatedRegistry(FederatedRegistryBase):
    """Complete federated registry model with database fields."""

    id: str
    created_at: datetime
    last_synced_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration for the model."""

        from_attributes = True


# Response Models
class ApiResponse(BaseModel):
    """Standard API response model."""

    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


# Generic type for pagination
T = TypeVar("T")


# Pagination Models
class PaginationMetadata(BaseModel):
    """Metadata for paginated responses."""

    total: int
    page: int
    page_size: int
    total_pages: int


# Pagination Response Model
class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""

    items: List[T]
    metadata: PaginationMetadata

    class Config:
        """Pydantic configuration for the model."""

        from_attributes = True