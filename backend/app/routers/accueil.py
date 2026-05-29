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
from app.models.insurance import Insurance
from app.services.audit_service import log_audit
from app.models.user import User, UserRole
from app.schemas.accueil import (
    FactureAccueilOut,
    InscriptionPatientCreate,
    InscriptionPatientResponse,
    MedecinOut,
    PassageAccueilOut,
    PatientOut,
)
from app.services.consultation_info_service import (
    creer_facture_consultation_depuis_passage,
    get_consultation_info,
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
        stmt = (
            select(User)
            .where(
                User.role == UserRole.medecin,
                User.est_actif.is_(True),
            )
            .order_by(User.nom, User.prenom)
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

        assurance = None
        compagnie_nom = None
        if data.est_assure:
            if not data.numero_assure:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Patient assuré : renseigner le numéro d'assuré",
                )
            if data.assurance_id:
                assurance = db.get(Insurance, data.assurance_id)
                if not assurance or not assurance.est_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Compagnie d'assurance invalide ou inactive",
                    )
                compagnie_nom = assurance.nom_compagnie
            elif data.compagnie_assurance:
                assurance = db.scalars(
                    select(Insurance).where(
                        Insurance.nom_compagnie == data.compagnie_assurance.strip(),
                        Insurance.est_active.is_(True),
                    )
                ).first()
                compagnie_nom = data.compagnie_assurance.strip()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Patient assuré : sélectionner une compagnie d'assurance",
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
            assurance_id=assurance.id if assurance else None,
            assureur=compagnie_nom if data.est_assure else None,
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
            compagnie_assurance=compagnie_nom,
            date_validite_assurance=data.date_validite_assurance,
            numero_assure=data.numero_assure,
            montant_consultation_fcfa=montant,
            remise_fcfa=remise,
            statut=StatutPassage.enregistre,
        )
        db.add(passage)
        db.flush()

        facture = creer_facture_consultation_depuis_passage(
            db, patient, passage, commentaire=None
        )
        info = get_consultation_info(db, patient, passage)

        log_audit(
            db,
            user_id=current.id,
            action="patient_create",
            entity_type="patient",
            entity_id=patient.id,
            details={
                "code_patient": patient.code_patient,
                "patient_nom": f"{patient.prenom} {patient.nom}",
                "medecin_nom": info.get("medecin_nom"),
                "numero_facture": facture.numero_facture,
            },
        )
        log_audit(
            db,
            user_id=current.id,
            action="invoice_create",
            entity_type="facture",
            entity_id=facture.id,
            details={
                "numero_facture": facture.numero_facture,
                "patient_code": patient.code_patient,
                "montant": float(facture.montant_total),
            },
        )

        db.commit()
        db.refresh(patient)
        db.refresh(passage)
        db.refresh(facture)
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

    facture_out = FactureAccueilOut(
        id=facture.id,
        numero_facture=facture.numero_facture,
        total_fcfa=Decimal(str(round(total, 2))),
        medecin_nom=info.get("medecin_nom"),
        batiment=info.get("batiment"),
    )

    med_label = info.get("medecin_nom") or "le médecin attribué"
    bat_label = info.get("batiment") or "le bâtiment indiqué sur la facture"

    return InscriptionPatientResponse(
        patient=_patient_to_out(patient),
        passage=passage_out,
        facture=facture_out,
        message_transfert=(
            f"Enregistrement OK. Le patient doit se rendre à la "
            f"caisse centrale avec le code {patient.code_patient} pour régler la "
            f"facture {facture.numero_facture}. Après paiement : consulter {med_label} "
            f"— {bat_label}."
        ),
    )
