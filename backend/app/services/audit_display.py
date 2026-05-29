"""Formatage des entrées audit pour l'interface admin."""

from __future__ import annotations

import json
from typing import Any

from app.models.audit import AuditLog
from app.models.user import User


def _parse_details(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _user_label(user: User | None) -> str:
    if not user:
        return "Système"
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return f"{user.prenom} {user.nom} ({role})"


def categorize(action: str, entity_type: str | None) -> tuple[str, str, str]:
    a = (action or "").lower()
    et = (entity_type or "").lower()

    if "payment" in a or "paiement" in et or a == "mobile_payment_confirm":
        return "PAIEMENT", "Paiement", "paiement"
    if "cancel" in a or "annul" in a:
        return "ANNULATION", "Annulation", "annulation"
    if "prescription" in a or "prescription" in et:
        return "PRESCRIPTION", "Transfert", "prescription"
    if "patient" in et or "patient" in a:
        return "PATIENT", "Attribution", "patient"
    if "facture" in et or "invoice" in a or "facture" in a:
        return "FACTURE", "Création", "facture"
    if "login" in a or "session" in a or "connexion" in a:
        return "SYSTÈME", "Connexion", "systeme"
    if "email" in a:
        return "SYSTÈME", "Notification", "systeme"
    return "SYSTÈME", "Opération", "systeme"


def build_entry(row: AuditLog, user: User | None) -> dict[str, Any]:
    details = _parse_details(row.details_json)
    cat, statut_label, css_key = categorize(row.action, row.entity_type)
    par = _user_label(user)

    titre = _build_titre(row, details, cat)
    details_ligne = _build_details_ligne(row, details, par, user)

    return {
        "id": row.id,
        "created_at": row.created_at,
        "categorie": cat,
        "categorie_label": cat,
        "titre": titre,
        "details_ligne": details_ligne,
        "statut_label": statut_label,
        "user_id": row.user_id,
        "user_nom": user.nom if user else None,
        "user_prenom": user.prenom if user else None,
        "user_role": user.role.value if user and hasattr(user.role, "value") else None,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "ip": row.ip,
        "css_key": css_key,
    }


def _build_titre(row: AuditLog, details: dict, cat: str) -> str:
    eid = row.entity_id or ""
    if cat == "PAIEMENT":
        ref = details.get("reference") or details.get("reference_transaction") or ""
        mt = details.get("montant")
        if mt:
            return f"Paiement confirmé — {float(mt):,.0f} FCFA".replace(",", " ")
        return "Paiement confirmé"
    if cat == "FACTURE":
        num = details.get("numero_facture") or eid
        return f"Facture #{num} — opération enregistrée"
    if cat == "PATIENT":
        if "medecin" in str(details).lower() or details.get("medecin_id"):
            return "Nouveau patient enregistré — Médecin attribué"
        return "Opération patient enregistrée"
    if cat == "PRESCRIPTION":
        return "Prescription transférée"
    if cat == "ANNULATION":
        num = details.get("numero_facture") or eid
        return f"Facture #{num} annulée"
    if cat == "SYSTÈME" and "login" in row.action.lower():
        return "Connexion utilisateur"
    return f"{row.action.replace('_', ' ').title()}"


def _build_details_ligne(row: AuditLog, details: dict, par: str, user: User | None) -> str:
    parts = [f"Par: {par}"]
    if details.get("patient_nom"):
        parts.append(f"Patient: {details['patient_nom']}")
    if details.get("patient_code"):
        parts.append(f"Patient: {details['patient_code']}")
    if details.get("code_patient"):
        parts.append(f"Patient: {details['code_patient']}")
    if details.get("medecin_nom"):
        parts.append(f"Médecin assigné: {details['medecin_nom']}")
    if details.get("facture_id"):
        parts.append(f"Facture: {details['facture_id'][:8]}…")
    if details.get("numero_facture"):
        parts.append(f"Facture: {details['numero_facture']}")
    if details.get("mode"):
        parts.append(f"Mode: {details['mode']}")
    if details.get("motif"):
        parts.append(f"Motif: {details['motif']}")
    if row.ip:
        parts.append(f"IP: {row.ip}")
    if user and "login" in row.action.lower():
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        parts.append(f"Rôle: {role}")
        parts.append("Session démarrée")
    return " · ".join(parts)
