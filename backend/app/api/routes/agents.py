from typing import List, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from loguru import logger

from app.db.client import Database
from app.core.auth import get_current_user_from_api_key
from app.models.schemas import Agent, AgentCreate, AgentUpdate, PaginatedResponse, PaginationMetadata
from app.utils.typesense_utils import TypesenseClient

router = APIRouter(prefix="/agents", tags=["agents"])

# Flag to track if startup event has already run
_startup_has_run = False

# Initialize Typesense collections on startup
@router.on_event("startup")
async def startup_event():
    """Initialize Typesense collections and sync agents on startup"""
    global _startup_has_run
    
    # Skip if already run
    if _startup_has_run:
        logger.debug("Startup event already executed, skipping duplicate run")
        return
        
    _startup_has_run = True
    
    try:
        # Initialize Typesense collections
        initialized = await TypesenseClient.initialize_collections()
        if initialized:
            # Get all agents from database for syncing
            async def fetch_agent(agent_id):
                return await Database.get_agent(agent_id)
                
            # Get all agent IDs first
            agents = await Database.list_agents(limit=1000, offset=0)
            agent_ids = [str(agent["id"]) for agent in agents if "id" in agent]
            
            if agent_ids:
                # Sync agents with Typesense
                results = await TypesenseClient.bulk_sync_agents(agent_ids, fetch_agent)
                success_count = sum(1 for success in results.values() if success)
                
                logger.info(f"Startup sync: Processed {len(agent_ids)} agents, successfully synced {success_count}")
            else:
                logger.info("No agents found to sync during startup")
    except Exception as e:
        logger.error(f"Error initializing Typesense or syncing agents: {str(e)}")


@router.get("/", response_model=PaginatedResponse[Agent])
async def list_agents(
    search: Optional[str] = Query(None, description="Search term to filter agents by name, description, or documentation"),
    is_team: Optional[bool] = Query(None, description="Filter agents by team status"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100)
):
    """List agents with pagination and optional filtering."""
    try:
        # Calculate offset
        offset = (page - 1) * page_size

        # search agents in typesense
        if search:
            agents = await TypesenseClient.search_agents(search)
            agents_id = [agent["id"] for agent in agents.get('hits', [])]
            agents = await Database.list_agents(
                agent_ids=agents_id,
                is_team=is_team,
                limit=page_size,
                offset=offset
            )

        
        # Get agents for current page
        agents = await Database.list_agents(
            is_team=is_team,
            limit=page_size,
            offset=offset
        )
        
        # Get total count for pagination metadata
        total_count = await Database.count_agents(
            registry_id=None if not is_team else is_team
        )
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size)
        
        # Construct paginated response
        response = {
            "items": agents,
            "metadata": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    
    # Otherwise, get the agent from the local database
    agent = await Database.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    
    return agent


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user = Depends(get_current_user_from_api_key),
):
    """Create a new agent with DID verification and deployment tracking."""
    from app.utils.did_utils import DIDManager, MltsProtocolHandler
    
    # Initialize data structures
    agent_data = agent.dict()
    agent_data.update({"is_federated": False, "federation_source": None, 
                      "registry_id": None, "user_id": current_user["id"]})
    verification_data = {}
    response_data = {}
    
    # Extract security credentials to verification table
    for field in ["did", "did_document", "public_key"]:
        if field in agent_data:
            verification_data[field] = agent_data.pop(field)
    
    # Handle DID generation
    if not verification_data.get("did") and not verification_data.get("public_key"):
        # Generate new keypair
        pub_key, priv_key = MltsProtocolHandler().generate_keys()
        verification_data["public_key"] = pub_key
        response_data["private_key"] = priv_key
    
    # Ensure we have a DID
    if not verification_data.get("did") and verification_data.get("public_key"):
        verification_data["did"] = DIDManager.generate_did(
            public_key=verification_data["public_key"]
        )
    
    # Ensure we have a DID document
    if verification_data.get("did") and verification_data.get("public_key") and not verification_data.get("did_document"):
        verification_data["did_document"] = DIDManager.generate_did_document(
            verification_data["did"], verification_data["public_key"], verification_method="mlts"
        )
    
    # Validate team members if this is a team
    if agent_data.get("is_team") and agent_data.get("members"):
        invalid = [mid for mid in agent_data["members"] if not await Database.get_agent(mid)]
        if invalid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                               detail=f"Invalid member IDs: {', '.join(invalid)}")
    
    try:
        # Create agent record
        created_agent = await Database.create_agent(agent_data)

        # Create agent record in Typesense
        typesense_record_created = await TypesenseClient.create_agent(created_agent)
        if not typesense_record_created:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to create agent record in Typesense")
        
        # Store verification data if complete
        if verification_data.get("did") and verification_data.get("public_key"):
            verification_data.update({
                "agent_id": created_agent["id"],
                "verification_method": "mlts",
                "key_type": "rsa"
            })
            await Database.create_agent_verification(verification_data)
        
        # Return response with private key if generated
        if "private_key" in response_data:
            agent_dict = created_agent.dict() if hasattr(created_agent, "dict") else created_agent
            return JSONResponse(content={**agent_dict, **response_data})
        
        return created_agent
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    current_user = Depends(get_current_user_from_api_key),
):
    """
    Update an existing agent (requires authentication and ownership).
    """
    try:
        # Check if agent exists and belongs to the current user
        existing_agent = await Database.get_agent(agent_id)
        if not existing_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with id {agent_id} not found",
            )
        
        if existing_agent["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this agent",
            )
        
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in agent_update.dict().items() if v is not None}
        
        # Validate team members if this is a team and members are being updated
        if update_data.get("members"):
            invalid_members = []
            for member_id in update_data["members"]:
                member = await Database.get_agent(member_id)
                if not member:
                    invalid_members.append(member_id)
            
            if invalid_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid member IDs: {', '.join(invalid_members)}",
                )
        
        # Update the agent
        updated_agent = await Database.update_agent(agent_id, update_data)
        return updated_agent
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
