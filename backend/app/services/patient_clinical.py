"""Helpers cliniques affichage dossier patient (médecin)."""

from datetime import date, datetime

from app.models.passage_accueil import PassageAccueil, StatutPassage


def calc_age_years(date_naissance: date | None) -> int | None:
    if not date_naissance:
        return None
    today = date.today()
    age = today.year - date_naissance.year
    if (today.month, today.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age


def derniere_consultation_at(
    passages: list[PassageAccueil],
    exclude_passage_id: str | None = None,
) -> datetime | None:
    """Date de la dernière consultation terminée (hors passage courant)."""
    ordered = sorted(
        passages,
        key=lambda p: p.created_at or datetime.min,
        reverse=True,
    )
    for pa in ordered:
        if exclude_passage_id and pa.id == exclude_passage_id:
            continue
        if pa.statut == StatutPassage.termine:
            return pa.created_at
    for pa in ordered:
        if exclude_passage_id and pa.id == exclude_passage_id:
            continue
        return pa.created_at
    return None
