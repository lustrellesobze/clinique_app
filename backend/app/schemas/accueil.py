from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.passage_accueil import StatutPassage, TypeConsultationPassage
from app.models.patient import Sexe


class InscriptionPatientBase(BaseModel):
    nom: str = Field(..., max_length=100)
    prenom: str = Field(..., max_length=100)
    date_naissance: Optional[date] = None
    sexe: Sexe
    telephone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=150)
    contact_urgence: Optional[str] = Field(None, max_length=255)

    poids_kg: Optional[Decimal] = None
    taille_cm: Optional[Decimal] = None
    temperature_c: Optional[Decimal] = None
    tension: Optional[str] = Field(None, max_length=30)

    motif_consultation: str = ""
    type_consultation: TypeConsultationPassage = TypeConsultationPassage.generale
    medecin_id: str = Field(..., min_length=1, description="Médecin attribué")

    derniere_date_regles: Optional[date] = None

    est_assure: bool = False
    assurance_id: Optional[str] = Field(None, max_length=36)
    compagnie_assurance: Optional[str] = Field(None, max_length=200)
    date_validite_assurance: Optional[date] = None
    numero_assure: Optional[str] = Field(None, max_length=80)

    montant_consultation_fcfa: Decimal = Field(default=Decimal("5000"))
    remise_fcfa: Decimal = Field(default=Decimal("0"))


class InscriptionPatientCreate(InscriptionPatientBase):
    pass


class PatientOut(BaseModel):
    id: str
    code_patient: str
    nom: str
    prenom: str
    date_naissance: Optional[date] = None
    sexe: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


class PassageAccueilOut(BaseModel):
    id: str
    patient_id: str
    statut: str
    type_consultation: str
    montant_consultation_fcfa: Decimal
    remise_fcfa: Decimal
    total_fcfa: Decimal
    medecin_id: Optional[str] = None
    enregistre_par_id: str

    class Config:
        from_attributes = True


class FactureAccueilOut(BaseModel):
    id: str
    numero_facture: str
    total_fcfa: Decimal
    medecin_nom: str | None = None
    batiment: str | None = None


class InscriptionPatientResponse(BaseModel):
    patient: PatientOut
    passage: PassageAccueilOut
    facture: FactureAccueilOut | None = None
    message_transfert: str


class MedecinOut(BaseModel):
    id: str
    nom: str
    prenom: str

    class Config:
        from_attributes = True
