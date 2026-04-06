import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class TypeConsultationPassage(str, enum.Enum):
    generale = "generale"
    rendez_vous = "rendez_vous"
    specialiste = "specialiste"
    urgence = "urgence"


class StatutPassage(str, enum.Enum):
    """Après enregistrement : visible médecin + caisse jusqu’au paiement."""

    enregistre = "enregistre"
    en_consultation = "en_consultation"
    attente_paiement = "attente_paiement"
    termine = "termine"
    annule = "annule"


class PassageAccueil(Base):
    """Une venue à l’accueil : vitaux, consultation, lien patient / infirmier / médecin."""

    __tablename__ = "passages_accueil"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    enregistre_par_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    medecin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    poids_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    taille_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    tension: Mapped[str | None] = mapped_column(String(30), nullable=True)

    motif_consultation: Mapped[str] = mapped_column(Text, default="")
    type_consultation: Mapped[TypeConsultationPassage] = mapped_column(
        SQLEnum(TypeConsultationPassage, native_enum=False, length=30),
        default=TypeConsultationPassage.generale,
    )

    derniere_date_regles: Mapped[date | None] = mapped_column(Date, nullable=True)

    est_assure: Mapped[bool] = mapped_column(Boolean, default=False)
    compagnie_assurance: Mapped[str | None] = mapped_column(String(150), nullable=True)
    date_validite_assurance: Mapped[date | None] = mapped_column(Date, nullable=True)
    numero_assure: Mapped[str | None] = mapped_column(String(80), nullable=True)

    montant_consultation_fcfa: Mapped[float] = mapped_column(
        Numeric(12, 2), default=5000
    )
    remise_fcfa: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    statut: Mapped[StatutPassage] = mapped_column(
        SQLEnum(StatutPassage, native_enum=False, length=30),
        default=StatutPassage.enregistre,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )
