"""
Crée ou met à jour les comptes de démo (après `alembic upgrade head`) :
  python scripts/create_test_user.py

Même mot de passe pour tous les comptes (plateforme de test).
Les médecins correspondent à la liste « Médecin attribué » de l'accueil.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.seed.medecins_demo import MEDECINS_AS_SEED_USERS

# ─── Identifiants démo (à changer en production) ─────────────────────────
SHARED_PASSWORD = "demo123"

# (rôle, email, nom, prénom, service affiché)
SEED_USERS: list[tuple[UserRole, str, str, str, str | None]] = [
    (UserRole.infirmiere_accueil, "accueil@demo.cm", "Kamga", "Chantal", "Accueil"),
    (UserRole.caissier_central, "caisse@demo.cm", "Nguema", "Eric", "Caisse centrale"),
    *MEDECINS_AS_SEED_USERS,
    (UserRole.caissier_pharmacie, "pharmacie@demo.cm", "Mballa", "Lucie", "Pharmacie"),
    (UserRole.caissier_labo, "labo@demo.cm", "Fotso", "Alain", "Laboratoire"),
    (UserRole.caissier_imagerie, "imagerie@demo.cm", "Bella", "Sarah", "Imagerie"),
    (UserRole.comptable, "comptable@demo.cm", "Tchouassi", "Henri", "Comptabilité"),
    (UserRole.resp_hospit, "hospit@demo.cm", "Mvondo", "Grace", "Hospitalisation"),
    (UserRole.gestionnaire_assurance, "assurance@demo.cm", "Nkolo", "Patricia", "Assurances"),
    (UserRole.admin, "admin@demo.cm", "Admin", "Système", None),
]


def main() -> None:
    db: Session = SessionLocal()
    pwd_hash = hash_password(SHARED_PASSWORD)
    created = 0
    updated = 0
    skipped = 0
    try:
        for role, email, nom, prenom, service in SEED_USERS:
            existing = db.scalars(select(User).where(User.email == email)).first()
            if existing:
                changed = False
                if existing.nom != nom:
                    existing.nom = nom
                    changed = True
                if existing.prenom != prenom:
                    existing.prenom = prenom
                    changed = True
                if existing.service != service:
                    existing.service = service
                    changed = True
                if existing.role != role:
                    existing.role = role
                    changed = True
                if not existing.est_actif:
                    existing.est_actif = True
                    changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1
                continue
            db.add(
                User(
                    id=str(uuid.uuid4()),
                    nom=nom,
                    prenom=prenom,
                    email=email,
                    mot_de_passe_hash=pwd_hash,
                    role=role,
                    service=service,
                    est_actif=True,
                )
            )
            created += 1
        db.commit()
    finally:
        db.close()

    print("Mot de passe commun (tous les comptes) :", SHARED_PASSWORD)
    print("Comptes créés :", created, "| mis à jour :", updated, "| inchangés :", skipped)
    print("\nMédecins (liste accueil = comptes de connexion) :")
    for _, email, nom, prenom, service in MEDECINS_AS_SEED_USERS:
        print(f"  Dr {prenom} {nom} — {email} — {service}")


if __name__ == "__main__":
    main()
