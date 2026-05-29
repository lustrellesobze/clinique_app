from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.passage_accueil import PassageAccueil, StatutPassage
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.medecin import DoctorLookupOut, DoctorPatientOut
from app.services.patient_clinical import calc_age_years, derniere_consultation_at

router = APIRouter(prefix="/doctor", tags=["doctor"])

_role_medecin_or_admin = require_role(
    UserRole.medecin.value,
    UserRole.admin.value,
)


@router.get("/patients", response_model=list[DoctorPatientOut])
def doctor_patients(
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    try:
        stmt = (
            select(PassageAccueil, Patient)
            .join(Patient, Patient.id == PassageAccueil.patient_id)
            .where(
                PassageAccueil.medecin_id == current.id,
                PassageAccueil.statut.in_(
                    [
                        StatutPassage.enregistre,
                        StatutPassage.en_consultation,
                        StatutPassage.attente_paiement,
                    ]
                ),
            )
            .order_by(PassageAccueil.created_at.desc())
        )
        rows = db.execute(stmt).all()
        return [
            DoctorPatientOut(
                patient_id=p.id,
                passage_id=pa.id,
                code_patient=p.code_patient,
                nom=p.nom,
                prenom=p.prenom,
                telephone=p.telephone,
                assureur=p.assureur,
                statut_passage=pa.statut.value,
                type_consultation=pa.type_consultation.value,
                created_at=pa.created_at,
            )
            for pa, p in rows
        ]
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/lookup/{code_patient}", response_model=DoctorLookupOut)
def doctor_lookup_patient(
    code_patient: str,
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    """Charge un patient par ID pour la consultation (passage actif du médecin)."""
    code = code_patient.strip().upper()
    try:
        patient = db.scalars(
            select(Patient).where(
                Patient.code_patient == code,
                Patient.est_actif.is_(True),
            )
        ).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucun patient actif avec l'ID {code}",
            )

        passage = db.scalars(
            select(PassageAccueil)
            .where(
                PassageAccueil.patient_id == patient.id,
                PassageAccueil.medecin_id == current.id,
                PassageAccueil.statut.in_(
                    [
                        StatutPassage.enregistre,
                        StatutPassage.en_consultation,
                        StatutPassage.attente_paiement,
                    ]
                ),
            )
            .order_by(PassageAccueil.created_at.desc())
            .limit(1)
        ).first()
        if not passage and current.role.value != UserRole.admin.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune consultation active pour ce patient avec votre compte",
            )
        if not passage:
            passage = db.scalars(
                select(PassageAccueil)
                .where(PassageAccueil.patient_id == patient.id)
                .order_by(PassageAccueil.created_at.desc())
                .limit(1)
            ).first()
        if not passage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun passage accueil pour ce patient",
            )

        all_passages = db.scalars(
            select(PassageAccueil).where(PassageAccueil.patient_id == patient.id)
        ).all()

        return DoctorLookupOut(
            patient_id=patient.id,
            passage_id=passage.id,
            code_patient=patient.code_patient,
            nom=patient.nom,
            prenom=patient.prenom,
            telephone=patient.telephone,
            assureur=patient.assureur or passage.compagnie_assurance,
            statut_passage=passage.statut.value,
            type_consultation=passage.type_consultation.value,
            created_at=passage.created_at,
            date_naissance=patient.date_naissance,
            sexe=patient.sexe.value if patient.sexe is not None else None,
            age_ans=calc_age_years(patient.date_naissance),
            derniere_consultation=derniere_consultation_at(
                list(all_passages), exclude_passage_id=passage.id
            ),
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
