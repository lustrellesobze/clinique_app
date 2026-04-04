import enum
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    infirmiere_accueil = "infirmiere_accueil"
    caissier_central = "caissier_central"
    medecin = "medecin"
    caissier_pharmacie = "caissier_pharmacie"
    caissier_labo = "caissier_labo"
    caissier_imagerie = "caissier_imagerie"
    comptable = "comptable"
    resp_hospit = "resp_hospit"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, length=40),
    )
    service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=True)
