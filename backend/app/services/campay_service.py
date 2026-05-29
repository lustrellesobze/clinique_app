from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from app.config import settings


class CampayError(Exception):
    """Erreur fonctionnelle lors d'un appel Campay."""


@dataclass
class CampayCollectionResult:
    reference: str
    status: str
    raw: dict[str, Any]
    ussd_code: str | None = None
    operator: str | None = None


@dataclass
class CampayPaymentLinkResult:
    reference: str
    link: str
    status: str
    raw: dict[str, Any]


def campay_is_enabled() -> bool:
    return bool(
        (settings.CAMPAY_APP_USERNAME and settings.CAMPAY_APP_PASSWORD)
        or (settings.CAMPAY_PERMANENT_ACCESS_TOKEN or "").strip()
    )


def _is_enabled() -> bool:
    return campay_is_enabled()


def normalize_cameroon_phone(phone: str) -> str:
    """Format attendu par Campay : 2376XXXXXXXX (sans espaces)."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        raise CampayError("Numéro de téléphone invalide.")
    if digits.startswith("237") and len(digits) >= 12:
        return digits[:12]
    if digits.startswith("0") and len(digits) >= 10:
        return "237" + digits[1:10]
    if len(digits) == 9:
        return "237" + digits
    if len(digits) > 9:
        return "237" + digits[-9:]
    raise CampayError("Numéro de téléphone invalide (9 chiffres après 237).")


def _auth_headers() -> dict[str, str]:
    token = (settings.CAMPAY_PERMANENT_ACCESS_TOKEN or "").strip()
    if token:
        return {"Authorization": f"Token {token}"}
    return {}


def _get_access_token(client: httpx.Client) -> str:
    if not _is_enabled():
        raise CampayError("Campay non configuré (identifiants manquants).")

    permanent = (settings.CAMPAY_PERMANENT_ACCESS_TOKEN or "").strip()
    if permanent:
        return permanent

    resp = client.post(
        f"{settings.CAMPAY_BASE_URL.rstrip('/')}/api/token/",
        json={
            "username": settings.CAMPAY_APP_USERNAME,
            "password": settings.CAMPAY_APP_PASSWORD,
        },
        headers={"Accept": "application/json"},
    )
    if resp.status_code >= 400:
        raise CampayError(f"Authentification Campay échouée ({resp.status_code}).")

    data = resp.json()
    token = data.get("token") or data.get("access") or data.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise CampayError("Jeton Campay invalide dans la réponse token.")
    return token.strip()


def initiate_collection(
    *,
    amount: Decimal,
    phone_number: str,
    provider: str,
    external_reference: str,
    description: str,
) -> CampayCollectionResult:
    if provider not in {"orange_money", "mtn_momo"}:
        raise CampayError("Provider Mobile Money non supporté.")

    with httpx.Client(timeout=20.0) as client:
        access_token = _get_access_token(client)
        phone = normalize_cameroon_phone(phone_number)
        payload = {
            "amount": str(int(amount)),
            "currency": "XAF",
            "from": phone,
            "description": description[:255],
            "external_reference": external_reference[:64],
        }
        resp = client.post(
            f"{settings.CAMPAY_BASE_URL.rstrip('/')}/api/collect/",
            json=payload,
            headers={
                "Authorization": f"Token {access_token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code >= 400:
            detail = resp.text[:500] if resp.text else ""
            raise CampayError(
                f"Initiation Campay échouée ({resp.status_code})"
                f"{': ' + detail if detail else ''}"
            )

        data = resp.json()
        reference = (
            data.get("reference")
            or data.get("external_reference")
            or data.get("transaction_reference")
            or external_reference
        )
        status = (data.get("status") or "PENDING").upper()
        ussd = data.get("ussd_code")
        operator = data.get("operator")
        return CampayCollectionResult(
            reference=str(reference),
            status=status,
            raw=data,
            ussd_code=str(ussd).strip() if ussd else None,
            operator=str(operator).strip() if operator else None,
        )


def create_payment_link(
    *,
    amount: Decimal,
    phone_number: str,
    external_reference: str,
    description: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    redirect_url: str | None = None,
    failure_redirect_url: str | None = None,
    payment_options: str = "MOMO",
) -> CampayPaymentLinkResult:
    """Lien Campay scannable (QR) — page de paiement Mobile Money."""
    base = settings.CAMPAY_BASE_URL.rstrip("/")
    ok_redirect = (redirect_url or settings.CAMPAY_PAYMENT_REDIRECT_URL or f"{base}/").strip()
    fail_redirect = (
        failure_redirect_url
        or settings.CAMPAY_PAYMENT_FAILURE_REDIRECT_URL
        or ok_redirect
    ).strip()

    with httpx.Client(timeout=20.0) as client:
        access_token = _get_access_token(client)
        phone = normalize_cameroon_phone(phone_number)
        payload = {
            "amount": str(int(amount)),
            "currency": "XAF",
            "description": description[:255],
            "external_reference": external_reference[:64],
            "from": phone,
            "first_name": (first_name or "Client")[:80],
            "last_name": (last_name or "Clinique")[:80],
            "email": (email or "")[:120],
            "redirect_url": ok_redirect,
            "failure_redirect_url": fail_redirect,
            "payment_options": payment_options,
        }
        resp = client.post(
            f"{base}/api/get_payment_link/",
            json=payload,
            headers={
                "Authorization": f"Token {access_token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code >= 400:
            detail = resp.text[:500] if resp.text else ""
            raise CampayError(
                f"Lien de paiement Campay échoué ({resp.status_code})"
                f"{': ' + detail if detail else ''}"
            )

        data = resp.json()
        link = data.get("link") or data.get("payment_link") or data.get("url")
        if not isinstance(link, str) or not link.strip():
            raise CampayError("Campay n'a pas renvoyé de lien de paiement.")
        reference = (
            data.get("reference")
            or data.get("external_reference")
            or external_reference
        )
        status = (data.get("status") or "SUCCESSFUL").upper()
        return CampayPaymentLinkResult(
            reference=str(reference),
            link=link.strip(),
            status=status,
            raw=data,
        )


def get_transaction_status(reference: str) -> dict[str, Any]:
    """GET /api/transaction/{reference}/ — même schéma que le webhook Campay."""
    ref = (reference or "").strip()
    if not ref:
        raise CampayError("Référence transaction vide.")

    with httpx.Client(timeout=20.0) as client:
        access_token = _get_access_token(client)
        resp = client.get(
            f"{settings.CAMPAY_BASE_URL.rstrip('/')}/api/transaction/{ref}/",
            headers={
                "Authorization": f"Token {access_token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code >= 400:
            raise CampayError(f"Lecture statut Campay échouée ({resp.status_code}).")
        data = resp.json()
        if not isinstance(data, dict):
            raise CampayError("Réponse Campay invalide.")
        return data
