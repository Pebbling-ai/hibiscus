"""
Typesense utility functions for managing search operations.
This module provides an abstraction layer for Typesense operations.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import typesense
from typesense.exceptions import TypesenseClientError
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
AGENTS_COLLECTION = "agents"
AGENT_SCHEMA = {
    "name": AGENTS_COLLECTION,
    "fields": [
        {"name": "agent_id", "type": "string", "facet": True, "sort": True},
        {"name": "name", "type": "string", "facet": True, "sort": True},
        {"name": "description", "type": "string"},
        {"name": "domains", "type": "string[]", "optional": True},
        {"name": "tags", "type": "string[]", "optional": True, "facet": True},
        {"name": "mode", "type": "string", "optional": True, "facet": True},
        {"name": "created_at", "type": "int64", "optional": True, "sort": True},
        {"name": "updated_at", "type": "int64", "optional": True, "sort": True},
    ],
    "default_sorting_field": "agent_id",
    "token_separators": ["_", "-"],
}


class TypesenseClient:
    """
    A singleton client for Typesense operations.
    Manages initialization, collections, and document operations.
    """

    _instance = None
    _client = None

    @classmethod
    def get_client(cls) -> Optional[typesense.Client]:
        """
        Get the initialized Typesense client instance.
        Uses the Singleton pattern to ensure only one client exists.

        Returns:
            typesense.Client: The Typesense client instance or None if not configured
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._client

    def __init__(self):
        """
        Initialize the Typesense client with credentials from environment variables.
        """
        if TypesenseClient._instance is not None:
            raise Exception("TypesenseClient is a singleton. Use get_client() instead.")

        TypesenseClient._instance = self

        # Get credentials from environment variables
        api_key = os.getenv("TYPESENSE_API_KEY")
        host = os.getenv("TYPESENSE_HOST", "localhost")
        port = os.getenv("TYPESENSE_PORT", "8108")
        protocol = os.getenv("TYPESENSE_PROTOCOL", "http")

        if not api_key:
            logger.warning("TYPESENSE_API_KEY not set. Search operations will fail.")
            TypesenseClient._client = None
        else:
            try:
                TypesenseClient._client = typesense.Client(
                    {
                        "api_key": api_key,
                        "nodes": [{"host": host, "port": port, "protocol": protocol}],
                        "connection_timeout_seconds": 2,
                    }
                )
                logger.info(f"Typesense client initialized with host: {host}:{port}")
            except TypesenseClientError as e:
                logger.error(f"Failed to initialize Typesense client: {str(e)}")
                TypesenseClient._client = None

    @classmethod
    async def initialize_collections(cls) -> bool:
        """
        Initialize Typesense collections if they don't exist.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning(
                "Typesense client not initialized. Cannot create collections."
            )
            return False

        try:
            # Check if collection exists
            try:
                client.collections[AGENTS_COLLECTION].retrieve()
                logger.info(f"Collection '{AGENTS_COLLECTION}' already exists.")
            except TypesenseClientError:
                # Create collection if it doesn't exist
                client.collections.create(AGENT_SCHEMA)
                logger.info(f"Collection '{AGENTS_COLLECTION}' created successfully.")

            return True
        except TypesenseClientError as e:
            logger.error(f"Error initializing Typesense collections: {str(e)}")
            return False

    @classmethod
    async def create_agent(cls, agent_data: Dict[str, Any]) -> bool:
        """
        Index an agent in Typesense.

        Args:
            agent_data: Agent data to index

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning("Typesense client not initialized. Cannot index agent.")
            return False

        try:
            # Ensure agent has an ID
            if "id" not in agent_data or not agent_data["id"]:
                logger.error("Cannot index agent without an ID")
                return False

            # Convert agent data to Typesense document format
            document = cls._convert_agent_to_document(agent_data)

            # Make sure we have agent_id field from the ID
            agent_id = str(agent_data["id"])
            document["agent_id"] = agent_id

            # Important: Set 'id' field for Typesense
            document["id"] = agent_id

            # Use upsert which avoids duplicates and handles both create/update
            client.collections[AGENTS_COLLECTION].documents.upsert(document)
            logger.info(f"Agent upserted in Typesense with ID: {agent_id}")

            return True
        except Exception as e:
            logger.error(f"Error indexing agent in Typesense: {str(e)}")
            return False

    @classmethod
    async def update_agent(cls, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """
        Update an agent in Typesense.

        Args:
            agent_id: ID of the agent to update
            agent_data: Updated agent data

        Returns:
            bool: True if update was successful, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning("Typesense client not initialized. Cannot update agent.")
            return False

        try:
            # Convert agent data to Typesense document format
            document = cls._convert_agent_to_document(agent_data)

            # Update document
            (client.collections[AGENTS_COLLECTION]
                .documents[agent_id]
                .update(document))
            logger.info(f"Agent updated in Typesense with ID: {agent_id}")
            return True
        except TypesenseClientError as e:
            logger.error(f"Error updating agent in Typesense: {str(e)}")
            return False

    @classmethod
    async def delete_agent(cls, agent_id: str) -> bool:
        """
        Delete an agent from Typesense.

        Args:
            agent_id: ID of the agent to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning("Typesense client not initialized. Cannot delete agent.")
            return False

        try:
            # In Typesense we use the agent_id field as document identifier
            # First check if document exists by searching for it
            search_params = {
                "q": "*",
                "query_by": "name",  # This field doesn't matter for this query
                "filter_by": f"agent_id:={agent_id}",
            }

            search_results = client.collections[AGENTS_COLLECTION].documents.search(
                search_params
            )

            # If agent exists in search results, delete it
            if search_results.get("found", 0) > 0:
                hits = search_results.get("hits", [])
                for hit in hits:
                    document = hit.get("document", {})
                    document_id = document.get(
                        "agent_id"
                    )  # Use agent_id as the identifier
                    if document_id:
                        # Delete document by ID
                        client.collections[AGENTS_COLLECTION].documents[
                            document_id
                        ].delete()
                        logger.info(f"Agent deleted from Typesense with ID: {agent_id}")

            return True
        except TypesenseClientError as e:
            logger.error(f"Error deleting agent from Typesense: {str(e)}")
            return False

    @classmethod
    async def search_agents(
        cls,
        query: str,
        page: int = 1,
        per_page: int = 20,
        filters: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for agents in Typesense.

        Args:
            query: Search query string
            page: Page number (starting from 1)
            per_page: Number of results per page
            filters: Typesense filter expression (e.g. "tags:=[ai]")

        Returns:
            Dict containing search results or empty dict if search failed
        """
        client = cls.get_client()
        if not client:
            logger.warning("Typesense client not initialized. Cannot search agents.")
            return {"found": 0, "hits": []}

        try:
            search_parameters = {
                "q": query,
                "query_by": "name,description,domains,tags",
                "sort_by": "_text_match:desc,created_at:desc",
                "page": page,
                "per_page": per_page,
                "highlight_full_fields": "name,description",
            }

            # Add filters if provided
            if filters:
                search_parameters["filter_by"] = filters

            # Execute search
            results = client.collections[AGENTS_COLLECTION].documents.search(
                search_parameters
            )

            # Process results
            processed_results = {
                "found": results.get("found", 0),
                "page": results.get("page", 1),
                "per_page": per_page,
                "hits": [],
            }

            # Extract document data from hits and map agent_id back to id for compatibility
            for hit in results.get("hits", []):
                document = hit.get("document", {})
                highlights = hit.get("highlights", [])

                # Map agent_id back to id for compatibility with the rest of the system
                if "agent_id" in document and "id" not in document:
                    document["id"] = document["agent_id"]

                # Add highlight information
                document["_highlights"] = highlights
                processed_results["hits"].append(document)

            return processed_results
        except TypesenseClientError as e:
            logger.error(f"Error searching agents in Typesense: {str(e)}")
            return {"found": 0, "hits": []}

    @classmethod
    async def index_agent_batch(cls, agents: List[Dict[str, Any]]) -> bool:
        """
        Index a batch of agents in Typesense.

        Args:
            agents: List of agent data to index

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning("Typesense client not initialized. Cannot index agents.")
            return False

        try:
            # Convert agent data to Typesense document format
            documents = [cls._convert_agent_to_document(agent) for agent in agents]

            # Index documents in batch
            response = client.collections[AGENTS_COLLECTION].documents.import_(
                documents, {"action": "upsert"}
            )

            # Check for errors
            if isinstance(response, list):
                success_count = sum(1 for item in response if not item.get("error"))
                logger.info(
                    f"Indexed {success_count}/{len(documents)} agents in Typesense"
                )
                return success_count == len(documents)

            return True
        except TypesenseClientError as e:
            logger.error(f"Error batch indexing agents in Typesense: {str(e)}")
            return False

    @classmethod
    async def sync_agent(cls, agent_id: str, fetch_agent_fn) -> bool:
        """
        Sync a single agent from the database to Typesense.

        Args:
            agent_id: ID of the agent to sync
            fetch_agent_fn: Async function that takes agent_id and returns agent data

        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            # Ensure collection exists
            await cls.initialize_collections()

            # Fetch agent from database
            agent = await fetch_agent_fn(agent_id)

            # Index agent in Typesense
            return await cls.create_agent(agent)
        except Exception as e:
            logger.error(f"Error syncing agent to Typesense: {str(e)}")
            return False

    @classmethod
    async def bulk_sync_agents(
        cls, agent_ids: List[str], fetch_agent_fn
    ) -> Dict[str, bool]:
        """
        Sync multiple specific agents from the database to Typesense,
        skipping agents that already exist.

        Args:
            agent_ids: List of agent IDs to sync
            fetch_agent_fn: Async function that takes agent_id and returns agent data

        Returns:
            Dict mapping agent IDs to success status
        """
        results = {}
        already_exists_count = 0

        # Initialize collection if needed
        await cls.initialize_collections()

        # Process each agent
        for agent_id in agent_ids:
            # Check if agent already exists in Typesense
            exists = await cls.check_agent_exists(agent_id)

            if exists:
                # Skip agents that already exist
                results[agent_id] = True
                already_exists_count += 1
                continue

            # Sync agent if it doesn't exist
            results[agent_id] = await cls.sync_agent(agent_id, fetch_agent_fn)

        # Log summary
        if already_exists_count > 0:
            logger.info(
                f"Skipped {already_exists_count} agents that already exist in Typesense"
            )

        return results

    @classmethod
    async def sync_agents_from_database(cls, fetch_agents_fn) -> bool:
        """
        Sync all agents from the database to Typesense.

        Args:
            fetch_agents_fn: Async function that returns a list of agents from the database

        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            # Ensure collection exists
            await cls.initialize_collections()

            # Fetch agents from database
            agents = await fetch_agents_fn()

            # Index agents in Typesense
            return await cls.index_agent_batch(agents)
        except Exception as e:
            logger.error(f"Error syncing agents to Typesense: {str(e)}")
            return False

    @classmethod
    async def check_agent_exists(cls, agent_id: str) -> bool:
        """
        Check if an agent exists in Typesense by its ID.

        Args:
            agent_id: The ID of the agent to check

        Returns:
            bool: True if the agent exists, False otherwise
        """
        client = cls.get_client()
        if not client:
            logger.warning(
                "Typesense client not initialized. Cannot check agent existence."
            )
            return False

        try:
            # Search for the agent by agent_id
            search_params = {
                "q": "*",
                "query_by": "agent_id",
                "filter_by": f"agent_id:={agent_id}",
                "per_page": 1,
            }

            results = client.collections[AGENTS_COLLECTION].documents.search(
                search_params
            )

            # If we found a hit with this agent_id, it exists
            return results.get("found", 0) > 0

        except Exception as e:
            logger.warning(f"Error checking if agent exists in Typesense: {str(e)}")
            return False

    @classmethod
    def _convert_agent_to_document(cls, agent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert agent data to a Typesense document format.

        Args:
            agent: Agent data

        Returns:
            Dict containing the formatted Typesense document
        """
        # The id field is required for Typesense and must be a string
        if "id" not in agent or not agent["id"]:
            raise ValueError("Agent must have an id field")

        # Create document with required fields
        document = {
            "agent_id": str(agent["id"]),  # Use agent_id as primary identifier field
            "name": agent.get("name", ""),
            "description": agent.get("description", ""),
        }

        # Add optional fields if they exist
        if "domains" in agent and agent["domains"]:
            # Ensure domains is a list
            if isinstance(agent["domains"], str):
                try:
                    document["domains"] = json.loads(agent["domains"])
                except json.JSONDecodeError:
                    document["domains"] = [agent["domains"]]
            else:
                document["domains"] = agent["domains"]

        if "tags" in agent and agent["tags"]:
            # Ensure tags is a list
            if isinstance(agent["tags"], str):
                try:
                    document["tags"] = json.loads(agent["tags"])
                except json.JSONDecodeError:
                    document["tags"] = [agent["tags"]]
            else:
                document["tags"] = agent["tags"]

        if "mode" in agent and agent["mode"]:
            document["mode"] = agent["mode"]
        elif "is_team" in agent and agent.get("is_team"):
            # Default mode for teams if not specified
            document["mode"] = "collaborate"

        # Convert timestamp strings to unix timestamps (int64)
        if "created_at" in agent and agent["created_at"]:
            if isinstance(agent["created_at"], str):
                try:
                    # Convert ISO format string to unix timestamp (seconds)
                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        agent["created_at"].replace("Z", "+00:00")
                    )
                    document["created_at"] = int(dt.timestamp())
                except (ValueError, TypeError):
                    # If conversion fails, use current timestamp
                    document["created_at"] = int(datetime.now().timestamp())
            elif isinstance(agent["created_at"], (int, float)):
                document["created_at"] = int(agent["created_at"])

        if "updated_at" in agent and agent["updated_at"]:
            if isinstance(agent["updated_at"], str):
                try:
                    # Convert ISO format string to unix timestamp (seconds)
                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        agent["updated_at"].replace("Z", "+00:00")
                    )
                    document["updated_at"] = int(dt.timestamp())
                except (ValueError, TypeError):
                    # If conversion fails, use current timestamp
                    document["updated_at"] = int(datetime.now().timestamp())
            elif isinstance(agent["updated_at"], (int, float)):
                document["updated_at"] = int(agent["updated_at"])

        return document


# Initialize the client when the module is imported
typesense_client = TypesenseClient.get_client()
