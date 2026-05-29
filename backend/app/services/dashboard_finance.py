"""Utilitaires financiers pour le tableau de bord admin."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.models.invoice import FactureStatut

SERVICE_LABELS: dict[str, str] = {
    "consultation": "Consultation",
    "pharmacie": "Pharmacie",
    "laboratoire": "Laboratoire",
    "imagerie": "Imagerie",
    "hospitalisation": "Hospitalisation",
    "autre": "Autre",
}

PERIODE_LABELS: dict[str, str] = {
    "journalier": "Journalier",
    "hebdomadaire": "Hebdomadaire",
    "mensuel": "Mensuel",
    "trimestriel": "Trimestriel",
}


def service_from_numero(numero: str) -> str:
    n = (numero or "").upper()
    if n.startswith("FACT-CONS-"):
        return "consultation"
    if n.startswith("FACT-LABO-"):
        return "laboratoire"
    if n.startswith("FACT-IMG-"):
        return "imagerie"
    if n.startswith("FACT-HOSPIT-"):
        return "hospitalisation"
    if n.startswith("FACT-PHAR-"):
        return "pharmacie"
    return "autre"


def service_label(service: str) -> str:
    return SERVICE_LABELS.get(service, service.capitalize())


def to_decimal(v: object, default: str = "0") -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal(default)
    return Decimal(str(v))


def period_bounds(periode: str, date_ref: date) -> tuple[date, date]:
    p = (periode or "").lower()
    if p == "journalier":
        return date_ref, date_ref
    if p == "hebdomadaire":
        start = date_ref - timedelta(days=date_ref.weekday())
        return start, start + timedelta(days=6)
    if p == "mensuel":
        start = date_ref.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        return start, end
    if p == "trimestriel":
        q = (date_ref.month - 1) // 3
        start_month = q * 3 + 1
        start = date(date_ref.year, start_month, 1)
        end_month = start_month + 2
        if end_month == 12:
            end = date(date_ref.year, 12, 31)
        else:
            end = date(date_ref.year, end_month + 1, 1) - timedelta(days=1)
        return start, end
    raise HTTPException(
        status_code=400,
        detail="Période invalide (journalier, hebdomadaire, mensuel, trimestriel)",
    )


def datetime_range(d0: date, d1: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(d0, datetime.min.time())
    end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt


def statut_affichage(statut: FactureStatut, montant_total: Decimal, montant_regle: Decimal) -> tuple[str, str]:
    st = statut.value if hasattr(statut, "value") else str(statut)
    if st == FactureStatut.payee.value:
        return "payee", "Payée"
    if st == FactureStatut.en_attente.value or st == FactureStatut.brouillon.value:
        return "en_attente", "En attente"
    if st == FactureStatut.partielle.value:
        return "partielle", "Partiel"
    if st in (FactureStatut.retard.value, FactureStatut.annulee.value):
        return "impayee", "Impayée"
    if montant_regle < montant_total:
        return "impayee", "Impayée"
    return "payee", "Payée"
