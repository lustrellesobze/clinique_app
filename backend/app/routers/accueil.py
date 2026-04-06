import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.patient import Patient
from app.models.passage_accueil import PassageAccueil, StatutPassage
from app.models.user import User, UserRole
from app.schemas.accueil import (
    InscriptionPatientCreate,
    InscriptionPatientResponse,
    MedecinOut,
    PassageAccueilOut,
    PatientOut,
)

router = APIRouter(prefix="/accueil", tags=["accueil"])

_role_accueil = require_role(
    UserRole.infirmiere_accueil.value,
    UserRole.admin.value,
)


def _patient_to_out(p: Patient) -> PatientOut:
    return PatientOut(
        id=p.id,
        code_patient=p.code_patient,
        nom=p.nom,
        prenom=p.prenom,
        date_naissance=p.date_naissance,
        sexe=p.sexe.value if p.sexe is not None else None,
        telephone=p.telephone,
        email=p.email,
    )


def _generer_code_patient(db: Session) -> str:
    year = datetime.now().year
    for _ in range(80):
        suffix = f"{secrets.randbelow(100000):05d}"
        code = f"P-{year}-{suffix}"
        exists = db.scalar(select(Patient.id).where(Patient.code_patient == code))
        if not exists:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Impossible de générer un code patient unique",
    )


@router.get("/medecins", response_model=list[MedecinOut])
def liste_medecins(
    db: Session = Depends(get_db),
    _: User = Depends(_role_accueil),
):
    try:
        stmt = select(User).where(
            User.role == UserRole.medecin,
            User.est_actif.is_(True),
        )
        users = db.scalars(stmt).all()
        return [
            MedecinOut(id=u.id, nom=u.nom, prenom=u.prenom) for u in users
        ]
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.post(
    "/inscriptions",
    response_model=InscriptionPatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def creer_inscription(
    data: InscriptionPatientCreate,
    db: Session = Depends(get_db),
    current: User = Depends(_role_accueil),
):
    try:
        med = db.scalars(
            select(User).where(
                User.id == data.medecin_id,
                User.role == UserRole.medecin,
                User.est_actif.is_(True),
            )
        ).first()
        if not med:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Médecin invalide ou inactif",
            )

        if data.est_assure:
            if not data.compagnie_assurance or not data.numero_assure:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Patient assuré : renseigner la compagnie et le numéro d'assuré",
                )

        code = _generer_code_patient(db)

        patient = Patient(
            code_patient=code,
            nom=data.nom.strip(),
            prenom=data.prenom.strip(),
            date_naissance=data.date_naissance,
            sexe=data.sexe,
            telephone=data.telephone,
            email=data.email,
            contact_urgence=data.contact_urgence,
            medecin_id=data.medecin_id,
            assureur=data.compagnie_assurance if data.est_assure else None,
            numero_police_assurance=data.numero_assure if data.est_assure else None,
            est_actif=True,
        )
        db.add(patient)
        db.flush()

        montant = float(data.montant_consultation_fcfa)
        remise = float(data.remise_fcfa)
        total = max(0.0, montant - remise)

        passage = PassageAccueil(
            patient_id=patient.id,
            enregistre_par_id=current.id,
            medecin_id=data.medecin_id,
            poids_kg=float(data.poids_kg) if data.poids_kg is not None else None,
            taille_cm=float(data.taille_cm) if data.taille_cm is not None else None,
            temperature_c=float(data.temperature_c)
            if data.temperature_c is not None
            else None,
            tension=data.tension,
            motif_consultation=data.motif_consultation or "",
            type_consultation=data.type_consultation,
            derniere_date_regles=data.derniere_date_regles,
            est_assure=data.est_assure,
            compagnie_assurance=data.compagnie_assurance,
            date_validite_assurance=data.date_validite_assurance,
            numero_assure=data.numero_assure,
            montant_consultation_fcfa=montant,
            remise_fcfa=remise,
            statut=StatutPassage.enregistre,
        )
        db.add(passage)
        db.commit()
        db.refresh(patient)
        db.refresh(passage)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Données incohérentes (clé étrangère ou doublon).",
        ) from e
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e

    passage_out = PassageAccueilOut(
        id=passage.id,
        patient_id=passage.patient_id,
        statut=passage.statut.value,
        type_consultation=passage.type_consultation.value,
        montant_consultation_fcfa=data.montant_consultation_fcfa,
        remise_fcfa=data.remise_fcfa,
        total_fcfa=Decimal(str(round(total, 2))),
        medecin_id=passage.medecin_id,
        enregistre_par_id=passage.enregistre_par_id,
    )

    return InscriptionPatientResponse(
        patient=_patient_to_out(patient),
        passage=passage_out,
        message_transfert=(
            f"Enregistrement OK. Communiquer au médecin et à la caisse "
            f"l'identifiant patient : {patient.code_patient} (passage {passage.id[:8]}…)."
        ),
    )
