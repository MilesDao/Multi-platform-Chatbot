from app.security import (
    create_access_token,
    decode_access_token,
    decrypt_token,
    encrypt_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_the_password_but_verifies():
    hashed = hash_password("s3cret-pass")

    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed) is True
    assert verify_password("wrong-pass", hashed) is False


def test_access_token_round_trips_the_subject():
    token = create_access_token("42")

    assert decode_access_token(token) == "42"


def test_expired_access_token_decodes_to_none():
    token = create_access_token("42", expires_minutes=-1)

    assert decode_access_token(token) is None


def test_tampered_access_token_decodes_to_none():
    assert decode_access_token("not-a-jwt") is None


def test_page_access_token_encryption_round_trips():
    ciphertext = encrypt_token("EAAG-super-secret-page-token")

    assert ciphertext != "EAAG-super-secret-page-token"
    assert decrypt_token(ciphertext) == "EAAG-super-secret-page-token"


def test_decrypting_empty_string_returns_empty_string():
    assert decrypt_token("") == ""
