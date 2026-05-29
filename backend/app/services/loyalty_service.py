from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Facture
from app.models.loyalty import LoyaltyPoints


class LoyaltyService:
    """
    Règle simple (MVP soutenance):
    - 1 point gagné par tranche de 1000 FCFA encaissés.
    - 1 point = 1 FCFA de remise applicable sur une facture non payée.
    """

    @staticmethod
    def ensure_patient_row(db: Session, patient_id: str) -> LoyaltyPoints:
        row = db.scalars(select(LoyaltyPoints).where(LoyaltyPoints.patient_id == patient_id)).first()
        if row:
            return row
        row = LoyaltyPoints(patient_id=patient_id, points_balance=0, points_earned_total=0)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def add_points_for_payment(db: Session, patient_id: str, montant: Decimal) -> int:
        row = LoyaltyService.ensure_patient_row(db, patient_id)
        earned = int((montant // Decimal("1000")))
        if earned <= 0:
            return 0
        row.points_balance += earned
        row.points_earned_total += earned
        return earned

    @staticmethod
    def apply_points_to_invoice(db: Session, facture_id: str, points_to_use: int) -> int:
        if points_to_use <= 0:
            return 0
        facture = db.scalars(select(Facture).where(Facture.id == facture_id)).first()
        if not facture:
            return 0

        patient_id = facture.patient_id
        row = LoyaltyService.ensure_patient_row(db, patient_id)
        usable = min(int(row.points_balance), int(points_to_use))
        if usable <= 0:
            return 0

        total = Decimal(str(facture.montant_total or 0))
        regle = Decimal(str(facture.montant_regle or 0))
        restant = max(Decimal("0"), total - regle)
        remise = Decimal(str(usable))
        remise = min(remise, restant)  # on ne peut pas descendre sous le déjà-payé

        # Appliquer comme remise globale: réduit montant_total
        facture.remise_globale = float(Decimal(str(facture.remise_globale or 0)) + remise)
        facture.montant_total = float(max(Decimal("0"), total - remise))
        facture.part_patient = facture.montant_total

        row.points_balance -= int(remise)
        return int(remise)

