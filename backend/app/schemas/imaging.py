"""
Schemas Pydantic pour le module Imagerie
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class ImagingItemDetail(BaseModel):
    """Détail d'un item d'imagerie"""
    id: str
    nom_examen: str
    prix_unitaire: Decimal
    quantite: int = 1
    
    class Config:
        from_attributes = True


class ImagingPrescriptionPendingResponse(BaseModel):
    """Réponse pour une prescription d'imagerie en attente"""
    id: str
    patient_name: str
    patient_id: str
    medecin_name: str
    date_prescription: datetime
    items: List[ImagingItemDetail]
    montant_total: Decimal
    
    class Config:
        from_attributes = True


class ImagingInvoiceCreate(BaseModel):
    """Création d'une facture imagerie"""
    prescription_id: str = Field(..., description="ID de la prescription")
    montant_total: Decimal = Field(..., gt=0, description="Montant total")
    remise_fidelite: Decimal = Field(default=0, ge=0, description="Remise fidélité")
    part_assurance: Decimal = Field(default=0, ge=0, description="Part assurance")
    part_patient: Decimal = Field(..., gt=0, description="Part patient")
    mode_paiement: str = Field(..., description="Mode de paiement: especes, carte, mobile_money, cheque")
    reference_paiement: Optional[str] = Field(None, description="Référence de paiement")


class ImagingInvoiceResponse(BaseModel):
    """Réponse après création de facture imagerie"""
    id: str
    numero_facture: str
    patient_id: str
    patient_name: str
    montant_total: Decimal
    part_assurance: Decimal
    part_patient: Decimal
    statut: str
    created_at: datetime
    
    class Config:
        from_attributes = True
