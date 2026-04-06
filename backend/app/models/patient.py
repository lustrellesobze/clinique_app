import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Sexe(str, enum.Enum):
    M = "M"
    F = "F"
    autre = "autre"


class Patient(Base):
    """Dossier patient (aligné spec clinique : code type P-AAAA-XXXXX côté métier)."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code_patient: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    date_naissance: Mapped[date | None] = mapped_column(Date, nullable=True)
    sexe: Mapped[Sexe | None] = mapped_column(
        SQLEnum(Sexe, native_enum=False, length=10),
        nullable=True,
    )
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_urgence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    medecin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assurance_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("insurances.id", ondelete="SET NULL"), nullable=True
    )
    assureur: Mapped[str | None] = mapped_column(String(150), nullable=True)
    numero_police_assurance: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    est_actif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )
    
    # Relations
    hospitalizations = relationship("Hospitalization", back_populates="patient")
