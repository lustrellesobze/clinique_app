"""
Schemas pour le module Assurances
"""
from decimal import Decimal
from typing import Optional
from datetime import date

from pydantic import BaseModel, Field


class InsuranceResponse(BaseModel):
    """Réponse pour une compagnie d'assurance"""
    id: str
    nom_compagnie: str
    taux_couverture: int
    plafond_annuel_fcfa: Optional[Decimal]
    est_active: bool
    
    class Config:
        from_attributes = True


class InsuranceCalculateRequest(BaseModel):
    """Requête pour calculer la couverture d'assurance"""
    patient_id: str
    montant_total: Decimal = Field(gt=0)
    type_acte: str  # laboratoire, imagerie, consultation, hospitalisation, etc.


class InsuranceCalculateResponse(BaseModel):
    """Réponse du calcul de couverture"""
    est_assure: bool
    taux_couverture: int = 0
    part_assurance: Decimal = Decimal("0")
    part_patient: Decimal
    plafond_restant: Optional[Decimal] = None
    est_exclu: bool = False
    message: Optional[str] = None


class InsuranceClaimResponse(BaseModel):
    """Réponse pour une créance d'assurance"""
    facture_id: str
    numero_facture: str
    patient_nom: str
    patient_prenom: str
    compagnie_assurance: str
    montant_total: Decimal
    part_assurance: Decimal
    date_emission: date
    statut: str
    
    class Config:
        from_attributes = True


class InsuranceValidatePaymentRequest(BaseModel):
    """Requête pour valider le paiement d'une créance"""
    facture_ids: list[str]
    reference_paiement: str
    montant_paye: Decimal
