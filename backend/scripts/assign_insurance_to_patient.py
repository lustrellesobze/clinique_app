"""
Assigne une assurance à un patient de test
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.insurance import Insurance


def main() -> None:
    db: Session = SessionLocal()
    
    try:
        # Récupérer un patient
        patient = db.scalars(select(Patient).limit(1)).first()
        if not patient:
            print("❌ Aucun patient trouvé")
            return
        
        # Récupérer une assurance (SAHAM par exemple)
        insurance = db.scalars(
            select(Insurance).where(Insurance.nom_compagnie == "SAHAM Assurance")
        ).first()
        
        if not insurance:
            print("❌ Assurance SAHAM non trouvée")
            return
        
        # Assigner l'assurance au patient
        patient.assurance_id = insurance.id
        patient.numero_police_assurance = "POL-2026-001234"
        
        db.commit()
        
        print("✅ Assurance assignée avec succès!")
        print(f"   Patient: {patient.nom} {patient.prenom}")
        print(f"   Assurance: {insurance.nom_compagnie}")
        print(f"   Taux de couverture: {insurance.taux_couverture}%")
        print(f"   Plafond annuel: {insurance.plafond_annuel_fcfa:,.0f} FCFA" if insurance.plafond_annuel_fcfa else "   Plafond annuel: Illimité")
        print(f"   N° Police: {patient.numero_police_assurance}")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
