"""
Modèle Hospitalization - Gestion des séjours hospitaliers
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.orm import relationship

from app.database import Base


class Hospitalization(Base):
    """Modèle pour les hospitalisations"""
    
    __tablename__ = "hospitalizations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    medecin_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    date_admission = Column(DateTime, nullable=False, index=True)
    date_sortie = Column(DateTime, nullable=True)
    motif_hospitalisation = Column(Text, nullable=True)
    acompte_verse_fcfa = Column(Numeric(12, 2), default=0, nullable=False)
    montant_total_fcfa = Column(Numeric(12, 2), default=0, nullable=False)
    statut = Column(String(30), default="en_cours", nullable=False, index=True)  # en_cours, cloture
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    # Relations
    patient = relationship("Patient", back_populates="hospitalizations")
    room = relationship("Room", back_populates="hospitalizations")
    medecin = relationship("User", foreign_keys=[medecin_id])
    
    def __repr__(self):
        return f"<Hospitalization {self.id} - Patient {self.patient_id} - {self.statut}>"
