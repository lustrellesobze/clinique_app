"""
Crée une hospitalisation de test pour tester le CRON de facturation.
"""
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.hospitalization import Hospitalization
from app.models.patient import Patient
from app.models.room import Room


def main() -> None:
    db: Session = SessionLocal()
    
    try:
        # Récupérer un patient de test
        patient = db.scalars(select(Patient).limit(1)).first()
        if not patient:
            print("❌ Aucun patient trouvé. Exécutez d'abord create_test_patient.py")
            return
        
        # Récupérer une chambre disponible
        room = db.scalars(
            select(Room).where(Room.est_disponible == True).limit(1)
        ).first()
        if not room:
            print("❌ Aucune chambre disponible. Exécutez d'abord create_test_rooms.py")
            return
        
        # Créer une hospitalisation qui a commencé il y a 3 jours
        date_admission = datetime.now() - timedelta(days=3)
        
        hospitalization = Hospitalization(
            patient_id=patient.id,
            room_id=room.id,
            date_admission=date_admission,
            motif_hospitalisation="Test CRON - Observation médicale",
            acompte_verse_fcfa=Decimal("50000")  # Acompte de 50 000 FCFA
        )
        
        # Marquer la chambre comme occupée
        room.est_disponible = False
        
        db.add(hospitalization)
        db.commit()
        
        print("✅ Hospitalisation de test créée avec succès!")
        print(f"   Patient: {patient.nom} {patient.prenom}")
        print(f"   Chambre: {room.numero} ({room.type_chambre})")
        print(f"   Tarif journalier: {room.tarif_journalier_fcfa} FCFA")
        print(f"   Date admission: {date_admission.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Acompte versé: 50 000 FCFA")
        print(f"   Jours écoulés: 3")
        print(f"   Total accumulé: {float(room.tarif_journalier_fcfa) * 3} FCFA")
        print("\nVous pouvez maintenant exécuter le script CRON:")
        print("   python scripts/cron_hospitalization.py")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
