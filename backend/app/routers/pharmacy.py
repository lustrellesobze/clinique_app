from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Facture, LigneFacture, Patient, Prescription, PrescriptionItem, User
from app.schemas.pharmacy import (
    PharmacyInvoiceCreate,
    PharmacyInvoiceResponse,
    PharmacyPrescriptionPendingResponse,
    PharmacyItemDetail,
    SubstituteItemIn,
)

router = APIRouter(prefix="/pharmacy", tags=["pharmacy"])


def _role_value(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)


@router.get("/pending", response_model=list[PharmacyPrescriptionPendingResponse])
async def get_pending_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = _role_value(current_user)
    if role not in ["caissier_pharmacie", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    prescriptions = (
        db.query(Prescription)
        .filter(
            or_(
                Prescription.type_prescription == "pharmacie",
                Prescription.type_prescription == "pharmacy",
            ),
            Prescription.statut == "transferee",
        )
        .order_by(Prescription.created_at.desc())
        .all()
    )

    result: list[PharmacyPrescriptionPendingResponse] = []
    for prescription in prescriptions:
        patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
        medecin = db.query(User).filter(User.id == prescription.medecin_id).first()
        montant_total = sum(Decimal(str(i.prix_unitaire)) * i.quantite for i in prescription.items)

        result.append(
            PharmacyPrescriptionPendingResponse(
                id=prescription.id,
                patient_name=f"{patient.nom} {patient.prenom}" if patient else "Inconnu",
                patient_id=prescription.patient_id,
                medecin_name=f"Dr. {medecin.nom} {medecin.prenom}" if medecin else "Inconnu",
                date_prescription=prescription.created_at,
                items=[
                    PharmacyItemDetail(
                        id=item.id,
                        nom_item=item.nom_item,
                        description=item.description,
                        prix_unitaire=item.prix_unitaire,
                        quantite=item.quantite,
                    )
                    for item in prescription.items
                ],
                montant_total=montant_total,
            )
        )
    return result


@router.put("/items/{item_id}/substitute", response_model=PharmacyItemDetail)
async def substitute_item(
    item_id: str,
    body: SubstituteItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = _role_value(current_user)
    if role not in ["caissier_pharmacie", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    item = db.query(PrescriptionItem).filter(PrescriptionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Médicament prescrit introuvable")

    original = item.nom_item
    motif = body.motif or "indisponible"
    item.nom_item = body.equivalent_nom
    item.description = (
        f"{item.description or ''}\nSubstitution: {original} -> {body.equivalent_nom} ({motif})"
    ).strip()
    db.commit()
    db.refresh(item)
    return PharmacyItemDetail(
        id=item.id,
        nom_item=item.nom_item,
        description=item.description,
        quantite=item.quantite,
        prix_unitaire=item.prix_unitaire,
    )


@router.post("/invoices", response_model=PharmacyInvoiceResponse)
async def create_pharmacy_invoice(
    invoice_data: PharmacyInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = _role_value(current_user)
    if role not in ["caissier_pharmacie", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    prescription = db.query(Prescription).filter(Prescription.id == invoice_data.prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription non trouvée")
    if prescription.type_prescription not in ["pharmacie", "pharmacy"]:
        raise HTTPException(status_code=400, detail="Cette prescription n'est pas de type pharmacie")
    if prescription.statut != "transferee":
        raise HTTPException(status_code=400, detail="Prescription non en attente")

    patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")

    year = datetime.now().year
    count = db.query(Facture).filter(Facture.numero_facture.like(f"FACT-PHAR-{year}-%")).count()
    numero_facture = f"FACT-PHAR-{year}-{count + 1:05d}"

    montant_total = Decimal(str(invoice_data.montant_total))
    part_assurance = Decimal(str(invoice_data.part_assurance))
    part_patient = Decimal(str(invoice_data.part_patient))
    remise = Decimal(str(invoice_data.remise_fidelite))

    facture = Facture(
        numero_facture=numero_facture,
        patient_id=prescription.patient_id,
        caissier_id=current_user.id,
        montant_total=float(montant_total),
        remise_globale=float(remise),
        part_assurance=float(part_assurance),
        part_patient=float(part_patient),
        montant_regle=float(montant_total) if invoice_data.mode_paiement else 0,
        statut="payee" if invoice_data.mode_paiement else "en_attente",
        commentaire="Facture pharmacie depuis prescription transferee",
    )
    db.add(facture)
    db.flush()

    for idx, item in enumerate(prescription.items, start=1):
        db.add(
            LigneFacture(
                facture_id=facture.id,
                ordre=idx,
                designation=item.nom_item,
                quantite=item.quantite,
                prix_unitaire=item.prix_unitaire,
                remise_montant=0,
                montant_ligne=Decimal(str(item.prix_unitaire)) * item.quantite,
            )
        )

    prescription.statut = "traitee"
    db.commit()
    db.refresh(facture)

    return PharmacyInvoiceResponse(
        id=facture.id,
        numero_facture=facture.numero_facture,
        patient_id=facture.patient_id,
        patient_name=f"{patient.nom} {patient.prenom}",
        montant_total=facture.montant_total,
        part_assurance=facture.part_assurance or 0,
        part_patient=facture.part_patient or 0,
        statut=facture.statut.value if hasattr(facture.statut, "value") else str(facture.statut),
        created_at=facture.created_at,
    )
