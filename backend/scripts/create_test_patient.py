"""
Script pour créer un patient de test
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from app.database import SessionLocal
from app.models import Patient

def create_test_patient():
    db = SessionLocal()
    try:
        # Vérifier si un patient existe déjà
        existing = db.query(Patient).first()
        if existing:
            print(f"✓ Patient existant trouvé: {existing.nom} {existing.prenom}")
            return
        
        # Créer un patient de test
        patient = Patient(
            code_patient="P-2026-00001",
            nom="DUPONT",
            prenom="Jean",
            date_naissance=date(1985, 5, 15),
            sexe="M",
            telephone="+237 690 00 00 00",
            email="jean.dupont@test.cm"
        )
        db.add(patient)
        db.commit()
        print(f"✓ Patient de test créé: {patient.nom} {patient.prenom} ({patient.code_patient})")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Erreur: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_patient()
