from app.core.security import hash_password, verify_password


LEGACY_HASH = '$pbkdf2-sha256$29000$8Z5zTkkJoRRCaA3B2HuPMQ$gDphjmjXM2ob94EpKAuccOnV5LxJThZwhpFQV6Qqgto'


def test_hash_password_uses_pbkdf2_format_and_verifies() -> None:
    hashed = hash_password('ChangeMe123!')

    assert hashed.startswith('$pbkdf2-sha256$29000$')
    assert verify_password('ChangeMe123!', hashed) is True
    assert verify_password('wrong-password', hashed) is False


def test_verify_password_supports_legacy_passlib_pbkdf2_hash() -> None:
    assert verify_password('ChangeMe123!', LEGACY_HASH) is True
    assert verify_password('wrong-password', LEGACY_HASH) is False