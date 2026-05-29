"""
Crée ou met à jour le catalogue d'assurances (CNPS, ASCOMA, AXA, etc.).

Usage (depuis backend/) :
  python scripts/seed_insurance_catalog.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.insurance import Insurance
from app.services.insurance_catalog_seed import CATALOG_INSURANCES, build_exclusions_field


def main() -> None:
    db = SessionLocal()
    try:
        created = 0
        updated = 0
        for entry in CATALOG_INSURANCES:
            nom = entry["nom_compagnie"]
            existing = db.scalars(
                select(Insurance).where(Insurance.nom_compagnie == nom)
            ).first()
            exclusions = build_exclusions_field(entry)
            if existing:
                existing.taux_couverture = entry["taux_couverture"]
                existing.plafond_annuel_fcfa = entry["plafond_annuel_fcfa"]
                existing.est_active = entry["est_active"]
                existing.exclusions = exclusions
                updated += 1
            else:
                ins = Insurance(
                    nom_compagnie=nom,
                    taux_couverture=entry["taux_couverture"],
                    plafond_annuel_fcfa=entry["plafond_annuel_fcfa"],
                    est_active=entry["est_active"],
                    exclusions=exclusions,
                )
                db.add(ins)
                created += 1
        db.commit()
        print(f"Catalogue assurances : {created} créée(s), {updated} mise(s) à jour.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
