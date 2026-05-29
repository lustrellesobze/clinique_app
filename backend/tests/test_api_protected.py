"""Routes protégées par JWT."""


def test_patients_search_requires_authentication(client):
    response = client.get("/api/patients", params={"q": "P-2025"})
    assert response.status_code == 401


def test_patients_search_with_valid_token(client, auth_headers):
    response = client.get("/api/patients", params={"q": "zzz-inexistant"}, headers=auth_headers)
    # 200 avec liste vide ou 404 selon implémentation — pas 401/403
    assert response.status_code == 200
    assert isinstance(response.json(), list)
