"""
Crée des factures de test avec des parts d'assurance pour tester le module Assurances
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.insurance import Insurance
from app.models.invoice import Facture, FactureStatut


def main() -> None:
    db: Session = SessionLocal()
    
    try:
        # Récupérer les assurances existantes
        insurances = db.scalars(select(Insurance)).all()
        if not insurances:
            print("Aucune assurance trouvée. Exécutez d'abord create_test_insurances.py")
            return
        
        # Récupérer les patients existants
        patients = db.scalars(select(Patient)).all()
        if not patients:
            print("Aucun patient trouvé. Exécutez d'abord create_test_patient.py")
            return
        
        # Assigner des assurances à quelques patients
        for i, patient in enumerate(patients[:3]):  # 3 premiers patients
            if not patient.assurance_id:
                patient.assurance_id = insurances[i % len(insurances)].id
                print(f"Assurance assignée au patient {patient.nom} {patient.prenom}")
        
        db.commit()
        
        # Créer des factures avec parts d'assurance
        factures_created = 0
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        for i, patient in enumerate(patients[:3]):
            if patient.assurance_id:
                insurance = db.get(Insurance, patient.assurance_id)
                
                # Créer 2 factures par patient
                for j in range(2):
                    montant_total = Decimal(50000 + (i * 10000) + (j * 5000))
                    
                    # Calculer la part assurance (selon le taux de couverture)
                    taux_couverture = Decimal(insurance.taux_couverture)
                    part_assurance = montant_total * (taux_couverture / 100)
                    part_patient = montant_total - part_assurance
                    
                    facture = Facture(
                        id=str(uuid.uuid4()),
                        numero_facture=f"FAC-TEST-{timestamp}-{factures_created + 1:04d}",
                        patient_id=patient.id,
                        montant_total=float(montant_total),
                        part_assurance=float(part_assurance),
                        part_patient=float(part_patient),
                        statut=FactureStatut.en_attente,
                        created_at=datetime.now() - timedelta(days=i * 3 + j)
                    )
                    
                    db.add(facture)
                    factures_created += 1
                    print(f"Facture créée: {facture.numero_facture} - Total: {montant_total} FCFA - Part assurance: {part_assurance} FCFA")
        
        db.commit()
        print(f"\n✅ {factures_created} factures avec créances d'assurance créées avec succès!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
