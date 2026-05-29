"""
Schemas Pydantic pour le module Hospitalisation
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RoomResponse(BaseModel):
    """Réponse pour une chambre"""
    id: str
    numero: str
    type_chambre: str
    tarif_journalier_fcfa: Decimal
    est_disponible: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class HospitalizationCreate(BaseModel):
    """Création d'une hospitalisation"""
    patient_id: str = Field(..., description="ID du patient")
    room_id: str = Field(..., description="ID de la chambre")
    medecin_id: Optional[str] = Field(None, description="ID du médecin")
    motif_hospitalisation: Optional[str] = Field(None, description="Motif d'hospitalisation")
    acompte_verse_fcfa: Decimal = Field(..., gt=0, description="Acompte versé")
    date_admission: datetime = Field(default_factory=datetime.now, description="Date d'admission")


class HospitalizationResponse(BaseModel):
    """Réponse pour une hospitalisation"""
    id: str
    patient_id: str
    patient_name: str
    room_numero: str
    room_type: str
    medecin_name: Optional[str] = None
    date_admission: datetime
    date_sortie: Optional[datetime] = None
    motif_hospitalisation: Optional[str] = None
    acompte_verse_fcfa: Decimal
    montant_total_fcfa: Decimal
    statut: str
    tarif_journalier: Decimal
    nombre_jours: int
    
    class Config:
        from_attributes = True


class HospitalizationDischarge(BaseModel):
    """Clôture d'une hospitalisation"""
    hospitalization_id: str = Field(..., description="ID de l'hospitalisation")
    date_sortie: datetime = Field(default_factory=datetime.now, description="Date de sortie")
    mode_paiement: str = Field(..., description="Mode de paiement: especes, carte, mobile_money, cheque")
    reference_paiement: Optional[str] = Field(None, description="Référence de paiement")


class HospitalizationStatsOut(BaseModel):
    chambres_occupees: int
    chambres_total: int
    ca_hospitalisation_fcfa: float
    duree_moyenne_jours: float
    patients_hospitalises: int = 0
    sejours_clotures: int = 0


class HospitalizationAdminRow(BaseModel):
    id: str
    patient_id: str
    patient_code: str
    patient_name: str
    room_numero: str
    room_type: str
    room_label: str
    medecin_name: Optional[str] = None
    date_admission: datetime
    nombre_jours: int
    frais_chambre_fcfa: float
    total_facture_fcfa: float
    acomptes_fcfa: float
    solde_fcfa: float
    motif_hospitalisation: Optional[str] = None
    tarif_journalier: float
    statut: str


class HospitalizationDashboardOut(BaseModel):
    stats: HospitalizationStatsOut
    patients: list[HospitalizationAdminRow]
    rooms_available: int


class HospitalizationDischargeResponse(BaseModel):
    """Réponse après clôture"""
    hospitalization_id: str
    facture_id: str
    numero_facture: str
    nombre_jours: int
    montant_total: Decimal
    acompte_verse: Decimal
    reste_a_payer: Decimal
    
    class Config:
        from_attributes = True
