from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.passage_accueil import PassageAccueil, StatutPassage
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.medecin import DoctorPatientOut

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
