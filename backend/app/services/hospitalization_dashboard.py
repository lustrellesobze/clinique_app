"""Statistiques et liste enrichie pour l'administration hospitalisation."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.hospitalization import Hospitalization
from app.models.invoice import Facture
from app.models.patient import Patient
from app.models.room import Room
from app.models.user import User


def _role_value(role: object) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _room_type_label(type_chambre: str | None) -> str:
    if not type_chambre:
        return ""
    labels = {
        "commune": "Commune",
        "individuelle": "Individuelle",
        "vip": "VIP",
    }
    return labels.get(type_chambre.lower(), type_chambre.capitalize())


def _days_since(admission: datetime) -> int:
    days = (datetime.now().date() - admission.date()).days + 1
    return max(1, days)


def build_hospitalization_dashboard(db: Session) -> dict:
    rooms = db.scalars(select(Room).order_by(Room.numero)).all()
    total_rooms = len(rooms)
    occupied_rooms = sum(1 for r in rooms if not r.est_disponible)

    hospitalizations = db.scalars(
        select(Hospitalization)
        .where(Hospitalization.statut == "en_cours")
        .order_by(Hospitalization.date_admission.desc())
    ).all()

    patients_rows: list[dict] = []
    total_ca = Decimal("0")
    total_days = 0

    for hosp in hospitalizations:
        patient = db.get(Patient, hosp.patient_id)
        room = db.get(Room, hosp.room_id)
        tarif = Decimal(str(room.tarif_journalier_fcfa if room else 0))
        jours = _days_since(hosp.date_admission)
        frais_chambre = tarif * jours

        factures = db.scalars(
            select(Facture).where(
                Facture.patient_id == hosp.patient_id,
                Facture.created_at >= hosp.date_admission,
                Facture.est_annulee.is_(False),
            )
        ).all()
        total_facture = sum(
            Decimal(str(f.montant_total or 0)) for f in factures
        )
        if total_facture < frais_chambre:
            total_facture = frais_chambre

        acompte = Decimal(str(hosp.acompte_verse_fcfa or 0))
        solde = max(Decimal("0"), total_facture - acompte)

        medecin_name = None
        if hosp.medecin_id:
            med = db.get(User, hosp.medecin_id)
            if med:
                medecin_name = f"Dr. {med.nom} {med.prenom}"

        room_num = room.numero if room else "?"
        room_type = _room_type_label(room.type_chambre if room else None)

        patients_rows.append(
            {
                "id": hosp.id,
                "patient_id": hosp.patient_id,
                "patient_code": patient.code_patient if patient else "",
                "patient_name": (
                    f"{patient.nom} {patient.prenom}" if patient else "Inconnu"
                ),
                "room_numero": room_num,
                "room_type": room.type_chambre if room else "",
                "room_label": f"Ch. {room_num} ({room_type})",
                "medecin_name": medecin_name,
                "date_admission": hosp.date_admission,
                "nombre_jours": jours,
                "frais_chambre_fcfa": float(frais_chambre),
                "total_facture_fcfa": float(total_facture),
                "acomptes_fcfa": float(acompte),
                "solde_fcfa": float(solde),
                "motif_hospitalisation": hosp.motif_hospitalisation,
                "tarif_journalier": float(tarif),
                "statut": hosp.statut,
            }
        )
        total_ca += total_facture
        total_days += jours

    avg_days = round(total_days / len(hospitalizations), 1) if hospitalizations else 0.0

    closed_count = db.scalar(
        select(func.count())
        .select_from(Hospitalization)
        .where(Hospitalization.statut == "cloture")
    ) or 0

    return {
        "stats": {
            "chambres_occupees": occupied_rooms,
            "chambres_total": total_rooms,
            "ca_hospitalisation_fcfa": float(total_ca),
            "duree_moyenne_jours": avg_days,
            "patients_hospitalises": len(hospitalizations),
            "sejours_clotures": int(closed_count),
        },
        "patients": patients_rows,
        "rooms_available": sum(1 for r in rooms if r.est_disponible),
    }
