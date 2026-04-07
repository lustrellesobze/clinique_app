from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.realtime import caisse_realtime_manager
from app.database import get_db
from app.models.invoice import Facture, FactureStatut
from app.models.payment import Paiement, StatutPaiement

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class MobileWebhookIn(BaseModel):
    reference_transaction: str = Field(min_length=3, max_length=120)
    status: str = Field(description="SUCCESS, FAILED, PENDING")
    provider: str | None = None
    paid_at: datetime | None = None
    amount: Decimal | None = None
    operator_message: str | None = None


@router.post("/mobile-money")
async def mobile_money_webhook(
    body: MobileWebhookIn,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
):
    # Pour la soutenance: token simple. A remplacer par signature HMAC opérateur.
    if x_webhook_token != "dev-mobile-webhook-token":
        raise HTTPException(status_code=401, detail="Webhook token invalide")

    payment = db.scalars(
        select(Paiement).where(Paiement.reference_transaction == body.reference_transaction)
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable")

    facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    status_up = body.status.upper()
    total = Decimal(str(facture.montant_total or 0))
    regle = Decimal(str(facture.montant_regle or 0))
    amount = Decimal(str(body.amount if body.amount is not None else payment.montant))

    if status_up == "SUCCESS" and payment.statut != StatutPaiement.confirme:
        payment.statut = StatutPaiement.confirme
        regle = regle + amount
        facture.montant_regle = float(regle)
        if regle >= total:
            facture.statut = FactureStatut.payee
        elif regle > 0:
            facture.statut = FactureStatut.partielle
        else:
            facture.statut = FactureStatut.en_attente
    elif status_up == "FAILED":
        payment.statut = StatutPaiement.annule
    else:
        payment.statut = StatutPaiement.en_attente

    if body.operator_message:
        payment.commentaire = f"{payment.commentaire or ''}\nWebhook: {body.operator_message}".strip()

    db.commit()
    db.refresh(payment)
    db.refresh(facture)

    await caisse_realtime_manager.broadcast(
        {
            "event": "mobile_payment_updated",
            "payment_id": payment.id,
            "reference_transaction": payment.reference_transaction,
            "payment_status": payment.statut.value,
            "invoice_id": facture.id,
            "invoice_status": facture.statut.value,
            "invoice_paid": float(facture.montant_regle or 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    return {"ok": True}


@router.websocket("/ws/caisse")
async def caisse_ws(ws: WebSocket):
    await caisse_realtime_manager.connect(ws)
    try:
        while True:
            # keep alive: front may optionally send ping
            await ws.receive_text()
    except WebSocketDisconnect:
        caisse_realtime_manager.disconnect(ws)
