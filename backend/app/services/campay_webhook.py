"""
Webhook Campay : même schéma métier que GET /api/transaction/{reference}/.

Références SDK / docs publiques :
- Transaction : reference, status (PENDING | SUCCESSFUL | FAILED), amount, currency,
  operator, code, operator_reference, description, external_reference.
- Authentification callback : JWT HS256 signé avec la clé webhook (voir SDK Go CamPay).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.config import settings
from app.models.invoice import Facture, FactureStatut
from app.models.patient import Patient
from app.models.payment import Paiement, StatutPaiement
from app.services.audit_service import log_audit
from app.services.loyalty_service import LoyaltyService
from app.services.notification_service import NotificationService


Outcome = Literal["confirmed", "failed", "pending", "noop"]


@dataclass
class CampayTransactionNotify:
    """Notification normalisée (Campay + format legacy interne)."""

    lookup_refs: list[str]
    raw_status: str
    normalized: Literal["SUCCESS", "FAILED", "PENDING"]
    amount_reported: Decimal | None
    operator_message: str | None


def normalize_campay_status(raw: str | None) -> Literal["SUCCESS", "FAILED", "PENDING"]:
    s = (raw or "").strip().upper()
    if s in ("SUCCESSFUL", "SUCCESS", "COMPLETED", "COMPLETE", "PAID"):
        return "SUCCESS"
    if s in ("FAILED", "FAILURE", "CANCELLED", "CANCELED", "REJECTED", "DECLINED"):
        return "FAILED"
    return "PENDING"


def _dig(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _flatten_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    inner = out.get("data")
    if isinstance(inner, dict):
        merged = {**out, **inner}
        merged.pop("data", None)
        out = merged
    txn = out.get("transaction")
    if isinstance(txn, dict):
        merged = {**out, **txn}
        merged.pop("transaction", None)
        out = merged
    return out


def parse_campay_transaction_notification(payload: dict[str, Any]) -> CampayTransactionNotify:
    """
    Accepte :
    - JSON Campay (transaction / webhook) : reference, external_reference, status, …
    - Format legacy démo : reference_transaction, status (SUCCESS / FAILED / PENDING), amount optionnel
    """
    p = _flatten_payload(dict(payload))

    # Legacy (tests internes)
    legacy_ref = _dig(p, "reference_transaction")
    if legacy_ref:
        refs = [str(legacy_ref)]
        raw_st = str(_dig(p, "status") or "")
        norm = normalize_campay_status(raw_st)
        amt_raw = _dig(p, "amount")
        op_msg = _dig(p, "operator_message")
        if isinstance(op_msg, str):
            msg = op_msg
        else:
            msg = None
        amt = _decimal_optional(amt_raw)
        return CampayTransactionNotify(
            lookup_refs=refs,
            raw_status=raw_st,
            normalized=norm,
            amount_reported=amt,
            operator_message=msg,
        )

    refs: list[str] = []
    for key in ("reference", "external_reference", "externalReference"):
        v = _dig(p, key)
        if v is not None and str(v).strip():
            sref = str(v).strip()
            if sref not in refs:
                refs.append(sref)

    raw_st = str(_dig(p, "status") or "")
    norm = normalize_campay_status(raw_st)

    parts: list[str] = []
    for label, key in (
        ("operator", "operator"),
        ("code", "code"),
        ("operator_reference", "operator_reference"),
        ("operator_reference", "operatorReference"),
        ("description", "description"),
        ("currency", "currency"),
    ):
        val = _dig(p, key)
        if val is not None and str(val).strip():
            parts.append(f"{label}={val}")

    amt = _decimal_optional(_dig(p, "amount"))

    return CampayTransactionNotify(
        lookup_refs=refs,
        raw_status=raw_st,
        normalized=norm,
        amount_reported=amt,
        operator_message="; ".join(parts) if parts else None,
    )


def _decimal_optional(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def find_payment_for_campay_refs(
    db: Session, refs: list[str]
) -> tuple[Paiement | None, Facture | None]:
    for ref in refs:
        if not ref:
            continue
        payment = db.scalars(
            select(Paiement).where(Paiement.reference_transaction == ref)
        ).first()
        if payment:
            facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
            return payment, facture
    return None, None


def apply_campay_notification_to_payment(
    db: Session,
    *,
    payment: Paiement,
    facture: Facture,
    notify: CampayTransactionNotify,
    append_comment: bool = True,
) -> Outcome:
    """Met à jour paiement + facture selon la notification. Pas de commit ici."""

    total = Decimal(str(facture.montant_total or 0))
    regle = Decimal(str(facture.montant_regle or 0))
    pay_amt = Decimal(str(payment.montant or 0))

    if append_comment:
        detail_parts = [f"Campay status={notify.raw_status}"]
        if notify.operator_message:
            detail_parts.append(str(notify.operator_message))
        suffix = "\n" + " | ".join(detail_parts)
        payment.commentaire = f"{payment.commentaire or ''}{suffix}".strip()

    if notify.normalized == "SUCCESS":
        if payment.statut != StatutPaiement.confirme:
            payment.statut = StatutPaiement.confirme
            regle = regle + pay_amt
            facture.montant_regle = float(regle)
            if regle >= total:
                facture.statut = FactureStatut.payee
            elif regle > 0:
                facture.statut = FactureStatut.partielle
            else:
                facture.statut = FactureStatut.en_attente
            return "confirmed"
        return "noop"

    if notify.normalized == "FAILED":
        if payment.statut == StatutPaiement.en_attente:
            payment.statut = StatutPaiement.annule
            return "failed"
        return "noop"

    # PENDING ou inconnu → laisser en attente côté paiement
    if payment.statut == StatutPaiement.en_attente:
        payment.statut = StatutPaiement.en_attente
        return "pending"
    return "noop"


def finalize_confirmed_mobile_payment_effects(db: Session, payment: Paiement, facture: Facture) -> None:
    """Audit, fidélité, notification interne (best effort)."""
    try:
        log_audit(
            db,
            user_id=payment.caissier_id,
            action="mobile_payment_webhook_confirmed",
            entity_type="paiement",
            entity_id=payment.id,
            details={"facture_id": facture.id, "montant": float(payment.montant)},
        )
        patient = db.scalars(select(Patient).where(Patient.id == facture.patient_id)).first()
        if patient:
            LoyaltyService.add_points_for_payment(db, patient.id, Decimal(str(payment.montant)))
        if payment.caissier_id:
            NotificationService.create_notification(
                db=db,
                user_id=payment.caissier_id,
                type_notification="paiement",
                titre="Paiement Mobile Money confirmé",
                message=(
                    f"Paiement {float(payment.montant):,.0f} FCFA confirmé "
                    f"(ref. {payment.reference_transaction or '-'})."
                ),
            )
    except Exception:
        pass


def _jwt_header_candidates(request: Request) -> list[str]:
    out: list[str] = []
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        out.append(auth[7:].strip())
    for key in (
        "x-campay-signature",
        "campay-signature",
        "x-webhook-signature",
        "signature",
        "x-signature",
    ):
        v = request.headers.get(key)
        if v:
            out.append(v.strip())
    return [x for x in out if x.startswith("eyJ")]


def verify_campay_webhook_request(
    request: Request,
    *,
    payload_dict: dict[str, Any],
    raw_body: bytes,
    body_was_verified_jwt: bool,
) -> None:
    """
    - JWT HS256 (clé = CAMPAY_WEBHOOK_SECRET) dans Authorization: Bearer … ou en-têtes dédiés.
    - Sinon comparaison simple : x-webhook-token (ou webhook-token) == secret ou jeton dev.
    """
    secret = (settings.CAMPAY_WEBHOOK_SECRET or "").strip()
    legacy_plain = secret or "dev-mobile-webhook-token"

    if request.headers.get("x-webhook-token") == legacy_plain:
        return
    if request.headers.get("webhook-token") == legacy_plain:
        return

    if body_was_verified_jwt:
        return

    sig_field = payload_dict.get("signature")
    if isinstance(sig_field, str) and sig_field.startswith("eyJ") and secret:
        try:
            jwt.decode(sig_field, secret, algorithms=["HS256"])
            return
        except JWTError:
            pass

    if secret:
        for tok in _jwt_header_candidates(request):
            try:
                jwt.decode(tok, secret, algorithms=["HS256"])
                return
            except JWTError:
                continue

    raise HTTPException(status_code=401, detail="Webhook non authentifié")


def parse_webhook_raw_body(raw_body: bytes) -> tuple[dict[str, Any], bool]:
    """
    Retourne (payload_dict, body_was_verified_jwt).
    - JSON objet Campay ou legacy
    - corps réduit à un seul JWT signé (vérif faite ensuite dans verify_*)
    """
    text = raw_body.decode("utf-8", errors="ignore").strip()
    if not text:
        return {}, False

    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return {}, False
        return (obj if isinstance(obj, dict) else {}), False

    if text.startswith("eyJ"):
        secret = (settings.CAMPAY_WEBHOOK_SECRET or "").strip()
        if not secret:
            return {}, False
        try:
            claims = jwt.decode(text, secret, algorithms=["HS256"])
        except JWTError as e:
            raise HTTPException(status_code=401, detail="JWT webhook invalide") from e
        return (claims if isinstance(claims, dict) else {}), True

    return {}, False
