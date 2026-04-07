"""
Modèles Prescription et PrescriptionItem - Ordonnances médicales
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, Integer, text
from sqlalchemy.orm import relationship

from app.database import Base


class Prescription(Base):
    """Modèle pour les prescriptions/ordonnances"""
    
    __tablename__ = "prescriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    medecin_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    passage_accueil_id = Column(String(36), ForeignKey("passages_accueil.id", ondelete="SET NULL"), nullable=True)
    type_prescription = Column(String(30), nullable=False, index=True)  # pharmacie, labo, imagerie
    statut = Column(String(30), default="en_attente", nullable=False, index=True)  # en_attente, transferee, traitee, annulee
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    # Relations
    patient = relationship("Patient")
    medecin = relationship("User", foreign_keys=[medecin_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Prescription {self.id} - {self.type_prescription} - {self.statut}>"


class PrescriptionItem(Base):
    """Modèle pour les items d'une prescription"""
    
    __tablename__ = "prescription_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id = Column(String(36), ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    nom_item = Column(String(200), nullable=False)  # Nom du médicament/examen
    description = Column(Text, nullable=True)  # Posologie pour médicaments, instructions pour examens
    quantite = Column(Integer, default=1, nullable=False)
    prix_unitaire = Column(Numeric(12, 2), default=0, nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    # Relation
    prescription = relationship("Prescription", back_populates="items")
    
    def __repr__(self):
        return f"<PrescriptionItem {self.nom_item} x{self.quantite}>"
