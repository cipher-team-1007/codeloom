import os
import base64
from datetime import datetime
from typing import Optional, Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .models import GitHubCredential
from .exceptions import (
    EncryptionKeyMissingError,
    DecryptionError,
    CredentialExpiredError,
    CredentialVaultError,
)

class TokenVault:
    """
    Secure Token Vault providing AES-256-GCM encryption/decryption 
    and storage primitives for GitHub access tokens and credentials.
    """

    VERSION_PREFIX = "v1"

    def __init__(self, encryption_key: Optional[str] = None):
        raw_key = encryption_key or os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY")
        self._key_bytes = TokenVault._derive_key_bytes(raw_key) if raw_key else None
        # Storage dictionary for testing & session management
        self._credentials_store: Dict[str, GitHubCredential] = {}

    @staticmethod
    def _derive_key_bytes(key_input: str) -> bytes:
        """Derives a 32-byte binary key from hex string or raw key input."""
        if not key_input:
            raise EncryptionKeyMissingError("Encryption key cannot be empty.")
        
        # Try hex decode if 64 characters long
        if len(key_input) == 64:
            try:
                return bytes.fromhex(key_input)
            except ValueError:
                pass
        
        # Base64 decode attempt if valid
        try:
            decoded = base64.b64decode(key_input)
            if len(decoded) == 32:
                return decoded
        except Exception:
            pass

        key_bytes = key_input.encode('utf-8')
        if len(key_bytes) == 32:
            return key_bytes
        
        # Pad or hash to 32 bytes using SHA-256 for uniform key length
        import hashlib
        return hashlib.sha256(key_bytes).digest()

    def encrypt(self, secret: str) -> str:
        """
        Encrypts a raw token string using AES-256-GCM.
        Returns a formatted base64 string: 'v1:<base64_payload>'
        """
        if not secret:
            raise CredentialVaultError("Cannot encrypt empty secret.")
        if not self._key_bytes:
            raise EncryptionKeyMissingError("Encryption key not configured. Set GITHUB_TOKEN_ENCRYPTION_KEY.")

        try:
            aesgcm = AESGCM(self._key_bytes)
            nonce = os.urandom(12)  # 96-bit unique IV
            ciphertext = aesgcm.encrypt(nonce, secret.encode('utf-8'), None)
            payload_bytes = nonce + ciphertext
            b64_payload = base64.b64encode(payload_bytes).decode('utf-8')
            return f"{self.VERSION_PREFIX}:{b64_payload}"
        except Exception as e:
            if isinstance(e, CredentialVaultError):
                raise
            raise CredentialVaultError(f"Encryption operation failed: {e}") from e

    def decrypt(self, encrypted_payload: str) -> str:
        """
        Decrypts an AES-256-GCM payload formatted as 'v1:<base64_payload>'.
        Raises DecryptionError on bad payload or invalid key.
        """
        if not encrypted_payload:
            raise DecryptionError("Encrypted payload is empty.")
        if not self._key_bytes:
            raise EncryptionKeyMissingError("Encryption key not configured. Set GITHUB_TOKEN_ENCRYPTION_KEY.")

        parts = encrypted_payload.split(":", 1)
        if len(parts) != 2 or parts[0] != self.VERSION_PREFIX:
            raise DecryptionError("Invalid payload version or structure.")

        try:
            payload_bytes = base64.b64decode(parts[1])
            if len(payload_bytes) < 28: # 12 bytes nonce + 16 bytes tag
                raise DecryptionError("Payload too short.")
            
            nonce = payload_bytes[:12]
            ciphertext = payload_bytes[12:]
            
            aesgcm = AESGCM(self._key_bytes)
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            if isinstance(e, (EncryptionKeyMissingError, DecryptionError)):
                raise
            raise DecryptionError("Decryption failed. Invalid ciphertext or wrong key.") from e

    def store_credential(self, credential: GitHubCredential, raw_secret: str) -> GitHubCredential:
        """
        Encrypts the raw secret and stores the credential in vault memory.
        """
        encrypted_token = self.encrypt(raw_secret)
        credential.encrypted_secret = encrypted_token
        self._credentials_store[credential.credential_id] = credential
        return credential

    def get_credential(self, credential_id: str) -> Optional[GitHubCredential]:
        """Retrieves credential metadata without decrypting secret."""
        return self._credentials_store.get(credential_id)

    def retrieve_secret(self, credential_id: str) -> str:
        """
        Retrieves and decrypts the secret token for a credential ID.
        Checks expiration.
        """
        cred = self.get_credential(credential_id)
        if not cred:
            raise CredentialVaultError(f"Credential '{credential_id}' not found in vault.")
        if cred.is_expired():
            raise CredentialExpiredError(f"Credential '{credential_id}' has expired.")
        if not cred.encrypted_secret:
            raise CredentialVaultError(f"Credential '{credential_id}' has no encrypted payload.")
        
        return self.decrypt(cred.encrypted_secret)

    def delete_credential(self, credential_id: str) -> bool:
        """Deletes a credential from the vault store."""
        if credential_id in self._credentials_store:
            del self._credentials_store[credential_id]
            return True
        return False

    def __repr__(self) -> str:
        status = "CONFIGURED" if self._key_bytes else "KEY_MISSING"
        return f"<TokenVault status={status} stored_count={len(self._credentials_store)}>"
