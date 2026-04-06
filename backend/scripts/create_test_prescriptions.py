"""
Script pour créer des prescriptions de test
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime
from app.database import SessionLocal
from app.models import Prescription, PrescriptionItem, Patient, User

def create_test_prescriptions():
    db = SessionLocal()
    try:
        # Récupérer un patient et un médecin
        patient = db.query(Patient).first()
        medecin = db.query(User).filter(User.role == "medecin").first()
        
        if not patient or not medecin:
            print("❌ Aucun patient ou médecin trouvé. Créez d'abord des utilisateurs.")
            return
        
        # Créer une prescription laboratoire
        prescription_labo = Prescription(
            patient_id=patient.id,
            medecin_id=medecin.id,
            type_prescription="labo",
            statut="transferee",
            notes="Bilan sanguin complet"
        )
        db.add(prescription_labo)
        db.flush()
        
        # Ajouter des items
        items_labo = [
            PrescriptionItem(
                prescription_id=prescription_labo.id,
                nom_item="Numération Formule Sanguine (NFS)",
                description="Analyse complète du sang",
                quantite=1,
                prix_unitaire=Decimal("5000")
            ),
            PrescriptionItem(
                prescription_id=prescription_labo.id,
                nom_item="Glycémie à jeun",
                description="Dosage du glucose sanguin",
                quantite=1,
                prix_unitaire=Decimal("2000")
            ),
            PrescriptionItem(
                prescription_id=prescription_labo.id,
                nom_item="Créatininémie",
                description="Fonction rénale",
                quantite=1,
                prix_unitaire=Decimal("3000")
            )
        ]
        
        for item in items_labo:
            db.add(item)
        
        # Créer une prescription imagerie
        prescription_imagerie = Prescription(
            patient_id=patient.id,
            medecin_id=medecin.id,
            type_prescription="imagerie",
            statut="transferee",
            notes="Radiographie thorax"
        )
        db.add(prescription_imagerie)
        db.flush()
        
        # Ajouter des items
        items_imagerie = [
            PrescriptionItem(
                prescription_id=prescription_imagerie.id,
                nom_item="Radiographie thorax face",
                description="Cliché face",
                quantite=1,
                prix_unitaire=Decimal("8000")
            ),
            PrescriptionItem(
                prescription_id=prescription_imagerie.id,
                nom_item="Radiographie thorax profil",
                description="Cliché profil",
                quantite=1,
                prix_unitaire=Decimal("8000")
            )
        ]
        
        for item in items_imagerie:
            db.add(item)
        
        db.commit()
        print("✓ Prescriptions de test créées avec succès!")
        print(f"  - Prescription labo: {prescription_labo.id} (3 examens, total: 10000 FCFA)")
        print(f"  - Prescription imagerie: {prescription_imagerie.id} (2 examens, total: 16000 FCFA)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Erreur: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_prescriptions()
