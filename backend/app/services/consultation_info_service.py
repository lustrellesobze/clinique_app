"""Médecin attribué, bâtiment de consultation et facture liée au passage d'accueil."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Facture, FactureStatut, LigneFacture
from app.models.passage_accueil import PassageAccueil, StatutPassage, TypeConsultationPassage
from app.models.patient import Patient
from app.models.user import User, UserRole

# Spécialité / service du médecin → lieu de consultation
BATIMENT_PAR_SERVICE: dict[str, str] = {
    "Médecine": "Bâtiment A — Consultations générales",
    "Médecine générale": "Bâtiment A — Consultations générales",
    "Pédiatrie": "Bâtiment B — Pédiatrie",
    "Cardiologie": "Bâtiment C — Cardiologie",
    "Gynécologie": "Bâtiment D — Gynécologie",
}

BATIMENT_PAR_TYPE_CONSULTATION: dict[str, str] = {
    TypeConsultationPassage.urgence.value: "Pôle urgences — Bâtiment E",
    TypeConsultationPassage.specialiste.value: "Bâtiment C — Consultations spécialisées",
}

DEFAULT_BATIMENT = "Bâtiment A — Consultations générales"

TYPE_CONSULTATION_LABELS: dict[str, str] = {
    "generale": "Consultation générale",
    "rendez_vous": "Rendez-vous",
    "specialiste": "Spécialiste",
    "urgence": "Urgence",
}


def format_medecin_nom(medecin: User | None) -> str | None:
    if not medecin:
        return None
    label = f"{medecin.prenom.strip()} {medecin.nom.strip()}".strip()
    if not label:
        return None
    if label.lower().startswith("dr"):
        return label
    return f"Dr {label}"


def resolve_batiment(
    medecin: User | None,
    type_consultation: str | None = None,
) -> str:
    if type_consultation and type_consultation in BATIMENT_PAR_TYPE_CONSULTATION:
        return BATIMENT_PAR_TYPE_CONSULTATION[type_consultation]
    if medecin and medecin.service:
        return BATIMENT_PAR_SERVICE.get(medecin.service.strip(), DEFAULT_BATIMENT)
    return DEFAULT_BATIMENT


def get_dernier_passage_actif(db: Session, patient_id: str) -> PassageAccueil | None:
    return db.scalars(
        select(PassageAccueil)
        .where(
            PassageAccueil.patient_id == patient_id,
            PassageAccueil.statut.in_(
                [
                    StatutPassage.enregistre,
                    StatutPassage.attente_paiement,
                    StatutPassage.en_consultation,
                ]
            ),
        )
        .order_by(PassageAccueil.created_at.desc())
        .limit(1)
    ).first()


def get_consultation_info(
    db: Session,
    patient: Patient,
    passage: PassageAccueil | None = None,
) -> dict:
    passage = passage or get_dernier_passage_actif(db, patient.id)
    medecin_id = (passage.medecin_id if passage else None) or patient.medecin_id
    medecin = (
        db.scalars(select(User).where(User.id == medecin_id)).first()
        if medecin_id
        else None
    )
    type_val = (
        passage.type_consultation.value
        if passage and passage.type_consultation is not None
        else None
    )
    return {
        "medecin_id": medecin_id,
        "medecin_nom": format_medecin_nom(medecin),
        "batiment": resolve_batiment(medecin, type_val),
        "type_consultation": type_val,
        "type_consultation_label": TYPE_CONSULTATION_LABELS.get(type_val or "", type_val),
        "motif_consultation": (passage.motif_consultation or "").strip() if passage else "",
        "montant_consultation_fcfa": float(passage.montant_consultation_fcfa)
        if passage
        else None,
        "remise_passage_fcfa": float(passage.remise_fcfa) if passage else None,
        "passage_id": passage.id if passage else None,
    }


def _generer_numero_facture_consultation(db: Session, year: int) -> str:
    import secrets

    for _ in range(100):
        suffix = f"{secrets.randbelow(100000):05d}"
        num = f"FACT-CONS-{year}-{suffix}"
        exists = db.scalar(select(Facture.id).where(Facture.numero_facture == num))
        if not exists:
            return num
    raise RuntimeError("Impossible de générer un numéro de facture unique")


def get_facture_consultation_en_attente(db: Session, patient_id: str) -> Facture | None:
    return db.scalars(
        select(Facture)
        .where(
            Facture.patient_id == patient_id,
            Facture.numero_facture.like("FACT-CONS-%"),
            Facture.est_annulee.is_(False),
            Facture.statut.in_(
                [
                    FactureStatut.en_attente,
                    FactureStatut.partielle,
                    FactureStatut.brouillon,
                ]
            ),
        )
        .order_by(Facture.created_at.desc())
        .limit(1)
    ).first()


def get_facture_consultation_pour_caisse(db: Session, patient_id: str) -> Facture | None:
    """
    Facture unique affichée à la caisse : consultation en attente la plus récente,
    sinon la dernière facture consultation (ex. déjà payée, pour réimpression).
    """
    pending = get_facture_consultation_en_attente(db, patient_id)
    if pending:
        return pending
    return db.scalars(
        select(Facture)
        .where(
            Facture.patient_id == patient_id,
            Facture.numero_facture.like("FACT-CONS-%"),
            Facture.est_annulee.is_(False),
        )
        .order_by(Facture.created_at.desc())
        .limit(1)
    ).first()


def creer_facture_consultation_depuis_passage(
    db: Session,
    patient: Patient,
    passage: PassageAccueil,
    *,
    caissier_id: str | None = None,
    commentaire: str | None = None,
) -> Facture:
    existing = get_facture_consultation_en_attente(db, patient.id)
    if existing:
        return existing

    from datetime import datetime

    montant = Decimal(str(passage.montant_consultation_fcfa or 0))
    remise = Decimal(str(passage.remise_fcfa or 0))
    montant_ligne = max(Decimal("0"), montant - remise)

    info = get_consultation_info(db, patient, passage)
    note = (
        f"Consultation — {info['medecin_nom'] or 'Médecin à confirmer'} — "
        f"{info['batiment']}"
    )
    if commentaire:
        note = f"{commentaire.strip()} | {note}"

    facture = Facture(
        numero_facture=_generer_numero_facture_consultation(db, datetime.now().year),
        patient_id=patient.id,
        caissier_id=caissier_id,
        statut=FactureStatut.en_attente if montant_ligne > 0 else FactureStatut.payee,
        devise="XAF",
        commentaire=note,
        remise_globale=0,
        montant_total=float(montant_ligne),
        part_patient=float(montant_ligne),
        montant_regle=0,
    )
    db.add(facture)
    db.flush()

    db.add(
        LigneFacture(
            facture_id=facture.id,
            ordre=1,
            designation="Consultation",
            quantite=1,
            prix_unitaire=float(montant),
            remise_montant=float(remise),
            montant_ligne=float(montant_ligne),
        )
    )

    if passage.statut == StatutPassage.enregistre:
        passage.statut = StatutPassage.attente_paiement

    return facture
