"""
Router pour le module Assurances
"""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.permissions import require_role
from app.models.user import User, UserRole
from app.models.insurance import Insurance
from app.models.invoice import FactureStatut
from app.models.patient import Patient
from app.schemas.insurance import (
    InsuranceResponse,
    InsuranceCompanyDetailOut,
    InsuranceCompanyCreate,
    InsuranceCompanyUpdate,
    InsuranceCalculateRequest,
    InsuranceCalculateResponse,
    InsuranceClaimResponse,
    InsuranceValidatePaymentRequest,
)
from app.services.insurance_service import InsuranceService
from app.services.insurance_company_api import (
    insurance_to_detail,
    apply_create,
    apply_update,
)

router = APIRouter(prefix="/insurance", tags=["Insurance"])

_admin_only = require_role([UserRole.admin])
_manage_roles = require_role(
    [UserRole.admin, UserRole.gestionnaire_assurance, UserRole.comptable]
)


def _statut_creance(statut: FactureStatut) -> tuple[str, str]:
    st = statut.value if hasattr(statut, "value") else str(statut)
    if st == FactureStatut.payee.value:
        return "remboursee", "Remboursée"
    if st in (FactureStatut.en_attente.value, FactureStatut.partielle.value, FactureStatut.brouillon.value):
        return "en_attente", "En attente"
    return "refusee", "Refusée"


@router.get("/companies", response_model=list[InsuranceResponse])
def get_insurance_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compagnies actives (accueil, caisse, etc.)."""
    insurances = db.scalars(
        select(Insurance).where(Insurance.est_active.is_(True)).order_by(Insurance.nom_compagnie)
    ).all()
    return insurances


@router.get("/companies/manage", response_model=list[InsuranceCompanyDetailOut])
def list_all_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(_manage_roles),
):
    """Toutes les compagnies (actives et inactives) pour la gestion admin."""
    insurances = db.scalars(
        select(Insurance).order_by(Insurance.nom_compagnie)
    ).all()
    return [insurance_to_detail(i) for i in insurances]


@router.post(
    "/companies",
    response_model=InsuranceCompanyDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_insurance_company(
    data: InsuranceCompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_only),
):
    """Création réservée à l'administrateur."""
    dup = db.scalars(
        select(Insurance).where(Insurance.nom_compagnie == data.nom_compagnie.strip())
    ).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une compagnie avec ce nom existe déjà",
        )
    ins = Insurance(
        nom_compagnie=data.nom_compagnie.strip(),
        taux_couverture=80,
        est_active=True,
    )
    apply_create(ins, data)
    db.add(ins)
    db.commit()
    db.refresh(ins)
    return insurance_to_detail(ins)


@router.put("/companies/{company_id}", response_model=InsuranceCompanyDetailOut)
def update_insurance_company(
    company_id: str,
    data: InsuranceCompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_only),
):
    ins = db.get(Insurance, company_id)
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compagnie introuvable")
    apply_update(ins, data)
    db.commit()
    db.refresh(ins)
    return insurance_to_detail(ins)


@router.patch("/companies/{company_id}/activate", response_model=InsuranceCompanyDetailOut)
def activate_insurance_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_only),
):
    ins = db.get(Insurance, company_id)
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compagnie introuvable")
    ins.est_active = True
    db.commit()
    db.refresh(ins)
    return insurance_to_detail(ins)


@router.patch("/companies/{company_id}/deactivate", response_model=InsuranceCompanyDetailOut)
def deactivate_insurance_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_only),
):
    ins = db.get(Insurance, company_id)
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compagnie introuvable")
    ins.est_active = False
    db.commit()
    db.refresh(ins)
    return insurance_to_detail(ins)


@router.post("/calculate", response_model=InsuranceCalculateResponse)
def calculate_insurance_coverage(
    request: InsuranceCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InsuranceService.calculate_coverage(
        patient_id=request.patient_id,
        montant_total=request.montant_total,
        type_acte=request.type_acte,
        db=db,
    )


@router.get("/claims/pending", response_model=list[InsuranceClaimResponse])
def get_pending_claims(
    compagnie_id: Optional[str] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.comptable, UserRole.admin])),
):
    factures = InsuranceService.get_pending_claims(
        compagnie_id=compagnie_id,
        date_debut=date_debut,
        date_fin=date_fin,
        db=db,
    )

    result = []
    for facture in factures:
        patient = db.get(Patient, facture.patient_id)
        if not patient:
            continue

        compagnie_nom = "Non spécifié"
        if patient.assurance_id:
            insurance = db.get(Insurance, patient.assurance_id)
            if insurance:
                compagnie_nom = insurance.nom_compagnie

        sc, sl = _statut_creance(facture.statut)
        result.append(
            InsuranceClaimResponse(
                facture_id=facture.id,
                numero_facture=facture.numero_facture,
                patient_nom=patient.nom,
                patient_prenom=patient.prenom,
                patient_code=patient.code_patient,
                compagnie_assurance=compagnie_nom,
                montant_total=facture.montant_total,
                part_assurance=facture.part_assurance or 0,
                date_emission=facture.created_at.date(),
                statut=facture.statut.value,
                statut_creance=sc,
                statut_creance_label=sl,
            )
        )

    return result


@router.post("/claims/validate")
def validate_insurance_payment(
    request: InsuranceValidatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.comptable, UserRole.admin])),
):
    try:
        success = InsuranceService.validate_payment(
            facture_ids=request.facture_ids,
            reference_paiement=request.reference_paiement,
            montant_paye=request.montant_paye,
            db=db,
        )

        if success:
            return {
                "message": f"{len(request.facture_ids)} facture(s) validée(s) avec succès",
                "reference": request.reference_paiement,
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Échec de la validation",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la validation: {str(e)}",
        )
