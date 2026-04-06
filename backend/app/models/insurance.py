"""
Modèle Insurance - Gestion des compagnies d'assurance
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, text

from app.database import Base


class Insurance(Base):
    """Modèle pour les compagnies d'assurance"""
    
    __tablename__ = "insurances"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom_compagnie = Column(String(150), unique=True, nullable=False, index=True)
    taux_couverture = Column(Integer, nullable=False)  # Pourcentage 0-100
    plafond_annuel_fcfa = Column(Numeric(12, 2), nullable=True)
    exclusions = Column(Text, nullable=True)  # JSON list des actes exclus
    est_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    def __repr__(self):
        return f"<Insurance {self.nom_compagnie} - {self.taux_couverture}%>"
