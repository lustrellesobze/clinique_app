"""Service Google (unitaire, sans appel réseau réel)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.google_auth_service import (
    GoogleAuthError,
    google_accueil_auth_enabled,
    verify_google_id_token,
)


def test_google_accueil_disabled_without_client_id(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr("app.config.settings.GOOGLE_ACCUEIL_AUTH_ENABLED", True)
    assert google_accueil_auth_enabled() is False


def test_verify_google_id_token_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        "app.config.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": "invalid_token"}

    with patch("app.services.google_auth_service.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(GoogleAuthError, match="invalide"):
            verify_google_id_token("bad-token")
