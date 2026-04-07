from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Facture, LigneFacture, Patient, Prescription, User
from app.schemas.laboratory import LaboratoryInvoiceCreate, LaboratoryInvoiceResponse, PrescriptionItemDetail, PrescriptionPendingResponse

router = APIRouter(prefix="/laboratory", tags=["laboratory"])


def _role_value(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)


@router.get("/pending", response_model=list[PrescriptionPendingResponse])
async def get_pending_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in ["caissier_labo", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    prescriptions = (
        db.query(Prescription)
        .filter(
            or_(
                Prescription.type_prescription == "labo",
                Prescription.type_prescription == "laboratoire",
            ),
            Prescription.statut == "transferee",
        )
        .order_by(Prescription.created_at.desc())
        .all()
    )

    result: list[PrescriptionPendingResponse] = []
    for prescription in prescriptions:
        patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
        medecin = db.query(User).filter(User.id == prescription.medecin_id).first()
        montant_total = sum(Decimal(str(item.prix_unitaire)) * item.quantite for item in prescription.items)

        result.append(PrescriptionPendingResponse(
            id=prescription.id,
            patient_name=f"{patient.nom} {patient.prenom}" if patient else "Inconnu",
            patient_id=prescription.patient_id,
            medecin_name=f"Dr. {medecin.nom} {medecin.prenom}" if medecin else "Inconnu",
            date_prescription=prescription.created_at,
            items=[
                PrescriptionItemDetail(
                    id=item.id,
                    nom_examen=item.nom_item,
                    prix_unitaire=item.prix_unitaire,
                    quantite=item.quantite
                )
                for item in prescription.items
            ],
            montant_total=montant_total,
        ))

    return result


@router.post("/invoices", response_model=LaboratoryInvoiceResponse)
async def create_laboratory_invoice(
    invoice_data: LaboratoryInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in ["caissier_labo", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    prescription = db.query(Prescription).filter(Prescription.id == invoice_data.prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription non trouvée")
    if prescription.type_prescription not in ["labo", "laboratoire"]:
        raise HTTPException(status_code=400, detail="Cette prescription n'est pas de type laboratoire")
    if prescription.statut != "transferee":
        raise HTTPException(status_code=400, detail="Cette prescription n'est pas en attente de traitement")

    patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")

    year = datetime.now().year
    count = db.query(Facture).filter(Facture.numero_facture.like(f"FACT-LABO-{year}-%")).count()
    numero_facture = f"FACT-LABO-{year}-{count + 1:05d}"

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
        commentaire="Facture laboratoire depuis prescription transferee",
    )
    db.add(facture)
    db.flush()

    for idx, item in enumerate(prescription.items, start=1):
        db.add(LigneFacture(
            facture_id=facture.id,
            ordre=idx,
            designation=item.nom_item,
            quantite=item.quantite,
            prix_unitaire=item.prix_unitaire,
            remise_montant=0,
            montant_ligne=Decimal(str(item.prix_unitaire)) * item.quantite,
        ))

    prescription.statut = "traitee"
    db.commit()
    db.refresh(facture)

    return LaboratoryInvoiceResponse(
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
