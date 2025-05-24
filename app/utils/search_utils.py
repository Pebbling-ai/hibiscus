"""Utilities for searching and managing agents in the system."""

import math
from typing import Dict, Optional, Any
from loguru import logger
from app.db.client import Database
from app.utils.typesense_utils import TypesenseClient
from app.utils.did_utils import DIDManager, MltsProtocolHandler
from fastapi import HTTPException, status


async def search_agents(
    search: Optional[str] = None,
    is_team: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Search for agents with hybrid search using Typesense and database.

    Args:
        search: Optional search term
        is_team: Optional team filter
        page: Page number (starting from 1)
        page_size: Number of items per page

    Returns:
        Paginated response with agents and metadata
    """
    # Calculate offset
    offset = (page - 1) * page_size

    agent_ids = None

    # Search agents in typesense if search term is provided
    if search:
        try:
            search_results = await TypesenseClient.search_agents(search)

            # If no search results, return empty paginated response
            if not search_results.get("hits"):
                return {
                    "items": [],
                    "metadata": {
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                    },
                }

            # Extract agent IDs from search results
            agent_ids = [hit.get("id") for hit in search_results.get("hits", [])]

            # Return empty response if no matching agents
            if not agent_ids:
                return {
                    "items": [],
                    "metadata": {
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                    },
                }

            # Get total count for search results
            total_count = len(agent_ids)
        except Exception as search_error:
            logger.error(f"Typesense search failed: {search_error}")
            # Fall back to database search if Typesense fails
            agent_ids = None

    # Get agents from database (with or without agent_ids filter)
    agents = await Database.list_agents(
        limit=page_size,
        offset=offset,
        verification_data_required=False,
        is_team=is_team,
        agent_ids=agent_ids,
    )

    # Get total count for pagination if not search or if search failed
    if search and agent_ids is not None:
        # We already have the total count from search results
        total_count = len(agent_ids)
    else:
        # Get count from database for normal listing
        total_count = await Database.count_agents(
            registry_id=None if not is_team else is_team
        )

    # Calculate total pages
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    # Construct paginated response
    response = {
        "items": agents,
        "metadata": {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }

    return response


async def create_agent_with_verification(
    agent_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    Create a new agent with DID verification and deployment tracking.

    Args:
        agent_data: Agent data dictionary
        user_id: ID of the user creating the agent

    Returns:
        Dictionary containing the created agent and optionally a private key
    """
    # Initialize data structures
    agent_data.update(
        {
            "is_federated": False,
            "federation_source": None,
            "registry_id": None,
            "user_id": user_id,
        }
    )
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
    if (
        verification_data.get("did")
        and verification_data.get("public_key")
        and not verification_data.get("did_document")
    ):
        verification_data["did_document"] = DIDManager.generate_did_document(
            verification_data["did"],
            verification_data["public_key"],
            verification_method="mlts",
        )

    # Validate team members if this is a team
    if agent_data.get("is_team") and agent_data.get("members"):
        invalid_members = []
        for member_id in agent_data["members"]:
            member = await Database.get_agent(member_id)
            if not member:
                invalid_members.append(member_id)

        if invalid_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member IDs: {', '.join(invalid_members)}",
            )

    try:
        # Create agent record
        created_agent = await Database.create_agent(agent_data)

        # Create agent record in Typesense
        typesense_record_created = await TypesenseClient.create_agent(created_agent)
        if not typesense_record_created:
            logger.error(
                f"Failed to create agent record in Typesense for agent ID: {created_agent['id']}"
            )
            # Consider whether to fail or continue - currently continuing

        # Store verification data if complete
        if verification_data.get("did") and verification_data.get("public_key"):
            verification_data.update(
                {
                    "agent_id": created_agent["id"],
                    "verification_method": "mlts",
                    "key_type": "rsa",
                }
            )
            await Database.create_agent_verification(verification_data)

        # Return result with private key if generated
        result = created_agent
        if "private_key" in response_data:
            if hasattr(created_agent, "dict"):
                agent_dict = created_agent.dict()
            else:
                agent_dict = created_agent
            result = {**agent_dict, **response_data}

        return result

    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}",
        )


async def update_agent_with_typesense(
    agent_id: str, update_data: Dict[str, Any], current_user_id: str
) -> Dict[str, Any]:
    """
    Update an agent with Typesense synchronization.

    Args:
        agent_id: ID of the agent to update
        update_data: Dictionary containing the fields to update
        current_user_id: ID of the user making the update

    Returns:
        Updated agent data
    """
    # Check if agent exists and belongs to the current user
    existing_agent = await Database.get_agent(agent_id)
    if not existing_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    if existing_agent["user_id"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this agent",
        )

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

    try:
        # Update the agent in the database
        updated_agent = await Database.update_agent(agent_id, update_data)

        # Check if any Typesense-relevant fields were updated
        typesense_fields = {"name", "description", "domains", "tags", "mode"}
        typesense_update_needed = any(
            field in update_data for field in typesense_fields
        )

        # Update in Typesense if relevant fields changed
        if typesense_update_needed:
            try:
                # Update the agent in Typesense
                typesense_success = await TypesenseClient.update_agent(
                    agent_id, updated_agent
                )
                if not typesense_success:
                    # Log warning but don't fail the request if Typesense update fails
                    logger.warning(f"Failed to update agent {agent_id} in Typesense")
            except Exception as ts_error:
                # Log the error but don't fail the whole request due to Typesense issues
                logger.error(f"Error updating agent in Typesense: {str(ts_error)}")

        return updated_agent
    except Exception as e:
        logger.error(f"Error updating agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}",
        )


async def get_agent_by_id(agent_id: str) -> Dict[str, Any]:
    """
    Get a specific agent by ID.

    Args:
        agent_id: ID of the agent to retrieve

    Returns:
        Agent data dictionary

    Raises:
        HTTPException: If agent not found
    """
    agent = await Database.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    return agent
