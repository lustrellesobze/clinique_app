import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ModePaiement(str, enum.Enum):
    especes = "especes"
    mtn_momo = "mtn_momo"
    orange_money = "orange_money"
    carte = "carte"
    assurance = "assurance"


class StatutPaiement(str, enum.Enum):
    en_attente = "en_attente"
    confirme = "confirme"
    annule = "annule"


class Paiement(Base):
    __tablename__ = "paiements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    facture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("factures.id", ondelete="RESTRICT"), nullable=False
    )
    caissier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    montant: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mode_paiement: Mapped[ModePaiement] = mapped_column(
        SQLEnum(ModePaiement, native_enum=False, length=20),
        default=ModePaiement.especes,
    )
    statut: Mapped[StatutPaiement] = mapped_column(
        SQLEnum(StatutPaiement, native_enum=False, length=20),
        default=StatutPaiement.confirme,
    )
    reference_transaction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), nullable=False
    )
