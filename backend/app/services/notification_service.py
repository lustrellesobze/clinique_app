"""
Service de gestion des notifications utilisateur
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import asyncio

from app.models.notification import Notification
from app.models.user import User


class NotificationService:
    """Service pour gérer les notifications"""
    
    @staticmethod
    async def create_notification_async(
        db: Session,
        user_id: str,
        type_notification: str,
        titre: str,
        message: str
    ) -> Notification:
        """
        Crée une nouvelle notification et l'envoie via WebSocket
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur destinataire
            type_notification: Type (assignation, paiement, alerte, etc.)
            titre: Titre de la notification
            message: Message de la notification
            
        Returns:
            Notification créée
        """
        notification = Notification(
            user_id=user_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            est_lue=False
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Envoyer via WebSocket
        from app.core.websocket_manager import manager
        await manager.send_notification(user_id, {
            "id": notification.id,
            "type_notification": notification.type_notification,
            "titre": notification.titre,
            "message": notification.message,
            "est_lue": notification.est_lue,
            "created_at": notification.created_at.isoformat()
        })
        
        return notification
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        type_notification: str,
        titre: str,
        message: str
    ) -> Notification:
        """
        Crée une nouvelle notification (version synchrone)
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur destinataire
            type_notification: Type (assignation, paiement, alerte, etc.)
            titre: Titre de la notification
            message: Message de la notification
            
        Returns:
            Notification créée
        """
        notification = Notification(
            user_id=user_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            est_lue=False
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Essayer d'envoyer via WebSocket (non-bloquant)
        try:
            from app.core.websocket_manager import manager
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(manager.send_notification(user_id, {
                    "id": notification.id,
                    "type_notification": notification.type_notification,
                    "titre": notification.titre,
                    "message": notification.message,
                    "est_lue": notification.est_lue,
                    "created_at": notification.created_at.isoformat()
                }))
        except Exception as e:
            print(f"Erreur envoi WebSocket: {e}")
        
        return notification
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """
        Récupère les notifications d'un utilisateur
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            unread_only: Si True, ne retourne que les non lues
            limit: Nombre maximum de notifications
            
        Returns:
            Liste de notifications
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.est_lue == False)
        
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        
        return list(db.scalars(query).all())
    
    @staticmethod
    def mark_as_read(db: Session, notification_id: str) -> Optional[Notification]:
        """
        Marque une notification comme lue
        
        Args:
            db: Session de base de données
            notification_id: ID de la notification
            
        Returns:
            Notification mise à jour ou None
        """
        notification = db.get(Notification, notification_id)
        
        if notification:
            notification.est_lue = True
            db.commit()
            db.refresh(notification)
        
        return notification
    
    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        """
        Marque toutes les notifications d'un utilisateur comme lues
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            
        Returns:
            Nombre de notifications mises à jour
        """
        notifications = db.scalars(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.est_lue == False
                )
            )
        ).all()
        
        count = 0
        for notification in notifications:
            notification.est_lue = True
            count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def get_unread_count(db: Session, user_id: str) -> int:
        """
        Compte les notifications non lues d'un utilisateur
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            
        Returns:
            Nombre de notifications non lues
        """
        count = db.scalar(
            select(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.est_lue == False
                )
            )
            .count()
        )
        
        return count or 0
    
    @staticmethod
    def delete_notification(db: Session, notification_id: str) -> bool:
        """
        Supprime une notification
        
        Args:
            db: Session de base de données
            notification_id: ID de la notification
            
        Returns:
            True si supprimée, False sinon
        """
        notification = db.get(Notification, notification_id)
        
        if notification:
            db.delete(notification)
            db.commit()
            return True
        
        return False
    
    # Méthodes utilitaires pour créer des notifications spécifiques
    
    @staticmethod
    def notify_patient_assignment(db: Session, medecin_id: str, patient_name: str) -> Notification:
        """Notifie un médecin qu'un patient lui a été assigné"""
        return NotificationService.create_notification(
            db=db,
            user_id=medecin_id,
            type_notification="assignation",
            titre="Nouveau patient assigné",
            message=f"Le patient {patient_name} vous a été assigné."
        )
    
    @staticmethod
    def notify_payment_received(db: Session, caissier_id: str, montant: float, facture_numero: str) -> Notification:
        """Notifie qu'un paiement a été reçu"""
        return NotificationService.create_notification(
            db=db,
            user_id=caissier_id,
            type_notification="paiement",
            titre="Paiement reçu",
            message=f"Paiement de {montant:,.0f} FCFA reçu pour la facture {facture_numero}."
        )
    
    @staticmethod
    def notify_hospitalization_alert(db: Session, user_id: str, patient_name: str, message: str) -> Notification:
        """Notifie une alerte d'hospitalisation"""
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type_notification="alerte",
            titre="Alerte hospitalisation",
            message=f"Patient {patient_name}: {message}"
        )
    
    @staticmethod
    def notify_insurance_claim(db: Session, user_id: str, montant: float, assurance_name: str) -> Notification:
        """Notifie une nouvelle créance d'assurance"""
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type_notification="assurance",
            titre="Nouvelle créance d'assurance",
            message=f"Créance de {montant:,.0f} FCFA pour {assurance_name}."
        )
