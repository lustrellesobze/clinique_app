"""
Données de démo pour le journal d'audit.

Usage (depuis backend/) :
  python scripts/seed_audit_demo.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import User
from app.services.audit_service import log_audit


def main() -> None:
    db = SessionLocal()
    try:
        user = db.scalars(select(User).where(User.est_actif.is_(True)).limit(1)).first()
        uid = user.id if user else None
        now = datetime.now()
        samples = [
            ("invoice_create", "facture", "FACT-CONS-2025-00047", {
                "numero_facture": "FACT-CONS-2025-00047",
                "patient_code": "P-2025-00047",
                "patient_nom": "KAMGA Jean-Baptiste",
            }),
            ("mobile_payment_confirm", "paiement", "pay-001", {
                "montant": 78000,
                "reference": "MTN-2025-88421",
                "numero_facture": "FACT-CONS-2025-00047",
            }),
            ("patient_create", "patient", "pat-001", {
                "patient_nom": "KAMGA Jean-Baptiste",
                "code_patient": "P-2025-00047",
                "medecin_nom": "Dr. NKOMO Paul",
            }),
            ("prescription_transfer", "prescription", "rx-001", {
                "patient_code": "P-2025-00046",
                "lignes": 2,
                "montant": 14000,
            }),
            ("invoice_cancel", "facture", "FACT-2025-00040", {
                "numero_facture": "FACT-2025-00040",
                "motif": "Doublon de saisie",
            }),
            ("user_login", "session", "sess-001", {}),
        ]
        for i, (action, etype, eid, details) in enumerate(samples):
            row = log_audit(
                db,
                user_id=uid,
                action=action,
                entity_type=etype,
                entity_id=eid,
                details=details,
                ip="192.168.1.12",
            )
            row.created_at = now - timedelta(minutes=15 * i)
        db.commit()
        print(f"{len(samples)} entrées audit de démo créées.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
