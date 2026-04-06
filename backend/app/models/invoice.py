import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class FactureStatut(str, enum.Enum):
    brouillon = "brouillon"
    en_attente = "en_attente"
    partielle = "partielle"
    payee = "payee"
    annulee = "annulee"
    retard = "retard"


class Facture(Base):
    __tablename__ = "factures"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    numero_facture: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    caissier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    statut: Mapped[FactureStatut] = mapped_column(
        SQLEnum(FactureStatut, native_enum=False, length=20),
        default=FactureStatut.brouillon,
    )
    montant_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    montant_regle: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remise_globale: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    part_assurance: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    part_patient: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    devise: Mapped[str] = mapped_column(String(3), default="XAF")
    est_annulee: Mapped[bool] = mapped_column(Boolean, default=False)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    lignes: Mapped[list["LigneFacture"]] = relationship(
        "LigneFacture",
        back_populates="facture",
        cascade="all, delete-orphan",
    )


class LigneFacture(Base):
    __tablename__ = "lignes_facture"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    facture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("factures.id", ondelete="CASCADE"), nullable=False
    )
    ordre: Mapped[int] = mapped_column(default=0)
    designation: Mapped[str] = mapped_column(String(255))
    quantite: Mapped[float] = mapped_column(Numeric(10, 3), default=1)
    prix_unitaire: Mapped[float] = mapped_column(Numeric(12, 2))
    remise_montant: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    montant_ligne: Mapped[float] = mapped_column(Numeric(12, 2))

    facture: Mapped["Facture"] = relationship("Facture", back_populates="lignes")
