"""Modèles SQLAlchemy — tables BDD."""

from app.models.hospitalization import Hospitalization
from app.models.insurance import Insurance
from app.models.invoice import Facture, FactureStatut, LigneFacture
from app.models.notification import Notification
from app.models.passage_accueil import PassageAccueil, StatutPassage, TypeConsultationPassage
from app.models.payment import ModePaiement, Paiement, StatutPaiement
from app.models.patient import Patient, Sexe
from app.models.prescription import Prescription, PrescriptionItem
from app.models.room import Room
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "Patient",
    "Sexe",
    "Facture",
    "FactureStatut",
    "LigneFacture",
    "Paiement",
    "ModePaiement",
    "StatutPaiement",
    "PassageAccueil",
    "StatutPassage",
    "TypeConsultationPassage",
    "Room",
    "Hospitalization",
    "Insurance",
    "Notification",
    "Prescription",
    "PrescriptionItem",
]
