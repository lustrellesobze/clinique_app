from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ConsultationRoutingOut(BaseModel):
    medecin_id: str | None = None
    medecin_nom: str | None = None
    batiment: str | None = None
    type_consultation: str | None = None
    type_consultation_label: str | None = None


class PatientCaisseOut(BaseModel):
    id: str
    code_patient: str
    nom: str
    prenom: str
    date_naissance: date | None = None
    telephone: str | None = None
    email: str | None = None
    medecin_id: str | None = None
    assureur: str | None = None
    numero_police_assurance: str | None = None
    est_actif: bool
    medecin_nom: str | None = None
    batiment: str | None = None
    type_consultation_label: str | None = None
    motif_consultation: str | None = None
    montant_consultation_fcfa: float | None = None
    remise_passage_fcfa: float | None = None


class AssignDoctorIn(BaseModel):
    medecin_id: str = Field(min_length=1)


class InvoiceLineIn(BaseModel):
    designation: str = Field(min_length=1, max_length=255)
    quantite: Decimal = Field(default=Decimal("1"))
    prix_unitaire: Decimal = Field(ge=0)
    remise_montant: Decimal = Field(default=Decimal("0"), ge=0)


class CreateConsultationInvoiceIn(BaseModel):
    patient_id: str | None = None
    code_patient: str | None = None
    commentaire: str | None = None
    remise_globale: Decimal = Field(default=Decimal("0"), ge=0)
    lignes: list[InvoiceLineIn] = Field(default_factory=list)


class InvoiceLineOut(BaseModel):
    id: str
    ordre: int
    designation: str
    quantite: Decimal
    prix_unitaire: Decimal
    remise_montant: Decimal
    montant_ligne: Decimal


class InvoiceOut(BaseModel):
    id: str
    numero_facture: str
    patient_id: str
    caissier_id: str | None = None
    statut: str
    montant_total: Decimal
    montant_regle: Decimal
    restant_a_payer: Decimal
    remise_globale: Decimal
    part_assurance: Decimal | None = None
    part_patient: Decimal | None = None
    devise: str
    commentaire: str | None = None
    created_at: datetime | None = None
    lignes: list[InvoiceLineOut] = Field(default_factory=list)
    patient: PatientCaisseOut | None = None
    medecin_nom: str | None = None
    batiment: str | None = None
    type_consultation_label: str | None = None
    code_patient: str | None = None
    paiements: list["PaymentOut"] = Field(default_factory=list)


class PaymentCreateIn(BaseModel):
    facture_id: str
    montant: Decimal = Field(gt=0)
    mode_paiement: str = Field(
        pattern="^(especes|mtn_momo|orange_money|carte|assurance)$"
    )
    reference_transaction: str | None = None
    commentaire: str | None = None


class MobilePaymentInitIn(BaseModel):
    facture_id: str
    provider: str = Field(pattern="^(orange_money|mtn_momo)$")
    montant: Decimal = Field(gt=0)
    telephone: str | None = Field(default=None, min_length=8, max_length=20)
    reference_transaction: str | None = None


class MobilePaymentInitOut(BaseModel):
    payment: "PaymentOut"
    qr_png_base64: str = ""
    qr_payload: str = ""
    instructions: list[str]
    campay_active: bool = False
    telephone: str | None = None
    payment_link: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    facture_id: str
    caissier_id: str | None = None
    montant: Decimal
    mode_paiement: str
    statut: str
    reference_transaction: str | None = None
    commentaire: str | None = None
    created_at: datetime | None = None


class PaymentStatusOut(BaseModel):
    payment_id: str
    statut: str
    facture_statut: str
    montant_regle: Decimal
    restant_a_payer: Decimal
