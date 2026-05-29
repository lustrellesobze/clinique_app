"""Vérification des jetons Google (connexion accueil uniquement)."""
from __future__ import annotations

import httpx

from app.config import settings


class GoogleAuthError(Exception):
    """Jeton Google invalide ou non autorisé."""


def google_accueil_auth_enabled() -> bool:
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    if not client_id:
        return False
    return bool(settings.GOOGLE_ACCUEIL_AUTH_ENABLED)


def verify_google_id_token(id_token: str) -> dict[str, str]:
    """
    Valide un ID token émis par Google Identity Services.
    https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
    """
    token = (id_token or "").strip()
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    if not client_id:
        raise GoogleAuthError("Connexion Google non configurée sur le serveur.")
    if not token:
        raise GoogleAuthError("Jeton Google manquant.")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
            )
    except httpx.HTTPError as e:
        raise GoogleAuthError("Impossible de contacter Google pour vérifier le jeton.") from e

    if resp.status_code != 200:
        raise GoogleAuthError("Jeton Google invalide ou expiré.")

    data = resp.json()
    if not isinstance(data, dict):
        raise GoogleAuthError("Réponse Google invalide.")

    aud = data.get("aud") or data.get("azp")
    if aud != client_id:
        raise GoogleAuthError("Jeton Google émis pour une autre application.")

    email = (data.get("email") or "").strip().lower()
    if not email:
        raise GoogleAuthError("Adresse e-mail absente du compte Google.")

    verified = data.get("email_verified")
    if str(verified).lower() not in ("true", "1"):
        raise GoogleAuthError("Adresse e-mail Google non vérifiée.")

    return {
        "email": email,
        "given_name": str(data.get("given_name") or ""),
        "family_name": str(data.get("family_name") or ""),
        "sub": str(data.get("sub") or ""),
    }
