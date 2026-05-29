"""
Webhooks (Mobile Money / Campay) et WebSockets (notifications utilisateur, caisse).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.realtime import caisse_realtime_manager
from app.core.security import decode_access_token
from app.core.websocket_manager import manager
from app.database import get_db
from app.services.campay_webhook import (
    apply_campay_notification_to_payment,
    finalize_confirmed_mobile_payment_effects,
    find_payment_for_campay_refs,
    parse_campay_transaction_notification,
    parse_webhook_raw_body,
    verify_campay_webhook_request,
)

# Notifications temps réel (JWT) — chemin final: /api/ws/notifications
ws_router = APIRouter(prefix="/ws", tags=["websocket"])

# Webhooks HTTP + WebSocket caisse
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@ws_router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket pour les notifications utilisateur.

    Usage: ws://localhost:8000/api/ws/notifications?token=<jwt_token>
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=1008, reason="Token invalide")
            return
    except Exception as e:
        await websocket.close(code=1008, reason=f"Erreur d'authentification: {str(e)}")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        manager.disconnect(websocket, user_id)


@router.post("/mobile-money")
async def mobile_money_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Callback Campay : corps JSON identique à la réponse transaction
    (reference, external_reference, status: PENDING|SUCCESSFUL|FAILED, amount, currency,
    operator, code, operator_reference, description).

    Auth :
    - JWT HS256 signé avec ``CAMPAY_WEBHOOK_SECRET`` (Authorization: Bearer … ou en-têtes du type
      X-Campay-Signature), comme ``ValidateCallback`` dans le SDK Go officiel ;
    - ou en-tête ``x-webhook-token`` égal à ``CAMPAY_WEBHOOK_SECRET`` (ou jeton dev si secret vide).
    """
    raw_body = await request.body()
    payload_dict, body_was_verified_jwt = parse_webhook_raw_body(raw_body)

    if not payload_dict:
        raise HTTPException(status_code=400, detail="Corps webhook vide ou invalide")

    verify_campay_webhook_request(
        request,
        payload_dict=payload_dict,
        raw_body=raw_body,
        body_was_verified_jwt=body_was_verified_jwt,
    )

    notify = parse_campay_transaction_notification(payload_dict)
    if not notify.lookup_refs:
        raise HTTPException(status_code=400, detail="reference / external_reference manquant")

    payment, facture = find_payment_for_campay_refs(db, notify.lookup_refs)
    if not payment or not facture:
        raise HTTPException(status_code=404, detail="Paiement introuvable")

    outcome = apply_campay_notification_to_payment(db, payment=payment, facture=facture, notify=notify)

    if outcome == "confirmed":
        finalize_confirmed_mobile_payment_effects(db, payment, facture)

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
            "campay_raw_status": notify.raw_status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    return {"ok": True, "outcome": outcome}


@router.websocket("/ws/caisse")
async def caisse_ws(ws: WebSocket):
    await caisse_realtime_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        caisse_realtime_manager.disconnect(ws)
