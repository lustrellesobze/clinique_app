"""Détails JSON des compagnies d'assurance (taux par catégorie, franchise, exclusions)."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

DEFAULT_TAUX = {
    "consultation": 80,
    "imagerie": 70,
    "chirurgie": 50,
    "esthetique": 0,
    "hospitalisation": 100,
}

TYPE_ACTE_MAP = {
    "consultation": "consultation",
    "generale": "consultation",
    "laboratoire": "consultation",
    "labo": "consultation",
    "imagerie": "imagerie",
    "radiologie": "imagerie",
    "chirurgie": "chirurgie",
    "esthetique": "esthetique",
    "hospitalisation": "hospitalisation",
    "pharmacie": "consultation",
    "pharmaceutique": "consultation",
}


def default_details(taux_fallback: int = 80) -> dict[str, Any]:
    return {
        "taux_par_categorie": {**DEFAULT_TAUX, "consultation": taux_fallback},
        "franchise_fcfa": None,
        "franchise_libelle": "Aucune",
        "exclusions_list": [],
    }


def parse_details(raw_exclusions: str | None, taux_couverture: int) -> dict[str, Any]:
    base = default_details(taux_couverture)
    if not raw_exclusions or not raw_exclusions.strip():
        return base
    try:
        data = json.loads(raw_exclusions)
    except json.JSONDecodeError:
        return base
    if isinstance(data, list):
        base["exclusions_list"] = [str(x) for x in data]
        return base
    if isinstance(data, dict):
        if "taux_par_categorie" in data:
            merged = {**DEFAULT_TAUX, **data.get("taux_par_categorie", {})}
            base["taux_par_categorie"] = merged
        if "exclusions_list" in data:
            base["exclusions_list"] = list(data.get("exclusions_list") or [])
        if "franchise_fcfa" in data:
            base["franchise_fcfa"] = data.get("franchise_fcfa")
        if "franchise_libelle" in data:
            base["franchise_libelle"] = data.get("franchise_libelle") or "Aucune"
        return base
    return base


def serialize_details(
    taux_par_categorie: dict[str, int],
    franchise_fcfa: Decimal | None,
    franchise_libelle: str | None,
    exclusions_list: list[str],
) -> str:
    payload = {
        "taux_par_categorie": taux_par_categorie,
        "franchise_fcfa": float(franchise_fcfa) if franchise_fcfa is not None else None,
        "franchise_libelle": franchise_libelle or "Aucune",
        "exclusions_list": exclusions_list,
    }
    return json.dumps(payload, ensure_ascii=False)


def taux_for_acte(details: dict[str, Any], type_acte: str) -> int:
    key = TYPE_ACTE_MAP.get((type_acte or "consultation").lower(), "consultation")
    taux_map = details.get("taux_par_categorie") or DEFAULT_TAUX
    return int(taux_map.get(key, taux_map.get("consultation", 80)))


def is_acte_excluded(details: dict[str, Any], type_acte: str) -> bool:
    key = (type_acte or "").lower()
    for ex in details.get("exclusions_list") or []:
        ex_l = str(ex).lower()
        if ex_l == key or ex_l in key or key in ex_l:
            return True
    taux = taux_for_acte(details, type_acte)
    return taux <= 0
