"""Fonctions de sécurité (hash mot de passe)."""

from app.core.security import hash_password, verify_password


def test_hash_and_verify_password():
    plain = "demo123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_rejects_empty_hash():
    assert verify_password("demo123", "") is False
