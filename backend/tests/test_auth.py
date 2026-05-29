"""Authentification JWT (login, refresh, Google config)."""

from tests.conftest import TEST_ADMIN_EMAIL, TEST_PASSWORD


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_success_returns_tokens(client, admin_user):
    response = client.post(
        "/api/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == TEST_ADMIN_EMAIL
    assert data["user"]["role"] == "admin"


def test_refresh_token(client, admin_user):
    login = client.post(
        "/api/auth/login",
        data={"username": TEST_ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    refresh_token = login.json()["refresh_token"]
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_google_config_disabled_by_default(test_client):
    response = test_client.get("/api/auth/google/config")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["client_id"] == ""


def test_google_login_disabled_returns_503(test_client):
    response = test_client.post(
        "/api/auth/google",
        json={"credential": "fake-token"},
    )
    assert response.status_code == 503
