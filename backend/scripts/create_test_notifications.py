"""
Crée des notifications de test pour tester le système de notifications
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.services.notification_service import NotificationService


def main() -> None:
    db: Session = SessionLocal()
    
    try:
        # Récupérer tous les utilisateurs
        users = db.scalars(select(User)).all()
        
        if not users:
            print("Aucun utilisateur trouvé. Exécutez d'abord create_test_user.py")
            return
        
        notifications_created = 0
        
        # Créer des notifications pour chaque utilisateur
        for user in users:
            # Notification d'assignation
            NotificationService.create_notification(
                db=db,
                user_id=user.id,
                type_notification="assignation",
                titre="Nouveau patient assigné",
                message=f"Le patient Jean Dupont vous a été assigné pour consultation."
            )
            notifications_created += 1
            
            # Notification de paiement
            NotificationService.create_notification(
                db=db,
                user_id=user.id,
                type_notification="paiement",
                titre="Paiement reçu",
                message="Paiement de 50,000 FCFA reçu pour la facture FAC-2026-001."
            )
            notifications_created += 1
            
            # Notification d'alerte
            NotificationService.create_notification(
                db=db,
                user_id=user.id,
                type_notification="alerte",
                titre="Alerte hospitalisation",
                message="Patient Marie Martin: Fin d'hospitalisation prévue demain."
            )
            notifications_created += 1
            
            print(f"✅ 3 notifications créées pour {user.nom} {user.prenom} ({user.email})")
        
        print(f"\n✅ Total: {notifications_created} notifications créées avec succès!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
