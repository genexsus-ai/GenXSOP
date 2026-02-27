from app.utils.security import get_password_hash, verify_password


def test_password_hash_round_trip() -> None:
    password = "Password123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed)


def test_verify_password_rejects_invalid_hash() -> None:
    assert verify_password("Password123!", "not-a-valid-bcrypt-hash") is False
