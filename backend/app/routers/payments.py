import base64
import io
import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
import qrcode

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.core.realtime import caisse_realtime_manager
from app.database import get_db
from app.models.invoice import Facture, FactureStatut
from app.models.payment import ModePaiement, Paiement, StatutPaiement
from app.models.user import User, UserRole
from app.schemas.caisse import (
    MobilePaymentInitIn,
    MobilePaymentInitOut,
    PaymentCreateIn,
    PaymentOut,
    PaymentStatusOut,
)

router = APIRouter(prefix="/payments", tags=["payments"])

_role_caisse_or_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.admin.value,
)


def _to_decimal(v: object, default: str = "0") -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal(default)
    return Decimal(str(v))


def _build_payment_status(payment: Paiement, facture: Facture) -> PaymentStatusOut:
    total = _to_decimal(facture.montant_total)
    regle = _to_decimal(facture.montant_regle)
    return PaymentStatusOut(
        payment_id=payment.id,
        statut=payment.statut.value,
        facture_statut=facture.statut.value,
        montant_regle=regle,
        restant_a_payer=max(Decimal("0"), total - regle),
    )


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    try:
        facture = db.scalars(select(Facture).where(Facture.id == body.facture_id)).first()
        if not facture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture introuvable",
            )

        total = _to_decimal(facture.montant_total)
        regle = _to_decimal(facture.montant_regle)
        montant = _to_decimal(body.montant)
        restant = max(Decimal("0"), total - regle)
        if montant > restant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Montant trop élevé. Reste à payer: {restant} FCFA",
            )

        payment = Paiement(
            facture_id=facture.id,
            caissier_id=current.id,
            montant=float(montant),
            mode_paiement=ModePaiement(body.mode_paiement),
            statut=StatutPaiement.confirme,
            reference_transaction=body.reference_transaction,
            commentaire=body.commentaire,
        )
        db.add(payment)

        new_regle = regle + montant
        facture.montant_regle = float(new_regle)
        if new_regle >= total:
            facture.statut = FactureStatut.payee
        elif new_regle > 0:
            facture.statut = FactureStatut.partielle
        else:
            facture.statut = FactureStatut.en_attente

        db.commit()
        db.refresh(payment)
        return payment
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.post(
    "/mobile/initiate",
    response_model=MobilePaymentInitOut,
    status_code=status.HTTP_201_CREATED,
)
def initiate_mobile_payment(
    body: MobilePaymentInitIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    """Mode mock pour soutenance: génère QR et statut en_attente.

    TODO: brancher l'API opérateur (Orange/MTN) ici.
    """
    try:
        facture = db.scalars(select(Facture).where(Facture.id == body.facture_id)).first()
        if not facture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture introuvable",
            )
        total = _to_decimal(facture.montant_total)
        regle = _to_decimal(facture.montant_regle)
        montant = _to_decimal(body.montant)
        restant = max(Decimal("0"), total - regle)
        if montant > restant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Montant trop élevé. Reste à payer: {restant} FCFA",
            )

        ref = body.reference_transaction or (
            f"{'OM' if body.provider == 'orange_money' else 'MM'}"
            f"-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.randbelow(1000):03d}"
        )
        payment = Paiement(
            facture_id=facture.id,
            caissier_id=current.id,
            montant=float(montant),
            mode_paiement=ModePaiement(body.provider),
            statut=StatutPaiement.en_attente,
            reference_transaction=ref,
            commentaire="Paiement mobile initié (mock avant API opérateur).",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        payload = (
            f"CLINIQUE|facture={facture.numero_facture}|montant={montant}|"
            f"provider={body.provider}|ref={ref}"
        )
        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

        return MobilePaymentInitOut(
            payment=payment,
            qr_png_base64=qr_b64,
            qr_payload=payload,
            instructions=[
                "Ouvrez votre application Mobile Money.",
                "Scannez le QR code puis validez sur votre téléphone.",
                "Utilisez ensuite le bouton de confirmation dans la caisse.",
            ],
        )
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("/mobile/{payment_id}/status", response_model=PaymentStatusOut)
def mobile_payment_status(
    payment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        payment = db.scalars(select(Paiement).where(Paiement.id == payment_id)).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Paiement introuvable")
        facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
        if not facture:
            raise HTTPException(status_code=404, detail="Facture introuvable")
        return _build_payment_status(payment, facture)
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.post("/mobile/{payment_id}/confirm", response_model=PaymentStatusOut)
def confirm_mobile_payment_mock(
    payment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    """Confirmation mock manuelle (en attendant webhook opérateur)."""
    try:
        payment = db.scalars(select(Paiement).where(Paiement.id == payment_id)).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Paiement introuvable")
        facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
        if not facture:
            raise HTTPException(status_code=404, detail="Facture introuvable")

        if payment.statut == StatutPaiement.en_attente:
            payment.statut = StatutPaiement.confirme
            total = _to_decimal(facture.montant_total)
            regle = _to_decimal(facture.montant_regle) + _to_decimal(payment.montant)
            facture.montant_regle = float(regle)
            if regle >= total:
                facture.statut = FactureStatut.payee
            elif regle > 0:
                facture.statut = FactureStatut.partielle
            else:
                facture.statut = FactureStatut.en_attente
            db.commit()
            db.refresh(payment)
            db.refresh(facture)
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    caisse_realtime_manager.broadcast(
                        {
                            "event": "mobile_payment_updated",
                            "payment_id": payment.id,
                            "reference_transaction": payment.reference_transaction,
                            "payment_status": payment.statut.value,
                            "invoice_id": facture.id,
                            "invoice_status": facture.statut.value,
                            "invoice_paid": float(facture.montant_regle or 0),
                        }
                    )
                )
            except RuntimeError:
                pass

        return _build_payment_status(payment, facture)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("", response_model=list[PaymentOut])
def list_payments(
    facture_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        rows = db.scalars(
            select(Paiement)
            .where(Paiement.facture_id == facture_id)
            .order_by(Paiement.created_at.desc())
        ).all()
        return rows
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
