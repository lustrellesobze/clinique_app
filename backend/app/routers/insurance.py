"""
Router pour le module Assurances
"""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db, get_current_user
from app.core.permissions import require_role
from app.models.user import User, UserRole
from app.models.insurance import Insurance
from app.models.invoice import Facture
from app.models.patient import Patient
from app.schemas.insurance import (
    InsuranceResponse,
    InsuranceCalculateRequest,
    InsuranceCalculateResponse,
    InsuranceClaimResponse,
    InsuranceValidatePaymentRequest
)
from app.services.insurance_service import InsuranceService

router = APIRouter(prefix="/api/insurance", tags=["Insurance"])


@router.get("/companies", response_model=list[InsuranceResponse])
def get_insurance_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des compagnies d'assurance actives
    """
    insurances = db.scalars(
        select(Insurance).where(Insurance.est_active == True)
    ).all()
    
    return insurances


@router.post("/calculate", response_model=InsuranceCalculateResponse)
def calculate_insurance_coverage(
    request: InsuranceCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calcule la répartition assurance/patient pour un montant donné
    """
    return InsuranceService.calculate_coverage(
        patient_id=request.patient_id,
        montant_total=request.montant_total,
        type_acte=request.type_acte,
        db=db
    )


@router.get("/claims/pending", response_model=list[InsuranceClaimResponse])
def get_pending_claims(
    compagnie_id: Optional[str] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.comptable, UserRole.admin]))
):
    """
    Récupère les créances d'assurance en attente
    Accessible uniquement aux comptables et admins
    """
    factures = InsuranceService.get_pending_claims(
        compagnie_id=compagnie_id,
        date_debut=date_debut,
        date_fin=date_fin,
        db=db
    )
    
    # Enrichir avec les informations patient
    result = []
    for facture in factures:
        patient = db.get(Patient, facture.patient_id)
        if not patient:
            continue
        
        # Récupérer l'assurance du patient
        compagnie_nom = "Non spécifié"
        if patient.assurance_id:
            insurance = db.get(Insurance, patient.assurance_id)
            if insurance:
                compagnie_nom = insurance.nom_compagnie
        
        result.append(InsuranceClaimResponse(
            facture_id=facture.id,
            numero_facture=facture.numero_facture,
            patient_nom=patient.nom,
            patient_prenom=patient.prenom,
            compagnie_assurance=compagnie_nom,
            montant_total=facture.montant_total,
            part_assurance=facture.part_assurance or 0,
            date_emission=facture.created_at.date(),
            statut=facture.statut.value
        ))
    
    return result


@router.post("/claims/validate")
def validate_insurance_payment(
    request: InsuranceValidatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.comptable, UserRole.admin]))
):
    """
    Valide le paiement d'une ou plusieurs créances d'assurance
    Accessible uniquement aux comptables et admins
    """
    try:
        success = InsuranceService.validate_payment(
            facture_ids=request.facture_ids,
            reference_paiement=request.reference_paiement,
            montant_paye=request.montant_paye,
            db=db
        )
        
        if success:
            return {
                "message": f"{len(request.facture_ids)} facture(s) validée(s) avec succès",
                "reference": request.reference_paiement
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Échec de la validation"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la validation: {str(e)}"
        )
