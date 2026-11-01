import pytest
from cryptography.fernet import Fernet
from backend.app.core.crypto import (
    FernetManager,
    generate_fernet_key,
    CryptoError,
    DecryptionError,
    MissingKeyError,
    get_fernet_manager,
)


def test_generate_fernet_key():
    key = generate_fernet_key()
    assert isinstance(key, str)
    # Valid Fernet key can initialize Fernet directly
    f = Fernet(key.encode("utf-8"))
    assert f is not None


def test_encryption_and_decryption_roundtrip():
    key = generate_fernet_key()
    mgr = FernetManager(primary_key=key)
    assert mgr.is_configured is True

    plaintext = "sk-ant-api03-test-secret-token"
    ciphertext = mgr.encrypt(plaintext)
    assert ciphertext != plaintext
    assert isinstance(ciphertext, str)

    decrypted = mgr.decrypt(ciphertext)
    assert decrypted == plaintext


def test_corrupted_ciphertext_raises_decryption_error():
    key = generate_fernet_key()
    mgr = FernetManager(primary_key=key)

    ciphertext = mgr.encrypt("my-secret-key")
    # Corrupt the payload
    corrupted = ciphertext[:-4] + "AAAA"

    with pytest.raises(DecryptionError):
        mgr.decrypt(corrupted)


def test_zero_downtime_key_rotation():
    old_key = generate_fernet_key()
    new_key = generate_fernet_key()

    # Step 1: Encrypted in the past with old_key
    old_mgr = FernetManager(primary_key=old_key)
    ciphertext_v1 = old_mgr.encrypt("candidate-byo-gemini-key-12345")

    # Step 2: Service configured during rotation with new_key and old_key
    rotating_mgr = FernetManager(primary_key=new_key, old_key=old_key)
    # Can decrypt seamlessly
    assert rotating_mgr.decrypt(ciphertext_v1) == "candidate-byo-gemini-key-12345"

    # Rotate ciphertext to re-encrypt with new primary key
    rotated_ciphertext, was_rotated = rotating_mgr.rotate(ciphertext_v1)
    assert was_rotated is True
    assert rotated_ciphertext != ciphertext_v1

    # Step 3: Service after rotation has ONLY new_key
    post_rotation_mgr = FernetManager(primary_key=new_key)
    assert post_rotation_mgr.decrypt(rotated_ciphertext) == "candidate-byo-gemini-key-12345"

    # Old manager can no longer decrypt the newly rotated ciphertext
    with pytest.raises(DecryptionError):
        old_mgr.decrypt(rotated_ciphertext)


def test_unconfigured_manager_raises_missing_key():
    mgr = FernetManager()
    assert mgr.is_configured is False

    with pytest.raises(MissingKeyError):
        mgr.encrypt("data")

    with pytest.raises(MissingKeyError):
        mgr.decrypt("some-ciphertext")


def test_invalid_key_format_raises_crypto_error():
    with pytest.raises(CryptoError):
        FernetManager(primary_key="not-a-valid-base64-key")


def test_get_fernet_manager_singleton():
    mgr = get_fernet_manager()
    assert isinstance(mgr, FernetManager)
