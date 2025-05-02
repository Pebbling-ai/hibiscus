"""
Service for managing agents with DID and MLTS verification.
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional, List

from app.db.client import get_supabase_client
from app.services.agent_verification_service import AgentVerificationService
from app.utils.did_utils import DIDManager, MltsProtocolHandler

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agents with DID support."""
    
    def __init__(self, db_client=None):
        """
        Initialize the agent service.
        
        Args:
            db_client: Database client (if None, will use the default client)
        """
        self.db = db_client or get_supabase_client()
        self.verification_service = AgentVerificationService(db_client)
        self.mlts_handler = MltsProtocolHandler()
    
    async def create_agent(self, user_id: str, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent with DID and MLTS verification.
        
        Args:
            user_id: ID of the user creating the agent
            agent_data: Agent data including name, description, etc.
            
        Returns:
            Created agent with DID details
        """
        try:
            # Generate a DID for the agent
            agent_id = str(uuid.uuid4())
            did = DIDManager.generate_did(agent_id)
            
            # Generate MLTS keys
            public_key, private_key = self.mlts_handler.generate_keys()
            
            # Generate DID document
            did_document = DIDManager.generate_did_document(did, public_key, "mlts")
            
            # Prepare agent data with DID
            complete_agent_data = {
                **agent_data,
                "id": agent_id,
                "user_id": user_id,
                "did": did,
                "did_document": json.dumps(did_document)
            }
            
            # Ensure required fields exist
            required_fields = ["name", "description", "version", "author_name"]
            for field in required_fields:
                if field not in complete_agent_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create the agent in the database
            agent_result = await self.db.table("agents").insert(complete_agent_data).execute()
            
            if not agent_result.data:
                raise ValueError("Failed to create agent")
            
            created_agent = agent_result.data[0]
            
            # Store verification keys
            await self.verification_service.store_agent_keys(
                agent_id, 
                public_key, 
                private_key, 
                "rsa",  # Key type
                "mlts"  # Verification method
            )
            
            logger.info(f"Created agent {created_agent['name']} with DID {did}")
            
            return created_agent
        
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            raise
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details by ID.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent details or None if not found
        """
        try:
            result = await self.db.table("agents").select("*").eq("id", agent_id).execute()
            
            if not result.data:
                return None
                
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {str(e)}")
            return None
    
    async def get_agent_by_did(self, did: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details by DID.
        
        Args:
            did: Decentralized Identifier
            
        Returns:
            Agent details or None if not found
        """
        try:
            result = await self.db.table("agents").select("*").eq("did", did).execute()
            
            if not result.data:
                return None
                
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error getting agent by DID {did}: {str(e)}")
            return None
    
    async def verify_agent_did(self, did: str) -> Dict[str, Any]:
        """
        Verify an agent's DID.
        
        Args:
            did: Decentralized Identifier
            
        Returns:
            Verification result
        """
        return await self.verification_service.verify_agent_did(did)
    
    async def prepare_secure_message(self, source_agent_id: str, target_did: str, 
                                    message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a secure message for agent-to-agent communication using MLTS.
        
        Args:
            source_agent_id: ID of the sending agent
            target_did: DID of the target agent
            message: Message content
            
        Returns:
            Secure message with MLTS signature
        """
        try:
            # Get the source agent verification with private key
            verification = await self.verification_service.get_agent_verification(
                source_agent_id, include_private_key=True
            )
            
            if not verification or "private_key" not in verification:
                raise ValueError("Could not get source agent's private key for signing")
            
            # Get the source agent details
            source_agent = await self.get_agent(source_agent_id)
            
            if not source_agent:
                raise ValueError(f"Source agent {source_agent_id} not found")
            
            # Prepare the message wrapper
            message_wrapper = {
                "from": source_agent["did"],
                "to": target_did,
                "timestamp": "TIMESTAMP",  # Would be actual timestamp in real implementation
                "payload": message
            }
            
            # Sign the message using MLTS
            signed_message = self.mlts_handler.sign_message(
                message_wrapper, verification["private_key"]
            )
            
            return signed_message
            
        except Exception as e:
            logger.error(f"Error preparing secure message: {str(e)}")
            raise
    
    async def verify_secure_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a secure message using MLTS.
        
        Args:
            message: Signed message
            
        Returns:
            Verification result
        """
        try:
            # Extract sender DID
            from_did = message.get("from")
            if not from_did:
                return {"verified": False, "reason": "Message missing sender DID"}
            
            # Get the sender agent
            sender_agent = await self.get_agent_by_did(from_did)
            if not sender_agent:
                return {"verified": False, "reason": "Sender agent not found"}
            
            # Get the sender's verification details
            verification = await self.verification_service.get_agent_verification(
                sender_agent["id"], include_private_key=False
            )
            
            if not verification:
                return {"verified": False, "reason": "Sender has no verification data"}
            
            # Verify the message signature using MLTS
            is_verified = self.mlts_handler.verify_communication(
                message, verification["public_key"]
            )
            
            if is_verified:
                return {
                    "verified": True,
                    "sender": {
                        "id": sender_agent["id"],
                        "name": sender_agent["name"],
                        "did": from_did
                    },
                    "payload": message.get("payload", {})
                }
            else:
                return {"verified": False, "reason": "MLTS signature verification failed"}
            
        except Exception as e:
            logger.error(f"Error verifying secure message: {str(e)}")
            return {"verified": False, "reason": str(e)}
