from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DoctorPatientOut(BaseModel):
    patient_id: str
    passage_id: str
    code_patient: str
    nom: str
    prenom: str
    telephone: str | None = None
    assureur: str | None = None
    statut_passage: str
    type_consultation: str
    created_at: datetime | None = None


class DoctorLookupOut(DoctorPatientOut):
    date_naissance: date | None = None
    sexe: str | None = None
    age_ans: int | None = None
    derniere_consultation: datetime | None = None
    allergies_connues: str = "Aucune connue"


class ConsultationUpdateIn(BaseModel):
    observations: str | None = None
    diagnostic: str | None = None
    statut: str | None = Field(
        default=None,
        pattern="^(en_consultation|attente_paiement|termine|annule)$",
    )
    poids_kg: Decimal | None = None
    taille_cm: Decimal | None = None
    temperature_c: Decimal | None = None
    tension: str | None = None


class ConsultationOut(BaseModel):
    passage_id: str
    patient_id: str
    statut: str
    motif_consultation: str
    poids_kg: Decimal | None = None
    taille_cm: Decimal | None = None
    temperature_c: Decimal | None = None
    tension: str | None = None


class PrescriptionItemIn(BaseModel):
    nom_item: str = Field(min_length=1, max_length=200)
    description: str | None = None
    quantite: int = Field(default=1, ge=1)
    prix_unitaire: Decimal = Field(default=Decimal("0"), ge=0)


class PrescriptionCreateIn(BaseModel):
    patient_id: str
    passage_accueil_id: str | None = None
    type_prescription: str = Field(
        pattern=(
            "^(pharmacie|laboratoire|imagerie|hospitalisation|"
            "specialiste|chirurgie|orl)$"
        )
    )
    notes: str | None = None
    items: list[PrescriptionItemIn] = Field(default_factory=list, min_length=1)


class PrescriptionTransferIn(BaseModel):
    destination: str = Field(
        pattern=(
            "^(pharmacie|laboratoire|imagerie|hospitalisation|"
            "specialiste|chirurgie|orl)$"
        )
    )
    commentaire: str | None = None


class PrescriptionItemOut(BaseModel):
    id: str
    nom_item: str
    description: str | None = None
    quantite: int
    prix_unitaire: Decimal


class PrescriptionOut(BaseModel):
    id: str
    patient_id: str
    medecin_id: str
    passage_accueil_id: str | None = None
    type_prescription: str
    statut: str
    notes: str | None = None
    created_at: datetime | None = None
    items: list[PrescriptionItemOut] = Field(default_factory=list)


class PatientRecordOut(BaseModel):
    patient_id: str
    code_patient: str
    nom: str
    prenom: str
    telephone: str | None = None
    assureur: str | None = None
    date_naissance: date | None = None
    sexe: str | None = None
    age_ans: int | None = None
    derniere_consultation: datetime | None = None
    allergies_connues: str = "Aucune connue"
    passages: list[ConsultationOut] = Field(default_factory=list)
    prescriptions: list[PrescriptionOut] = Field(default_factory=list)
