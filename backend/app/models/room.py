"""
Modèle Room - Gestion des chambres d'hospitalisation
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, Text, text
from sqlalchemy.orm import relationship

from app.database import Base


class Room(Base):
    """Modèle pour les chambres d'hospitalisation"""
    
    __tablename__ = "rooms"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    numero = Column(String(20), unique=True, nullable=False, index=True)
    type_chambre = Column(String(30), nullable=False)  # commune, individuelle, vip
    tarif_journalier_fcfa = Column(Numeric(12, 2), nullable=False)
    est_disponible = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    # Relations
    hospitalizations = relationship("Hospitalization", back_populates="room")
    
    def __repr__(self):
        return f"<Room {self.numero} - {self.type_chambre}>"
