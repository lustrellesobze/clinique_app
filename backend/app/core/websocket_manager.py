"""
Gestionnaire WebSocket pour les notifications en temps réel
"""
from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """Gère les connexions WebSocket pour les notifications en temps réel"""
    
    def __init__(self):
        # Dictionnaire: user_id -> Set de WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accepte une nouvelle connexion WebSocket pour un utilisateur"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        print(f"✅ WebSocket connecté pour user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Déconnecte un WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Nettoyer si plus aucune connexion
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        print(f"❌ WebSocket déconnecté pour user_id={user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Envoie un message à un utilisateur spécifique (toutes ses connexions)"""
        if user_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Erreur envoi WebSocket: {e}")
                    disconnected.add(connection)
            
            # Nettoyer les connexions mortes
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast(self, message: dict):
        """Envoie un message à tous les utilisateurs connectés"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
    
    async def send_notification(self, user_id: str, notification_data: dict):
        """Envoie une notification à un utilisateur"""
        message = {
            "type": "notification",
            "data": notification_data
        }
        await self.send_personal_message(message, user_id)


# Instance globale du gestionnaire
manager = ConnectionManager()
