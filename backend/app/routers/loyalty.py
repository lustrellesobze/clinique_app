from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.invoice import Facture, FactureStatut
from app.models.loyalty import LoyaltyPoints
from app.models.user import User, UserRole
from app.services.loyalty_service import LoyaltyService

router = APIRouter(prefix="/loyalty", tags=["loyalty"])

_role_caisse_or_admin = require_role(UserRole.caissier_central.value, UserRole.admin.value)


@router.get("/patient/{patient_id}")
def get_patient_points(
    patient_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        row = db.scalars(select(LoyaltyPoints).where(LoyaltyPoints.patient_id == patient_id)).first()
        if not row:
            return {"patient_id": patient_id, "points_balance": 0, "points_earned_total": 0}
        return {
            "patient_id": patient_id,
            "points_balance": row.points_balance,
            "points_earned_total": row.points_earned_total,
        }
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.post("/apply", status_code=status.HTTP_200_OK)
def apply_points(
    facture_id: str = Query(min_length=1),
    points: int = Query(ge=1),
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    try:
        inv = db.scalars(select(Facture).where(Facture.id == facture_id)).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Facture introuvable")
        if inv.statut == FactureStatut.payee:
            raise HTTPException(status_code=400, detail="Facture déjà payée")

        applied = LoyaltyService.apply_points_to_invoice(db, facture_id, points)
        db.commit()
        return {"facture_id": facture_id, "points_appliques": applied, "by": current.id}
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e

