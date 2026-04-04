"""
Crée un utilisateur de test (après `alembic upgrade head`) :
  python scripts/create_test_user.py

Par défaut : admin@clinique.cm / admin123
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


def main() -> None:
    db: Session = SessionLocal()
    try:
        email = "admin@clinique.cm"
        existing = db.scalars(select(User).where(User.email == email)).first()
        if existing:
            print("Utilisateur déjà présent:", email)
            return
        u = User(
            id=str(uuid.uuid4()),
            nom="Admin",
            prenom="Système",
            email=email,
            mot_de_passe_hash=hash_password("admin123"),
            role=UserRole.admin,
            service=None,
            est_actif=True,
        )
        db.add(u)
        db.commit()
        print("Créé:", email, "/ admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
