"""
Schemas pour le module Assurances
"""
from decimal import Decimal
from typing import Optional
from datetime import date

from pydantic import BaseModel, Field


class TauxParCategorie(BaseModel):
    consultation: int = Field(80, ge=0, le=100)
    imagerie: int = Field(70, ge=0, le=100)
    chirurgie: int = Field(50, ge=0, le=100)
    esthetique: int = Field(0, ge=0, le=100)
    hospitalisation: int = Field(100, ge=0, le=100)


class InsuranceResponse(BaseModel):
    """Réponse pour une compagnie d'assurance"""
    id: str
    nom_compagnie: str
    taux_couverture: int
    plafond_annuel_fcfa: Optional[Decimal]
    est_active: bool

    class Config:
        from_attributes = True


class InsuranceCompanyDetailOut(InsuranceResponse):
    """Compagnie avec taux par catégorie, franchise et exclusions."""
    taux_par_categorie: TauxParCategorie
    franchise_fcfa: Optional[Decimal] = None
    franchise_libelle: str = "Aucune"
    exclusions_list: list[str] = Field(default_factory=list)


class InsuranceCompanyCreate(BaseModel):
    nom_compagnie: str = Field(..., min_length=2, max_length=200)
    taux_par_categorie: TauxParCategorie
    plafond_annuel_fcfa: Optional[Decimal] = Field(None, ge=0)
    franchise_fcfa: Optional[Decimal] = Field(None, ge=0)
    franchise_libelle: Optional[str] = Field(None, max_length=200)
    exclusions_list: list[str] = Field(default_factory=list)
    est_active: bool = True


class InsuranceCompanyUpdate(BaseModel):
    nom_compagnie: Optional[str] = Field(None, min_length=2, max_length=200)
    taux_par_categorie: Optional[TauxParCategorie] = None
    plafond_annuel_fcfa: Optional[Decimal] = Field(None, ge=0)
    franchise_fcfa: Optional[Decimal] = Field(None, ge=0)
    franchise_libelle: Optional[str] = Field(None, max_length=200)
    exclusions_list: Optional[list[str]] = None
    est_active: Optional[bool] = None


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
    patient_code: str | None = None
    compagnie_assurance: str
    montant_total: Decimal
    part_assurance: Decimal
    date_emission: date
    statut: str
    statut_creance: str = "en_attente"
    statut_creance_label: str = "En attente"

    class Config:
        from_attributes = True


class InsuranceValidatePaymentRequest(BaseModel):
    """Requête pour valider le paiement d'une créance"""
    facture_ids: list[str]
    reference_paiement: str
    montant_paye: Decimal
