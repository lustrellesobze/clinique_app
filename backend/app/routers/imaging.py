"""
Router pour le module Imagerie
"""
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models import Prescription, PrescriptionItem, Patient, User, Facture, LigneFacture
from app.schemas.imaging import (
    ImagingPrescriptionPendingResponse,
    ImagingItemDetail,
    ImagingInvoiceCreate,
    ImagingInvoiceResponse
)

router = APIRouter(prefix="/imaging", tags=["imaging"])


@router.get("/pending", response_model=List[ImagingPrescriptionPendingResponse])
async def get_pending_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des prescriptions d'imagerie en attente
    """
    # Vérifier les permissions
    if current_user.role not in ["caissier_imagerie", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Récupérer les prescriptions de type imagerie avec statut transferee
    prescriptions = db.query(Prescription).filter(
        Prescription.type_prescription == "imagerie",
        Prescription.statut == "transferee"
    ).order_by(Prescription.created_at.desc()).all()
    
    # Construire la réponse
    result = []
    for prescription in prescriptions:
        patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
        medecin = db.query(User).filter(User.id == prescription.medecin_id).first()
        
        # Calculer le montant total
        montant_total = sum(
            item.prix_unitaire * item.quantite 
            for item in prescription.items
        )
        
        result.append(ImagingPrescriptionPendingResponse(
            id=prescription.id,
            patient_name=f"{patient.nom} {patient.prenom}" if patient else "Inconnu",
            patient_id=prescription.patient_id,
            medecin_name=f"Dr. {medecin.nom} {medecin.prenom}" if medecin else "Inconnu",
            date_prescription=prescription.created_at,
            items=[
                ImagingItemDetail(
                    id=item.id,
                    nom_examen=item.nom_item,
                    prix_unitaire=item.prix_unitaire,
                    quantite=item.quantite
                )
                for item in prescription.items
            ],
            montant_total=montant_total
        ))
    
    return result


@router.post("/invoices", response_model=ImagingInvoiceResponse)
async def create_imaging_invoice(
    invoice_data: ImagingInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crée une facture pour une prescription d'imagerie
    """
    # Vérifier les permissions
    if current_user.role not in ["caissier_imagerie", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Récupérer la prescription
    prescription = db.query(Prescription).filter(
        Prescription.id == invoice_data.prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription non trouvée")
    
    if prescription.type_prescription != "imagerie":
        raise HTTPException(status_code=400, detail="Cette prescription n'est pas de type imagerie")
    
    if prescription.statut != "transferee":
        raise HTTPException(status_code=400, detail="Cette prescription n'est pas en attente de traitement")
    
    # Récupérer le patient
    patient = db.query(Patient).filter(Patient.id == prescription.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Générer le numéro de facture
    from datetime import datetime
    year = datetime.now().year
    count = db.query(Facture).filter(
        Facture.numero_facture.like(f"FACT-IMG-{year}-%")
    ).count()
    numero_facture = f"FACT-IMG-{year}-{count + 1:05d}"
    
    # Créer la facture
    facture = Facture(
        numero_facture=numero_facture,
        patient_id=prescription.patient_id,
        montant_total_fcfa=invoice_data.montant_total,
        remise_fcfa=invoice_data.remise_fidelite,
        part_assurance_fcfa=invoice_data.part_assurance,
        part_patient_fcfa=invoice_data.part_patient,
        statut="payee" if invoice_data.mode_paiement else "en_attente",
        type_facture="imagerie"
    )
    db.add(facture)
    db.flush()
    
    # Ajouter les lignes de facture
    for item in prescription.items:
        ligne = LigneFacture(
            facture_id=facture.id,
            designation=item.nom_item,
            quantite=item.quantite,
            prix_unitaire_fcfa=item.prix_unitaire,
            montant_total_fcfa=item.prix_unitaire * item.quantite
        )
        db.add(ligne)
    
    # Mettre à jour le statut de la prescription
    prescription.statut = "traitee"
    
    db.commit()
    db.refresh(facture)
    
    return ImagingInvoiceResponse(
        id=facture.id,
        numero_facture=facture.numero_facture,
        patient_id=facture.patient_id,
        patient_name=f"{patient.nom} {patient.prenom}",
        montant_total=facture.montant_total_fcfa,
        part_assurance=facture.part_assurance_fcfa,
        part_patient=facture.part_patient_fcfa,
        statut=facture.statut,
        created_at=facture.created_at
    )

