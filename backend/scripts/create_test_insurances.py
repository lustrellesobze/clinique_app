"""
Crée des compagnies d'assurance de test
"""
import sys
import json
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.insurance import Insurance


# Compagnies d'assurance de test
TEST_INSURANCES = [
    {
        "nom_compagnie": "SAHAM Assurance",
        "taux_couverture": 80,
        "plafond_annuel_fcfa": Decimal("5000000"),  # 5 millions FCFA
        "exclusions": json.dumps(["dentaire", "optique"]),
        "est_active": True
    },
    {
        "nom_compagnie": "AXA Cameroun",
        "taux_couverture": 70,
        "plafond_annuel_fcfa": Decimal("3000000"),  # 3 millions FCFA
        "exclusions": json.dumps(["esthetique"]),
        "est_active": True
    },
    {
        "nom_compagnie": "ACTIVA Assurance",
        "taux_couverture": 90,
        "plafond_annuel_fcfa": Decimal("10000000"),  # 10 millions FCFA
        "exclusions": json.dumps([]),  # Aucune exclusion
        "est_active": True
    },
    {
        "nom_compagnie": "NSIA Assurance",
        "taux_couverture": 75,
        "plafond_annuel_fcfa": Decimal("4000000"),  # 4 millions FCFA
        "exclusions": json.dumps(["dentaire"]),
        "est_active": True
    },
    {
        "nom_compagnie": "SUNU Assurances",
        "taux_couverture": 85,
        "plafond_annuel_fcfa": None,  # Pas de plafond
        "exclusions": json.dumps(["optique", "esthetique"]),
        "est_active": True
    }
]


def main() -> None:
    db: Session = SessionLocal()
    created = 0
    skipped = 0
    
    try:
        for insurance_data in TEST_INSURANCES:
            # Vérifier si existe déjà
            existing = db.scalars(
                select(Insurance).where(
                    Insurance.nom_compagnie == insurance_data["nom_compagnie"]
                )
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Créer la compagnie
            insurance = Insurance(**insurance_data)
            db.add(insurance)
            created += 1
        
        db.commit()
        
        print("=" * 60)
        print("COMPAGNIES D'ASSURANCE DE TEST")
        print("=" * 60)
        print(f"Créées: {created}")
        print(f"Déjà existantes (ignorées): {skipped}")
        print()
        
        if created > 0:
            print("Compagnies créées:")
            for insurance_data in TEST_INSURANCES:
                print(f"  - {insurance_data['nom_compagnie']}")
                print(f"    Taux: {insurance_data['taux_couverture']}%")
                if insurance_data['plafond_annuel_fcfa']:
                    print(f"    Plafond: {insurance_data['plafond_annuel_fcfa']:,.0f} FCFA")
                else:
                    print(f"    Plafond: Illimité")
                exclusions = json.loads(insurance_data['exclusions'])
                if exclusions:
                    print(f"    Exclusions: {', '.join(exclusions)}")
                else:
                    print(f"    Exclusions: Aucune")
                print()
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
