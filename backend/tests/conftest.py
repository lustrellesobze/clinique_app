"""
Fixtures pytest — utilisées en local et en CI (GitHub Actions + MySQL).

En CI, DATABASE_URL et SECRET_KEY sont définis dans le workflow avant pytest.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

# Variables minimales si lancement pytest sans .env
os.environ.setdefault(
    "SECRET_KEY",
    "ci-test-secret-key-at-least-32-characters-long!!",
)
os.environ.setdefault("GOOGLE_CLIENT_ID", "")
os.environ.setdefault("GOOGLE_ACCUEIL_AUTH_ENABLED", "false")

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

TEST_ADMIN_EMAIL = "admin-ci@test.local"
TEST_PASSWORD = "testpass123"


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """Client HTTP sans override DB (health, routes publiques)."""
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    """Client avec session DB injectée (routes authentifiées / métier)."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_app:
        yield test_app
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db) -> User:
    row = db.scalars(select(User).where(User.email == TEST_ADMIN_EMAIL)).first()
    if row:
        return row
    user = User(
        email=TEST_ADMIN_EMAIL,
        nom="Admin",
        prenom="CI",
        mot_de_passe_hash=hash_password(TEST_PASSWORD),
        role=UserRole.admin,
        est_actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
