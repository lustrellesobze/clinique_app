"""
Test du calcul de couverture d'assurance
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.services.insurance_service import InsuranceService


def main() -> None:
    db: Session = SessionLocal()
    
    try:
        # Récupérer le patient avec assurance
        patient = db.scalars(
            select(Patient).where(Patient.assurance_id.isnot(None)).limit(1)
        ).first()
        
        if not patient:
            print("❌ Aucun patient assuré trouvé")
            return
        
        print("=" * 60)
        print("TEST DE CALCUL DE COUVERTURE D'ASSURANCE")
        print("=" * 60)
        print(f"Patient: {patient.nom} {patient.prenom}")
        print()
        
        # Test 1: Acte de laboratoire - 50 000 FCFA
        print("Test 1: Acte de laboratoire - 50 000 FCFA")
        print("-" * 60)
        result1 = InsuranceService.calculate_coverage(
            patient_id=patient.id,
            montant_total=Decimal("50000"),
            type_acte="laboratoire",
            db=db
        )
        print(f"Est assuré: {result1.est_assure}")
        print(f"Taux de couverture: {result1.taux_couverture}%")
        print(f"Part assurance: {result1.part_assurance:,.0f} FCFA")
        print(f"Part patient: {result1.part_patient:,.0f} FCFA")
        if result1.plafond_restant is not None:
            print(f"Plafond restant: {result1.plafond_restant:,.0f} FCFA")
        print(f"Message: {result1.message}")
        print()
        
        # Test 2: Acte d'imagerie - 100 000 FCFA
        print("Test 2: Acte d'imagerie - 100 000 FCFA")
        print("-" * 60)
        result2 = InsuranceService.calculate_coverage(
            patient_id=patient.id,
            montant_total=Decimal("100000"),
            type_acte="imagerie",
            db=db
        )
        print(f"Est assuré: {result2.est_assure}")
        print(f"Taux de couverture: {result2.taux_couverture}%")
        print(f"Part assurance: {result2.part_assurance:,.0f} FCFA")
        print(f"Part patient: {result2.part_patient:,.0f} FCFA")
        if result2.plafond_restant is not None:
            print(f"Plafond restant: {result2.plafond_restant:,.0f} FCFA")
        print(f"Message: {result2.message}")
        print()
        
        # Test 3: Acte dentaire (exclu pour SAHAM) - 30 000 FCFA
        print("Test 3: Acte dentaire (exclu) - 30 000 FCFA")
        print("-" * 60)
        result3 = InsuranceService.calculate_coverage(
            patient_id=patient.id,
            montant_total=Decimal("30000"),
            type_acte="dentaire",
            db=db
        )
        print(f"Est assuré: {result3.est_assure}")
        print(f"Est exclu: {result3.est_exclu}")
        print(f"Part assurance: {result3.part_assurance:,.0f} FCFA")
        print(f"Part patient: {result3.part_patient:,.0f} FCFA")
        print(f"Message: {result3.message}")
        print()
        
        print("=" * 60)
        print("TESTS TERMINÉS")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
