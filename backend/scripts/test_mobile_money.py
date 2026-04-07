"""
Script de test pour simuler un paiement Mobile Money
Démontre le flux complet avec notification WebSocket
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.invoice import Facture
from app.models.user import User, UserRole
from app.services.mobile_money import MobileMoneyService, MobileMoneyProvider


def test_mobile_money_payment():
    """Test complet d'un paiement Mobile Money"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 80)
        print("🧪 TEST PAIEMENT MOBILE MONEY")
        print("=" * 80)
        
        # 1. Récupérer un caissier
        caissier = db.scalar(
            select(User).where(User.role == UserRole.caissier_central).limit(1)
        )
        
        if not caissier:
            print("❌ Aucun caissier trouvé. Exécutez d'abord seed_all_data.py")
            return
        
        print(f"\n👤 Caissier: {caissier.prenom} {caissier.nom} ({caissier.email})")
        
        # 2. Récupérer une facture en attente
        facture = db.scalar(
            select(Facture).where(Facture.statut == "en_attente").limit(1)
        )
        
        if not facture:
            print("❌ Aucune facture en attente trouvée")
            return
        
        print(f"\n💰 Facture: {facture.numero_facture}")
        print(f"   Montant total: {facture.montant_total:,.0f} FCFA")
        print(f"   Montant réglé: {facture.montant_regle:,.0f} FCFA")
        print(f"   Reste à payer: {facture.montant_total - facture.montant_regle:,.0f} FCFA")
        
        # 3. Initier un paiement MTN MoMo
        montant_a_payer = facture.montant_total - facture.montant_regle
        telephone = "+237 670 00 00 01"
        
        print(f"\n📱 Initiation paiement MTN MoMo...")
        print(f"   Téléphone: {telephone}")
        print(f"   Montant: {montant_a_payer:,.0f} FCFA")
        
        result = MobileMoneyService.initiate_payment(
            db=db,
            facture_id=facture.id,
            montant=float(montant_a_payer),
            telephone=telephone,
            provider=MobileMoneyProvider.MTN_MOMO,
            caissier_id=caissier.id
        )
        
        transaction_id = result["transaction_id"]
        print(f"\n✅ Paiement initié!")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Statut: {result['status']}")
        print(f"   Message: {result['message']}")
        
        # 4. Simuler l'attente du client (3 secondes)
        print(f"\n⏳ En attente de confirmation du client...")
        time.sleep(3)
        
        # 5. Simuler la confirmation du paiement (succès)
        print(f"\n✅ Simulation de confirmation du paiement...")
        
        confirmation = MobileMoneyService.simulate_mtn_callback(
            db=db,
            transaction_id=transaction_id,
            success=True
        )
        
        print(f"\n🎉 PAIEMENT CONFIRMÉ!")
        print(f"   Transaction ID: {confirmation['transaction_id']}")
        print(f"   Statut: {confirmation['status']}")
        print(f"   Facture: {confirmation['facture_numero']}")
        print(f"   Montant: {confirmation['montant']:,.0f} FCFA")
        print(f"   Message: {confirmation['message']}")
        
        # 6. Vérifier la mise à jour de la facture
        db.refresh(facture)
        print(f"\n📊 État de la facture après paiement:")
        print(f"   Montant total: {facture.montant_total:,.0f} FCFA")
        print(f"   Montant réglé: {facture.montant_regle:,.0f} FCFA")
        print(f"   Statut: {facture.statut}")
        
        # 7. Test d'un paiement échoué
        print(f"\n" + "=" * 80)
        print(f"🧪 TEST PAIEMENT ÉCHOUÉ")
        print("=" * 80)
        
        # Récupérer une autre facture
        facture2 = db.scalar(
            select(Facture).where(
                Facture.statut == "en_attente",
                Facture.id != facture.id
            ).limit(1)
        )
        
        if facture2:
            print(f"\n💰 Facture: {facture2.numero_facture}")
            
            # Initier paiement Orange Money
            result2 = MobileMoneyService.initiate_payment(
                db=db,
                facture_id=facture2.id,
                montant=20000.0,
                telephone="+237 690 00 00 01",
                provider=MobileMoneyProvider.ORANGE_MONEY,
                caissier_id=caissier.id
            )
            
            transaction_id2 = result2["transaction_id"]
            print(f"\n📱 Paiement Orange Money initié: {transaction_id2}")
            
            time.sleep(2)
            
            # Simuler un échec
            print(f"\n❌ Simulation d'échec du paiement...")
            
            confirmation2 = MobileMoneyService.simulate_orange_callback(
                db=db,
                transaction_id=transaction_id2,
                success=False
            )
            
            print(f"\n⚠️  PAIEMENT ÉCHOUÉ!")
            print(f"   Transaction ID: {confirmation2['transaction_id']}")
            print(f"   Statut: {confirmation2['status']}")
            print(f"   Message: {confirmation2['message']}")
        
        print(f"\n" + "=" * 80)
        print(f"✅ TESTS TERMINÉS AVEC SUCCÈS!")
        print("=" * 80)
        print(f"\n📝 Note: Les notifications WebSocket ont été envoyées au caissier")
        print(f"   Pour les voir en temps réel, connectez-vous via WebSocket:")
        print(f"   ws://localhost:8000/api/ws/notifications?token=<jwt_token>")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_mobile_money_payment()
