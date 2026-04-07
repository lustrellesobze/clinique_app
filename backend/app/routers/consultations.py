from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.passage_accueil import PassageAccueil, StatutPassage
from app.models.user import User, UserRole
from app.schemas.medecin import ConsultationOut, ConsultationUpdateIn

router = APIRouter(prefix="/consultations", tags=["consultations"])

_role_medecin_or_admin = require_role(
    UserRole.medecin.value,
    UserRole.admin.value,
)


@router.put("/{consultation_id}", response_model=ConsultationOut)
def update_consultation(
    consultation_id: str,
    body: ConsultationUpdateIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_medecin_or_admin),
):
    try:
        passage = db.scalars(
            select(PassageAccueil).where(PassageAccueil.id == consultation_id)
        ).first()
        if not passage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation introuvable",
            )
        if current.role.value != UserRole.admin.value and passage.medecin_id != current.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette consultation n'est pas affectée à ce médecin",
            )

        if body.statut:
            passage.statut = StatutPassage(body.statut)
        if body.poids_kg is not None:
            passage.poids_kg = float(body.poids_kg)
        if body.taille_cm is not None:
            passage.taille_cm = float(body.taille_cm)
        if body.temperature_c is not None:
            passage.temperature_c = float(body.temperature_c)
        if body.tension is not None:
            passage.tension = body.tension

        observations = (body.observations or "").strip()
        diagnostic = (body.diagnostic or "").strip()
        if observations or diagnostic:
            base = (passage.motif_consultation or "").strip()
            block = []
            if observations:
                block.append(f"Observations medecin:\n{observations}")
            if diagnostic:
                block.append(f"Diagnostic:\n{diagnostic}")
            passage.motif_consultation = (
                f"{base}\n\n" + "\n\n".join(block) if base else "\n\n".join(block)
            )

        db.commit()
        db.refresh(passage)
        return ConsultationOut(
            passage_id=passage.id,
            patient_id=passage.patient_id,
            statut=passage.statut.value,
            motif_consultation=passage.motif_consultation or "",
            poids_kg=passage.poids_kg,
            taille_cm=passage.taille_cm,
            temperature_c=passage.temperature_c,
            tension=passage.tension,
        )
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e
