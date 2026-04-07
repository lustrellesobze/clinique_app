"""
Routes API pour la gestion des ordonnances
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.patient import Patient
from app.models.passage_accueil import PassageAccueil, StatutPassage
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User, UserRole
from app.schemas.medecin import (
    PrescriptionCreateIn,
    PrescriptionOut,
    PrescriptionTransferIn,
)
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

_role_medecin_or_admin = require_role(
    UserRole.medecin.value,
    UserRole.admin.value,
)


def _to_out(p: Prescription) -> PrescriptionOut:
    return PrescriptionOut(
        id=p.id,
        patient_id=p.patient_id,
        medecin_id=p.medecin_id,
        passage_accueil_id=p.passage_accueil_id,
        type_prescription=p.type_prescription,
        statut=p.statut,
        notes=p.notes,
        created_at=p.created_at,
        items=[
            {
                "id": i.id,
                "nom_item": i.nom_item,
                "description": i.description,
                "quantite": i.quantite,
                "prix_unitaire": i.prix_unitaire,
            }
            for i in p.items
        ],
    )


@router.post("", response_model=PrescriptionOut, status_code=status.HTTP_201_CREATED)
def create_prescription(
    body: PrescriptionCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    try:
        patient = db.scalars(select(Patient).where(Patient.id == body.patient_id)).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient introuvable",
            )
        if body.passage_accueil_id:
            passage = db.scalars(
                select(PassageAccueil).where(PassageAccueil.id == body.passage_accueil_id)
            ).first()
            if not passage:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Passage accueil introuvable",
                )

        prescription = Prescription(
            patient_id=body.patient_id,
            medecin_id=current.id,
            passage_accueil_id=body.passage_accueil_id,
            type_prescription=body.type_prescription,
            statut="en_attente",
            notes=body.notes,
        )
        db.add(prescription)
        db.flush()

        for it in body.items:
            db.add(
                PrescriptionItem(
                    prescription_id=prescription.id,
                    nom_item=it.nom_item,
                    description=it.description,
                    quantite=it.quantite,
                    prix_unitaire=float(it.prix_unitaire),
                )
            )

        db.commit()
        db.refresh(prescription)
        _ = prescription.items
        return _to_out(prescription)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.post("/{prescription_id}/transfer", response_model=PrescriptionOut)
def transfer_prescription(
    prescription_id: str,
    body: PrescriptionTransferIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    try:
        p = db.scalars(select(Prescription).where(Prescription.id == prescription_id)).first()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription introuvable",
            )
        if current.role != UserRole.admin and p.medecin_id != current.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Prescription non autorisée pour ce médecin",
            )

        p.type_prescription = body.destination
        p.statut = "transferee"
        if body.commentaire:
            note = body.commentaire.strip()
            p.notes = f"{p.notes}\n\nTransfert: {note}" if p.notes else f"Transfert: {note}"

        if p.passage_accueil_id:
            passage = db.scalars(
                select(PassageAccueil).where(PassageAccueil.id == p.passage_accueil_id)
            ).first()
            if passage:
                passage.statut = StatutPassage.attente_paiement

        db.commit()
        db.refresh(p)
        _ = p.items
        return _to_out(p)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("/{prescription_id}/pdf")
def download_prescription_pdf(
    prescription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Télécharge une ordonnance en PDF."""
    prescription = db.get(Prescription, prescription_id)

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordonnance non trouvée",
        )

    patient = db.get(Patient, prescription.patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé",
        )

    pdf_buffer = PDFService.generate_prescription_pdf(
        prescription=prescription,
        patient=patient,
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ordonnance_{prescription.id}.pdf"
        },
    )
