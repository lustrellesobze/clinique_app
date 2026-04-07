"""
Script de test interactif pour l'application Clinique
Permet de tester facilement toutes les fonctionnalités
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.invoice import Facture
from app.models.notification import Notification
from app.services.mobile_money import MobileMoneyService, MobileMoneyProvider
from app.services.notification_service import NotificationService


def print_header(title):
    """Affiche un en-tête formaté"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_menu(options):
    """Affiche un menu"""
    print("\n📋 Menu:")
    for key, value in options.items():
        print(f"  {key}. {value}")
    print("  0. Quitter")


def test_users(db: Session):
    """Test 1: Afficher les utilisateurs"""
    print_header("👥 UTILISATEURS")
    
    users = db.scalars(select(User)).all()
    
    if not users:
        print("❌ Aucun utilisateur trouvé")
        print("💡 Exécutez: python scripts/seed_all_data.py")
        return
    
    print(f"\n✅ {len(users)} utilisateurs trouvés:\n")
    
    for user in users:
        print(f"  📧 {user.email:30} | 👤 {user.prenom} {user.nom:20} | 🎭 {user.role.value}")
    
    print(f"\n💡 Identifiants de test: <email> / demo123")


def test_invoices(db: Session):
    """Test 2: Afficher les factures"""
    print_header("💰 FACTURES")
    
    factures = db.scalars(select(Facture).limit(10)).all()
    
    if not factures:
        print("❌ Aucune facture trouvée")
        return
    
    print(f"\n✅ {len(factures)} factures (10 premières):\n")
    
    for facture in factures:
        reste = facture.montant_total - facture.montant_regle
        print(f"  📄 {facture.numero_facture:30} | 💵 {facture.montant_total:>10,.0f} FCFA | "
              f"✅ {facture.montant_regle:>10,.0f} FCFA | ⏳ {reste:>10,.0f} FCFA | 📊 {facture.statut.value}")


def test_notifications(db: Session):
    """Test 3: Afficher les notifications"""
    print_header("🔔 NOTIFICATIONS")
    
    notifications = db.scalars(select(Notification).limit(10)).all()
    
    if not notifications:
        print("❌ Aucune notification trouvée")
        return
    
    print(f"\n✅ {len(notifications)} notifications (10 premières):\n")
    
    for notif in notifications:
        status = "📭 Non lue" if not notif.est_lue else "✅ Lue"
        icon = {"paiement": "💰", "assignation": "👤", "alerte": "⚠️", "assurance": "🏥"}.get(notif.type_notification, "📢")
        print(f"  {icon} {notif.titre:40} | {status} | {notif.created_at.strftime('%Y-%m-%d %H:%M')}")


def test_mobile_money_simple(db: Session):
    """Test 4: Test Mobile Money simplifié"""
    print_header("📱 TEST MOBILE MONEY")
    
    # Récupérer un caissier
    caissier = db.scalar(select(User).where(User.role == UserRole.caissier_central).limit(1))
    
    if not caissier:
        print("❌ Aucun caissier trouvé")
        return
    
    # Récupérer une facture en attente
    facture = db.scalar(select(Facture).where(Facture.statut == "en_attente").limit(1))
    
    if not facture:
        print("❌ Aucune facture en attente trouvée")
        return
    
    print(f"\n👤 Caissier: {caissier.prenom} {caissier.nom}")
    print(f"💰 Facture: {facture.numero_facture}")
    print(f"💵 Montant à payer: {facture.montant_total - facture.montant_regle:,.0f} FCFA")
    
    print("\n🔄 Initiation du paiement MTN MoMo...")
    
    montant = float(facture.montant_total - facture.montant_regle)
    
    result = MobileMoneyService.initiate_payment(
        db=db,
        facture_id=facture.id,
        montant=montant,
        telephone="+237 670 00 00 01",
        provider=MobileMoneyProvider.MTN_MOMO,
        caissier_id=caissier.id
    )
    
    transaction_id = result["transaction_id"]
    print(f"\n✅ Paiement initié!")
    print(f"   Transaction ID: {transaction_id}")
    print(f"   Statut: {result['status']}")
    
    print("\n⏳ Simulation de la confirmation...")
    
    confirmation = MobileMoneyService.simulate_mtn_callback(
        db=db,
        transaction_id=transaction_id,
        success=True
    )
    
    print(f"\n🎉 PAIEMENT CONFIRMÉ!")
    print(f"   Statut: {confirmation['status']}")
    print(f"   Message: {confirmation['message']}")
    
    # Vérifier la facture
    db.refresh(facture)
    print(f"\n📊 État de la facture:")
    print(f"   Montant réglé: {facture.montant_regle:,.0f} FCFA")
    print(f"   Statut: {facture.statut.value}")
    
    print(f"\n✅ Test terminé avec succès!")


def create_test_notification(db: Session):
    """Test 5: Créer une notification de test"""
    print_header("🔔 CRÉER UNE NOTIFICATION")
    
    users = db.scalars(select(User).limit(5)).all()
    
    if not users:
        print("❌ Aucun utilisateur trouvé")
        return
    
    print("\n👥 Utilisateurs disponibles:")
    for i, user in enumerate(users, 1):
        print(f"  {i}. {user.prenom} {user.nom} ({user.email})")
    
    try:
        choice = int(input("\n👉 Choisir un utilisateur (numéro): "))
        if choice < 1 or choice > len(users):
            print("❌ Choix invalide")
            return
        
        user = users[choice - 1]
        
        print("\n📝 Types de notification:")
        print("  1. Paiement")
        print("  2. Assignation")
        print("  3. Alerte")
        print("  4. Assurance")
        
        type_choice = int(input("\n👉 Choisir un type (numéro): "))
        types = ["paiement", "assignation", "alerte", "assurance"]
        
        if type_choice < 1 or type_choice > 4:
            print("❌ Choix invalide")
            return
        
        type_notif = types[type_choice - 1]
        
        titre = input("\n📌 Titre de la notification: ")
        message = input("💬 Message de la notification: ")
        
        notification = NotificationService.create_notification(
            db=db,
            user_id=user.id,
            type_notification=type_notif,
            titre=titre,
            message=message
        )
        
        print(f"\n✅ Notification créée avec succès!")
        print(f"   ID: {notification.id}")
        print(f"   Pour: {user.prenom} {user.nom}")
        print(f"   Type: {type_notif}")
        
    except ValueError:
        print("❌ Entrée invalide")
    except KeyboardInterrupt:
        print("\n\n❌ Annulé")


def show_api_info():
    """Test 6: Afficher les informations API"""
    print_header("🌐 INFORMATIONS API")
    
    print("\n📍 URLs:")
    print("  Backend API:  http://127.0.0.1:8000")
    print("  Swagger Docs: http://127.0.0.1:8000/docs")
    print("  Frontend:     http://localhost:4200")
    
    print("\n🔑 Authentification:")
    print("  POST /api/auth/login")
    print("  Body: {\"email\": \"caissier@demo.cm\", \"password\": \"demo123\"}")
    
    print("\n🔔 Notifications:")
    print("  GET    /api/notifications/")
    print("  GET    /api/notifications/unread-count")
    print("  PUT    /api/notifications/{id}/read")
    print("  DELETE /api/notifications/{id}")
    
    print("\n💰 Mobile Money:")
    print("  POST /api/payments/mobile-money/initiate")
    print("  GET  /api/payments/mobile-money/status/{transaction_id}")
    print("  POST /api/payments/mobile-money/callback/mtn")
    print("  POST /api/payments/mobile-money/callback/orange")
    
    print("\n📄 PDF:")
    print("  GET /api/invoices/{id}/pdf")
    print("  GET /api/prescriptions/{id}/pdf")
    
    print("\n🔌 WebSocket:")
    print("  ws://127.0.0.1:8000/api/ws/notifications?token=<jwt_token>")


def main():
    """Fonction principale"""
    print_header("🏥 TEST INTERACTIF - APPLICATION CLINIQUE")
    
    print("\n💡 Ce script permet de tester facilement toutes les fonctionnalités")
    print("   Assurez-vous que le backend est démarré sur le port 8000")
    
    db: Session = SessionLocal()
    
    try:
        while True:
            options = {
                "1": "Afficher les utilisateurs",
                "2": "Afficher les factures",
                "3": "Afficher les notifications",
                "4": "Test Mobile Money (complet)",
                "5": "Créer une notification de test",
                "6": "Afficher les informations API"
            }
            
            print_menu(options)
            
            try:
                choice = input("\n👉 Votre choix: ").strip()
                
                if choice == "0":
                    print("\n👋 Au revoir!")
                    break
                elif choice == "1":
                    test_users(db)
                elif choice == "2":
                    test_invoices(db)
                elif choice == "3":
                    test_notifications(db)
                elif choice == "4":
                    test_mobile_money_simple(db)
                elif choice == "5":
                    create_test_notification(db)
                elif choice == "6":
                    show_api_info()
                else:
                    print("❌ Choix invalide")
                
                input("\n⏎ Appuyez sur Entrée pour continuer...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                import traceback
                traceback.print_exc()
                input("\n⏎ Appuyez sur Entrée pour continuer...")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
