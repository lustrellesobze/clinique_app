"""
Modèle Notification - Gestion des notifications utilisateur
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import relationship

from app.database import Base


class Notification(Base):
    """Modèle pour les notifications"""
    
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type_notification = Column(String(50), nullable=False)  # assignation, paiement, alerte
    titre = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON data
    est_lue = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False, index=True)
    
    # Relation
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification {self.type_notification} - User {self.user_id}>"
