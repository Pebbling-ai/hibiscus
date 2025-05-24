"""Utilities for working with Decentralized Identifiers (DIDs) and MLTS protocol."""

import uuid
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# This would be replaced with actual MLTS library imports in a real implementation


class DIDManager:
    """Utility class for creating and managing DIDs."""

    DID_METHOD = "hibiscus"  # Custom DID method for this application

    @classmethod
    def generate_did(cls, public_key: Optional[str] = None) -> str:
        """
        Generate a new DID using the hibiscus method.

        Args:
            public_key: Optional public key to incorporate into the DID (PEM format string)

        Returns:
            Decentralized Identifier string
        """
        # If no public key is provided, generate a random identifier
        if not public_key:
            identifier = str(uuid.uuid4())
            return f"did:{cls.DID_METHOD}:{identifier}"

        # Process the public key to create a deterministic identifier
        try:
            # Handle PEM formatted string
            # Remove headers, footers, and whitespace
            if "-----BEGIN" in public_key:
                cleaned_key = "".join(
                    line
                    for line in public_key.strip().split("\n")
                    if not line.startswith("-----") and not line.endswith("-----")
                ).replace(" ", "")
            else:
                cleaned_key = public_key.strip().replace(" ", "")

            # Create a hash of the public key
            key_hash = hashlib.sha256(cleaned_key.encode("utf-8")).hexdigest()

            # Use the first 32 chars of the hash as the identifier
            base_id = key_hash[:32]

            # Final DID
            return f"did:{cls.DID_METHOD}:{base_id}"

        except Exception as e:
            logger.error(f"Error generating DID from public key: {str(e)}")
            # Fallback to UUID if there's any issue
            identifier = str(uuid.uuid4())
            return f"did:{cls.DID_METHOD}:{identifier}"

    @classmethod
    def parse_did(cls, did: str) -> Dict[str, str]:
        """
        Parse a DID into its components.

        Args:
            did: Decentralized Identifier string

        Returns:
            Dictionary with components (method, identifier)
        """
        try:
            parts = did.split(":")
            if len(parts) < 3 or parts[0] != "did":
                raise ValueError(f"Invalid DID format: {did}")

            return {"did": did, "method": parts[1], "identifier": parts[2]}
        except Exception as e:
            logger.error(f"Error parsing DID {did}: {str(e)}")
            raise ValueError(f"Invalid DID: {did}")

    @classmethod
    def generate_did_document(
        cls, did: str, public_key: str, verification_method: str = "mlts"
    ) -> Dict[str, Any]:
        """
        Generate a DID document for the given DID.

        Args:
            did: Decentralized Identifier
            public_key: Public key in PEM format
            verification_method: Method used for verification

        Returns:
            DID document as dictionary
        """
        verification_id = f"{did}#keys-1"

        # Create a basic DID document
        did_document = {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": did,
            "verificationMethod": [
                {
                    "id": verification_id,
                    "type": "MltsVerificationKey2023"
                    if verification_method == "mlts"
                    else "Ed25519VerificationKey2020",
                    "controller": did,
                    "publicKeyPem": public_key,
                }
            ],
            "authentication": [verification_id],
            "assertionMethod": [verification_id],
            "service": [
                {
                    "id": f"{did}#agent",
                    "type": "HibiscusAgent",
                    "serviceEndpoint": "https://pebbling.ai/agent-discovery",
                }
            ],
        }

        return did_document


class MltsProtocolHandler:
    """Handler for MLTS protocol operations."""

    def __init__(self):
        """Initialize the MLTS protocol handler."""
        # In a real implementation, this would initialize the MLTS library
        pass

    def generate_keys(self) -> Tuple[str, str]:
        """
        Generate a new key pair for MLTS authentication.

        Returns:
            Tuple of (public_key, private_key)
        """
        # This is a placeholder for actual MLTS key generation
        # In a real implementation, this would use the MLTS library

        # Mock implementation for now
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # Generate RSA key pair
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Get public key
        public_key = private_key.public_key()

        # Serialize keys to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        return public_pem, private_pem

    def verify_communication(self, message: Dict[str, Any], public_key: str) -> bool:
        """
        Verify a message using MLTS protocol.

        Args:
            message: Message to verify
            public_key: Public key to use for verification

        Returns:
            True if verification succeeds, False otherwise
        """
        # This is a placeholder for actual MLTS verification
        # In a real implementation, this would use the MLTS library

        # Mock implementation that always succeeds
        return True

    def sign_message(self, message: Dict[str, Any], private_key: str) -> Dict[str, Any]:
        """
        Sign a message using MLTS protocol.

        Args:
            message: Message to sign
            private_key: Private key to use for signing

        Returns:
            Message with signature added
        """
        # This is a placeholder for actual MLTS signing
        # In a real implementation, this would use the MLTS library

        # Mock implementation that adds a dummy signature
        signed_message = message.copy()
        signed_message["signature"] = {
            "type": "MltsSignature2023",
            "created": "2023-06-18T21:19:10Z",
            "verificationMethod": "did:example:123#keys-1",
            "value": "dummy_signature_value",
        }

        return signed_message
