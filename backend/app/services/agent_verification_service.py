"""
Service for managing agent verification keys and DID-related operations.
"""
import json
import logging
from typing import Dict, Optional, Any, Union

from app.utils.key_encryption import KeyEncryption
from app.db.client import get_supabase_client

logger = logging.getLogger(__name__)


class AgentVerificationService:
    """Service for managing agent verification and key operations."""
    
    def __init__(self, db_client=None, master_key=None):
        """
        Initialize the agent verification service.
        
        Args:
            db_client: Database client (if None, will use the default client)
            master_key (str, optional): Master key for encryption
        """
        self.db = db_client or get_supabase_client()
        self.key_encryptor = KeyEncryption(master_key)
    
    async def store_agent_keys(self, agent_id: str, public_key: str, 
                              private_key: str, key_type: str = "rsa",
                              verification_method: str = "mlts") -> Dict[str, Any]:
        """
        Store agent verification keys with encrypted private key.
        
        Args:
            agent_id: ID of the agent
            public_key: Public key in PEM format
            private_key: Private key in PEM format
            key_type: Type of key (e.g., "rsa", "ed25519")
            verification_method: Verification method (e.g., "mlts")
            
        Returns:
            Dictionary with created verification record
        """
        try:
            # Encrypt the private key
            encryption_result = self.key_encryptor.encrypt_private_key(private_key)
            
            # Extract the encrypted key and store encryption metadata separately
            encrypted_private_key = encryption_result.pop("encrypted_key")
            encryption_metadata = encryption_result
            
            # Store in the database
            verification_data = {
                "agent_id": agent_id,
                "public_key": public_key,
                "encrypted_private_key": encrypted_private_key,
                "encryption_method": "AES-256-GCM",
                "encryption_metadata": json.dumps(encryption_metadata),
                "key_type": key_type,
                "verification_method": verification_method
            }
            
            result = await self.db.table("agent_verification").insert(verification_data).execute()
            
            if not result.data:
                raise ValueError("Failed to store agent verification data")
                
            logger.info(f"Stored verification keys for agent {agent_id}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error storing agent keys: {str(e)}")
            raise
    
    async def get_agent_verification(self, agent_id: str, include_private_key: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent verification details.
        
        Args:
            agent_id: ID of the agent
            include_private_key: Whether to decrypt and include the private key
            
        Returns:
            Agent verification details, optionally with decrypted private key
        """
        try:
            # Fetch from database
            result = await self.db.table("agent_verification").select("*").eq("agent_id", agent_id).execute()
            
            if not result.data:
                logger.warning(f"No verification data found for agent {agent_id}")
                return None
                
            verification_data = result.data[0]
            
            # Decrypt private key if requested
            if include_private_key and verification_data.get("encrypted_private_key"):
                try:
                    # Prepare decryption input
                    encrypted_data = {
                        "encrypted_key": verification_data["encrypted_private_key"],
                        **json.loads(verification_data["encryption_metadata"])
                    }
                    
                    # Decrypt the private key
                    private_key = self.key_encryptor.decrypt_private_key(encrypted_data)
                    verification_data["private_key"] = private_key
                    
                except Exception as e:
                    logger.error(f"Error decrypting private key for agent {agent_id}: {str(e)}")
                    verification_data["decryption_error"] = str(e)
            
            return verification_data
            
        except Exception as e:
            logger.error(f"Error retrieving agent verification: {str(e)}")
            return None
    
    async def verify_agent_did(self, did: str) -> Dict[str, Any]:
        """
        Verify an agent based on its DID.
        
        Args:
            did: Decentralized Identifier of the agent
            
        Returns:
            Verification result with agent details if successful
        """
        try:
            # Find agent by DID
            agent_result = await self.db.table("agents").select("*").eq("did", did).execute()
            
            if not agent_result.data:
                return {"verified": False, "reason": "Agent with DID not found"}
            
            agent = agent_result.data[0]
            
            # Get verification details
            verification = await self.get_agent_verification(agent["id"], include_private_key=False)
            
            if not verification:
                return {"verified": False, "reason": "Agent has no verification data"}
            
            # For now, just return basic verification that the agent exists with DID
            # In a real implementation, you would verify cryptographic proof here
            
            return {
                "verified": True,
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "did": did,
                "verification_method": verification["verification_method"]
            }
            
        except Exception as e:
            logger.error(f"Error verifying agent DID {did}: {str(e)}")
            return {"verified": False, "reason": str(e)}
            
    async def generate_mlts_credentials(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate new MLTS credentials for an agent.
        This is a placeholder that would interact with MLTS library.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Generated credentials
        """
        # This would be replaced with actual MLTS credential generation
        # For now, we're just providing a placeholder for the interface
        
        try:
            # Here you would:
            # 1. Generate key pair using MLTS library
            # 2. Store the keys using store_agent_keys
            # 3. Update the agent's DID
            
            return {
                "status": "not_implemented",
                "message": "MLTS credential generation not yet implemented",
                "agent_id": agent_id
            }
        
        except Exception as e:
            logger.error(f"Error generating MLTS credentials: {str(e)}")
            raise
