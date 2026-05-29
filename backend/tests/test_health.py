"""Santé API + base de données."""


def test_root(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"]
    assert body["health"] == "/health"


def test_health_database_connected(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "database": "connected"}
