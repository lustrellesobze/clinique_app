from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.passage_accueil import PassageAccueil
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User, UserRole
from app.schemas.caisse import AssignDoctorIn, PatientCaisseOut
from app.schemas.medecin import ConsultationOut, PatientRecordOut, PrescriptionOut

router = APIRouter(prefix="/patients", tags=["patients"])

_role_caisse_or_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.admin.value,
)
_role_accueil_or_admin = require_role(
    UserRole.infirmiere_accueil.value,
    UserRole.admin.value,
)
_role_medecin_or_admin = require_role(
    UserRole.medecin.value,
    UserRole.admin.value,
)


def _patient_to_out(p: Patient) -> PatientCaisseOut:
    return PatientCaisseOut(
        id=p.id,
        code_patient=p.code_patient,
        nom=p.nom,
        prenom=p.prenom,
        date_naissance=p.date_naissance,
        telephone=p.telephone,
        email=p.email,
        medecin_id=p.medecin_id,
        assureur=p.assureur,
        numero_police_assurance=p.numero_police_assurance,
        est_actif=p.est_actif,
    )


@router.get("", response_model=list[PatientCaisseOut])
def search_patients(
    q: str = Query(min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    term = q.strip()
    like = f"%{term}%"
    try:
        stmt = (
            select(Patient)
            .where(
                Patient.est_actif.is_(True),
                or_(
                    Patient.code_patient == term,
                    Patient.nom.ilike(like),
                    Patient.prenom.ilike(like),
                    Patient.telephone.ilike(like),
                ),
            )
            .order_by(Patient.created_at.desc())
            .limit(30)
        )
        rows = db.scalars(stmt).all()
        return [_patient_to_out(p) for p in rows]
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.put("/{patient_id}/assign-doctor", response_model=PatientCaisseOut)
def assign_doctor(
    patient_id: str,
    body: AssignDoctorIn,
    db: Session = Depends(get_db),
    _: User = Depends(_role_accueil_or_admin),
):
    try:
        patient = db.scalars(select(Patient).where(Patient.id == patient_id)).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient introuvable",
            )

        medecin = db.scalars(
            select(User).where(
                User.id == body.medecin_id,
                User.role == UserRole.medecin,
                User.est_actif.is_(True),
            )
        ).first()
        if not medecin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Médecin invalide ou inactif",
            )

        patient.medecin_id = medecin.id
        db.commit()
        db.refresh(patient)
        return _patient_to_out(patient)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("/{patient_id}/record", response_model=PatientRecordOut)
def patient_record(
    patient_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    try:
        patient = db.scalars(select(Patient).where(Patient.id == patient_id)).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient introuvable",
            )
        if current.role.value != UserRole.admin.value and patient.medecin_id != current.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès dossier non autorisé pour ce médecin",
            )

        passages = db.scalars(
            select(PassageAccueil)
            .where(PassageAccueil.patient_id == patient.id)
            .order_by(PassageAccueil.created_at.desc())
            .limit(20)
        ).all()
        prescriptions = db.scalars(
            select(Prescription)
            .where(Prescription.patient_id == patient.id)
            .order_by(Prescription.created_at.desc())
            .limit(20)
        ).all()

        return PatientRecordOut(
            patient_id=patient.id,
            code_patient=patient.code_patient,
            nom=patient.nom,
            prenom=patient.prenom,
            telephone=patient.telephone,
            assureur=patient.assureur,
            passages=[
                ConsultationOut(
                    passage_id=p.id,
                    patient_id=p.patient_id,
                    statut=p.statut.value,
                    motif_consultation=p.motif_consultation or "",
                    poids_kg=p.poids_kg,
                    taille_cm=p.taille_cm,
                    temperature_c=p.temperature_c,
                    tension=p.tension,
                )
                for p in passages
            ],
            prescriptions=[
                PrescriptionOut(
                    id=pr.id,
                    patient_id=pr.patient_id,
                    medecin_id=pr.medecin_id,
                    passage_accueil_id=pr.passage_accueil_id,
                    type_prescription=pr.type_prescription,
                    statut=pr.statut,
                    notes=pr.notes,
                    created_at=pr.created_at,
                    items=[
                        {
                            "id": it.id,
                            "nom_item": it.nom_item,
                            "description": it.description,
                            "quantite": it.quantite,
                            "prix_unitaire": it.prix_unitaire,
                        }
                        for it in pr.items
                    ],
                )
                for pr in prescriptions
            ],
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
