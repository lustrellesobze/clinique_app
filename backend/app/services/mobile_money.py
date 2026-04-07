"""
Service Mobile Money pour MTN MoMo et Orange Money
Gère les paiements et envoie des notifications WebSocket
"""
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.invoice import Facture, FactureStatut
from app.models.user import User
from app.services.notification_service import NotificationService
from app.core.websocket_manager import manager


class MobileMoneyProvider:
    """Énumération des fournisseurs Mobile Money"""
    MTN_MOMO = "mtn_momo"
    ORANGE_MONEY = "orange_money"


class MobileMoneyStatus:
    """Statuts des transactions Mobile Money"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MobileMoneyService:
    """Service pour gérer les paiements Mobile Money"""
    
    # Simulation de base de données des transactions en mémoire
    # En production, utiliser une vraie table en base de données
    _transactions: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def initiate_payment(
        db: Session,
        facture_id: str,
        montant: float,
        telephone: str,
        provider: str,
        caissier_id: str
    ) -> Dict[str, Any]:
        """
        Initie un paiement Mobile Money
        
        Args:
            db: Session de base de données
            facture_id: ID de la facture
            montant: Montant à payer
            telephone: Numéro de téléphone du payeur
            provider: Fournisseur (mtn_momo ou orange_money)
            caissier_id: ID du caissier qui initie le paiement
            
        Returns:
            Dictionnaire avec les détails de la transaction
        """
        # Vérifier que la facture existe
        facture = db.get(Facture, facture_id)
        if not facture:
            raise ValueError("Facture non trouvée")
        
        # Générer un ID de transaction unique
        transaction_id = str(uuid.uuid4())
        
        # Créer la transaction
        transaction = {
            "transaction_id": transaction_id,
            "facture_id": facture_id,
            "montant": montant,
            "telephone": telephone,
            "provider": provider,
            "caissier_id": caissier_id,
            "status": MobileMoneyStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Stocker la transaction
        MobileMoneyService._transactions[transaction_id] = transaction
        
        # En production, ici on appellerait l'API du fournisseur Mobile Money
        # Pour la démo, on simule une réponse immédiate
        
        return {
            "transaction_id": transaction_id,
            "status": MobileMoneyStatus.PENDING,
            "message": f"Paiement {provider.upper()} initié. En attente de confirmation du client.",
            "montant": montant,
            "telephone": telephone
        }
    
    @staticmethod
    async def confirm_payment(
        db: Session,
        transaction_id: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirme ou rejette un paiement Mobile Money
        Envoie une notification WebSocket au caissier
        
        Args:
            db: Session de base de données
            transaction_id: ID de la transaction
            success: True si paiement réussi, False sinon
            error_message: Message d'erreur si échec
            
        Returns:
            Dictionnaire avec le résultat
        """
        # Récupérer la transaction
        transaction = MobileMoneyService._transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction non trouvée")
        
        # Mettre à jour le statut
        new_status = MobileMoneyStatus.SUCCESS if success else MobileMoneyStatus.FAILED
        transaction["status"] = new_status
        transaction["updated_at"] = datetime.now().isoformat()
        
        if error_message:
            transaction["error_message"] = error_message
        
        # Récupérer la facture
        facture = db.get(Facture, transaction["facture_id"])
        if not facture:
            raise ValueError("Facture non trouvée")
        
        # Si paiement réussi, mettre à jour la facture
        if success:
            montant_paye = Decimal(str(transaction["montant"]))
            facture.montant_regle = float(Decimal(str(facture.montant_regle)) + montant_paye)
            
            # Mettre à jour le statut de la facture
            if facture.montant_regle >= facture.montant_total:
                facture.statut = FactureStatut.payee
            elif facture.montant_regle > 0:
                facture.statut = FactureStatut.partielle
            
            db.commit()
            db.refresh(facture)
        
        # Créer une notification pour le caissier
        caissier_id = transaction["caissier_id"]
        
        if success:
            notification = NotificationService.create_notification(
                db=db,
                user_id=caissier_id,
                type_notification="paiement",
                titre="Paiement Mobile Money confirmé",
                message=f"Paiement de {transaction['montant']:,.0f} FCFA confirmé via {transaction['provider'].upper()} pour la facture {facture.numero_facture}."
            )
        else:
            notification = NotificationService.create_notification(
                db=db,
                user_id=caissier_id,
                type_notification="alerte",
                titre="Paiement Mobile Money échoué",
                message=f"Échec du paiement de {transaction['montant']:,.0f} FCFA via {transaction['provider'].upper()}. Raison: {error_message or 'Erreur inconnue'}"
            )
        
        # Envoyer notification WebSocket
        await manager.send_notification(caissier_id, {
            "id": notification.id,
            "type_notification": notification.type_notification,
            "titre": notification.titre,
            "message": notification.message,
            "est_lue": notification.est_lue,
            "created_at": notification.created_at.isoformat(),
            "transaction_id": transaction_id,
            "facture_numero": facture.numero_facture,
            "montant": transaction["montant"],
            "status": new_status
        })
        
        return {
            "transaction_id": transaction_id,
            "status": new_status,
            "facture_id": facture.id,
            "facture_numero": facture.numero_facture,
            "montant": transaction["montant"],
            "message": "Paiement confirmé avec succès" if success else f"Paiement échoué: {error_message}"
        }
    
    @staticmethod
    def get_transaction_status(transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le statut d'une transaction
        
        Args:
            transaction_id: ID de la transaction
            
        Returns:
            Dictionnaire avec les détails de la transaction ou None
        """
        return MobileMoneyService._transactions.get(transaction_id)
    
    @staticmethod
    def simulate_mtn_callback(
        db: Session,
        transaction_id: str,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Simule un callback MTN MoMo (pour tests)
        
        Args:
            db: Session de base de données
            transaction_id: ID de la transaction
            success: True pour simuler un succès
            
        Returns:
            Résultat de la confirmation
        """
        # En production, cette fonction serait appelée par l'API MTN
        # Ici on simule le callback
        
        error_message = None if success else "Client a annulé le paiement"
        
        # Utiliser asyncio pour appeler la fonction async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            MobileMoneyService.confirm_payment(db, transaction_id, success, error_message)
        )
        loop.close()
        
        return result
    
    @staticmethod
    def simulate_orange_callback(
        db: Session,
        transaction_id: str,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Simule un callback Orange Money (pour tests)
        
        Args:
            db: Session de base de données
            transaction_id: ID de la transaction
            success: True pour simuler un succès
            
        Returns:
            Résultat de la confirmation
        """
        # En production, cette fonction serait appelée par l'API Orange Money
        # Ici on simule le callback
        
        error_message = None if success else "Solde insuffisant"
        
        # Utiliser asyncio pour appeler la fonction async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            MobileMoneyService.confirm_payment(db, transaction_id, success, error_message)
        )
        loop.close()
        
        return result
