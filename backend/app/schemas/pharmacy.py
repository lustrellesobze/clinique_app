from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PharmacyItemDetail(BaseModel):
    id: str
    nom_item: str
    description: str | None = None
    quantite: int
    prix_unitaire: Decimal


class PharmacyPrescriptionPendingResponse(BaseModel):
    id: str
    patient_name: str
    patient_id: str
    medecin_name: str
    date_prescription: datetime
    items: list[PharmacyItemDetail]
    montant_total: Decimal


class PharmacyInvoiceCreate(BaseModel):
    prescription_id: str
    montant_total: Decimal = Field(gt=0)
    remise_fidelite: Decimal = Field(default=Decimal("0"), ge=0)
    part_assurance: Decimal = Field(default=Decimal("0"), ge=0)
    part_patient: Decimal = Field(gt=0)
    mode_paiement: str | None = None


class PharmacyInvoiceResponse(BaseModel):
    id: str
    numero_facture: str
    patient_id: str
    patient_name: str
    montant_total: Decimal
    part_assurance: Decimal
    part_patient: Decimal
    statut: str
    created_at: datetime


class SubstituteItemIn(BaseModel):
    equivalent_nom: str = Field(min_length=2, max_length=200)
    motif: str | None = None
