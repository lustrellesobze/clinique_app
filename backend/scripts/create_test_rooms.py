"""
Script pour créer des chambres de test
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from app.database import SessionLocal
from app.models import Room

def create_test_rooms():
    db = SessionLocal()
    try:
        # Vérifier si des chambres existent déjà
        existing = db.query(Room).first()
        if existing:
            print("✓ Chambres existantes trouvées")
            return
        
        # Créer des chambres de test
        rooms = [
            # Chambres communes
            Room(numero="C01", type_chambre="commune", tarif_journalier_fcfa=Decimal("15000"), 
                 description="Chambre commune - 4 lits", est_disponible=True),
            Room(numero="C02", type_chambre="commune", tarif_journalier_fcfa=Decimal("15000"), 
                 description="Chambre commune - 4 lits", est_disponible=True),
            Room(numero="C03", type_chambre="commune", tarif_journalier_fcfa=Decimal("15000"), 
                 description="Chambre commune - 4 lits", est_disponible=True),
            
            # Chambres individuelles
            Room(numero="I01", type_chambre="individuelle", tarif_journalier_fcfa=Decimal("25000"), 
                 description="Chambre individuelle - 1 lit", est_disponible=True),
            Room(numero="I02", type_chambre="individuelle", tarif_journalier_fcfa=Decimal("25000"), 
                 description="Chambre individuelle - 1 lit", est_disponible=True),
            Room(numero="I03", type_chambre="individuelle", tarif_journalier_fcfa=Decimal("25000"), 
                 description="Chambre individuelle - 1 lit", est_disponible=True),
            Room(numero="I04", type_chambre="individuelle", tarif_journalier_fcfa=Decimal("25000"), 
                 description="Chambre individuelle - 1 lit", est_disponible=True),
            
            # Chambres VIP
            Room(numero="V01", type_chambre="vip", tarif_journalier_fcfa=Decimal("50000"), 
                 description="Chambre VIP - Suite avec salle de bain privée", est_disponible=True),
            Room(numero="V02", type_chambre="vip", tarif_journalier_fcfa=Decimal("50000"), 
                 description="Chambre VIP - Suite avec salle de bain privée", est_disponible=True),
        ]
        
        for room in rooms:
            db.add(room)
        
        db.commit()
        print(f"✓ {len(rooms)} chambres créées avec succès!")
        print("  - 3 chambres communes (15 000 FCFA/jour)")
        print("  - 4 chambres individuelles (25 000 FCFA/jour)")
        print("  - 2 chambres VIP (50 000 FCFA/jour)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Erreur: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_rooms()
