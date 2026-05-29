import base64
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
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
from app.services.consultation_info_service import get_consultation_info
from app.schemas.medecin import ConsultationOut, PatientRecordOut, PrescriptionOut
from app.services.patient_clinical import calc_age_years, derniere_consultation_at

router = APIRouter(prefix="/patients", tags=["patients"])

_role_caisse_or_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.admin.value,
)
_role_hospit_caisse_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.resp_hospit.value,
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


def _patient_to_out(p: Patient, db: Session) -> PatientCaisseOut:
    info = get_consultation_info(db, p)
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
        medecin_nom=info.get("medecin_nom"),
        batiment=info.get("batiment"),
        type_consultation_label=info.get("type_consultation_label"),
        motif_consultation=info.get("motif_consultation") or None,
        montant_consultation_fcfa=info.get("montant_consultation_fcfa"),
        remise_passage_fcfa=info.get("remise_passage_fcfa"),
    )


@router.get("/qr/{code_patient}")
def patient_qr_png(
    code_patient: str,
    _: User = Depends(_role_caisse_or_admin),
):
    """QR code patient (historique) pour facture imprimée."""
    payload = f"PATIENT|{code_patient.strip().upper()}"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/lookup/{code_patient}", response_model=PatientCaisseOut)
def lookup_patient_by_code(
    code_patient: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_hospit_caisse_admin),
):
    """Chargement par ID patient exact (caisse / hospitalisation)."""
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
        return _patient_to_out(patient, db)
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


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
        return [_patient_to_out(p, db) for p in rows]
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
        return _patient_to_out(patient, db)
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
        if current.role.value != UserRole.admin.value:
            has_passage = db.scalars(
                select(PassageAccueil.id).where(
                    PassageAccueil.patient_id == patient.id,
                    PassageAccueil.medecin_id == current.id,
                ).limit(1)
            ).first()
            if patient.medecin_id != current.id and not has_passage:
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

        current_passage_id = passages[0].id if passages else None
        return PatientRecordOut(
            patient_id=patient.id,
            code_patient=patient.code_patient,
            nom=patient.nom,
            prenom=patient.prenom,
            telephone=patient.telephone,
            assureur=patient.assureur,
            date_naissance=patient.date_naissance,
            sexe=patient.sexe.value if patient.sexe is not None else None,
            age_ans=calc_age_years(patient.date_naissance),
            derniere_consultation=derniere_consultation_at(
                list(passages), exclude_passage_id=current_passage_id
            ),
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
