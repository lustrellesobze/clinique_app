"""
Routes WebSocket pour les notifications en temps réel
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.websocket_manager import manager
from app.core.security import decode_access_token

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint pour recevoir les notifications en temps réel
    
    Usage: ws://localhost:8000/api/ws/notifications?token=<jwt_token>
    """
    # Vérifier le token JWT
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=1008, reason="Token invalide")
            return
    except Exception as e:
        await websocket.close(code=1008, reason=f"Erreur d'authentification: {str(e)}")
        return
    
    # Connecter le WebSocket
    await manager.connect(websocket, user_id)
    
    try:
        # Garder la connexion ouverte et écouter les messages
        while True:
            # Recevoir les messages du client (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # On peut traiter des commandes ici si nécessaire
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        manager.disconnect(websocket, user_id)
