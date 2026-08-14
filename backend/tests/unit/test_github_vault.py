import os
import pytest
from datetime import datetime, timedelta, timezone

from engine.github.vault import TokenVault
from engine.github.models import GitHubCredential, TokenType
from engine.github.exceptions import (
    EncryptionKeyMissingError,
    DecryptionError,
    CredentialExpiredError,
    CredentialVaultError,
)

# Deterministic 32-byte test key
TEST_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
ALT_KEY = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"

@pytest.fixture
def vault():
    return TokenVault(encryption_key=TEST_KEY)

def test_1_encrypt_secret(vault):
    secret = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = vault.encrypt(secret)
    assert encrypted.startswith("v1:")
    assert secret not in encrypted

def test_2_decrypt_secret(vault):
    secret = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = vault.encrypt(secret)
    decrypted = vault.decrypt(encrypted)
    assert decrypted == secret

def test_3_roundtrip_equality(vault):
    tokens = [
        "ghp_test_token_12345",
        "gho_oauth_secret_abcde",
        "ghs_app_installation_xyz999"
    ]
    for token in tokens:
        enc = vault.encrypt(token)
        dec = vault.decrypt(enc)
        assert dec == token

def test_4_wrong_key_fails():
    vault1 = TokenVault(encryption_key=TEST_KEY)
    vault2 = TokenVault(encryption_key=ALT_KEY)

    encrypted = vault1.encrypt("ghp_secret_token_val")
    with pytest.raises(DecryptionError):
        vault2.decrypt(encrypted)

def test_5_modified_ciphertext_fails(vault):
    encrypted = vault.encrypt("ghp_secret_token_val")
    # Tamper with base64 payload
    parts = encrypted.split(":")
    tampered_b64 = parts[1][:-4] + "AAAA"
    tampered = f"{parts[0]}:{tampered_b64}"

    with pytest.raises(DecryptionError):
        vault.decrypt(tampered)

def test_6_modified_nonce_fails(vault):
    import base64
    encrypted = vault.encrypt("ghp_secret_token_val")
    parts = encrypted.split(":")
    raw = base64.b64decode(parts[1])
    # Flip bytes in nonce (first 12 bytes)
    nonce = bytearray(raw[:12])
    nonce[0] ^= 0xFF
    ciphertext = raw[12:]
    tampered_b64 = base64.b64encode(bytes(nonce) + ciphertext).decode('utf-8')
    tampered = f"{parts[0]}:{tampered_b64}"

    with pytest.raises(DecryptionError):
        vault.decrypt(tampered)

def test_7_empty_secret_behavior(vault):
    with pytest.raises(CredentialVaultError):
        vault.encrypt("")

def test_8_missing_encryption_key():
    vault_no_key = TokenVault(encryption_key=None)
    # Ensure env var is cleared for test
    if "GITHUB_TOKEN_ENCRYPTION_KEY" in os.environ:
        del os.environ["GITHUB_TOKEN_ENCRYPTION_KEY"]
    
    with pytest.raises(EncryptionKeyMissingError):
        vault_no_key.encrypt("ghp_some_secret")

def test_9_token_expiration_metadata(vault):
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=1)
    future_time = now + timedelta(hours=1)

    cred_expired = GitHubCredential(
        credential_id="cred-expired",
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        expires_at=expired_time
    )
    cred_valid = GitHubCredential(
        credential_id="cred-valid",
        token_type=TokenType.OAUTH_ACCESS_TOKEN,
        expires_at=future_time
    )

    vault.store_credential(cred_expired, "ghp_expired_token")
    vault.store_credential(cred_valid, "ghp_valid_token")

    with pytest.raises(CredentialExpiredError):
        vault.retrieve_secret("cred-expired")

    assert vault.retrieve_secret("cred-valid") == "ghp_valid_token"

def test_10_secret_not_exposed_in_repr(vault):
    raw = "ghp_super_secret_pat_999"
    cred = GitHubCredential(
        credential_id="cred-secret-repr",
        token_type=TokenType.FINE_GRAINED_PAT,
        account_login="octocat"
    )
    vault.store_credential(cred, raw)

    repr_str = repr(cred)
    str_str = str(cred)

    assert raw not in repr_str
    assert raw not in str_str
    assert "***REDACTED***" in repr_str

def test_11_different_encryptions_produce_different_nonces(vault):
    token = "ghp_static_token_text"
    enc1 = vault.encrypt(token)
    enc2 = vault.encrypt(token)

    assert enc1 != enc2  # Nonce randomness
    assert vault.decrypt(enc1) == token
    assert vault.decrypt(enc2) == token

def test_12_no_plaintext_secret_in_store(vault):
    raw = "ghp_plaintext_secret_123"
    cred = GitHubCredential(credential_id="c123")
    vault.store_credential(cred, raw)

    stored = vault.get_credential("c123")
    assert stored is not None
    assert stored.encrypted_secret is not None
    assert raw not in stored.encrypted_secret
    assert raw not in str(stored.model_dump())
