"""
Routes API pour la gestion des paiements et Mobile Money
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.mobile_money import MobileMoneyService, MobileMoneyProvider


router = APIRouter(prefix="/payments", tags=["payments"])


# Schémas Pydantic
class MobileMoneyPaymentRequest(BaseModel):
    facture_id: str
    montant: float
    telephone: str
    provider: str  # "mtn_momo" ou "orange_money"


class MobileMoneyPaymentResponse(BaseModel):
    transaction_id: str
    status: str
    message: str
    montant: float
    telephone: str


class MobileMoneyCallbackRequest(BaseModel):
    transaction_id: str
    success: bool
    error_message: Optional[str] = None


class TransactionStatusResponse(BaseModel):
    transaction_id: str
    status: str
    facture_id: str
    montant: float
    provider: str
    created_at: str
    updated_at: str


@router.post("/mobile-money/initiate", response_model=MobileMoneyPaymentResponse)
def initiate_mobile_money_payment(
    payment_request: MobileMoneyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initie un paiement Mobile Money (MTN MoMo ou Orange Money)
    """
    # Vérifier que l'utilisateur est caissier
    if current_user.role not in ["caissier_central", "caissier_labo", "caissier_imagerie", "caissier_pharmacie", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les caissiers peuvent initier des paiements"
        )
    
    # Vérifier le fournisseur
    if payment_request.provider not in [MobileMoneyProvider.MTN_MOMO, MobileMoneyProvider.ORANGE_MONEY]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fournisseur invalide. Utilisez 'mtn_momo' ou 'orange_money'"
        )
    
    try:
        result = MobileMoneyService.initiate_payment(
            db=db,
            facture_id=payment_request.facture_id,
            montant=payment_request.montant,
            telephone=payment_request.telephone,
            provider=payment_request.provider,
            caissier_id=current_user.id
        )
        
        return MobileMoneyPaymentResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'initiation du paiement: {str(e)}"
        )


@router.get("/mobile-money/status/{transaction_id}", response_model=TransactionStatusResponse)
def get_transaction_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère le statut d'une transaction Mobile Money
    """
    transaction = MobileMoneyService.get_transaction_status(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction non trouvée"
        )
    
    return TransactionStatusResponse(**transaction)


@router.post("/mobile-money/callback/mtn")
def mtn_momo_callback(
    callback_data: MobileMoneyCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint de callback pour MTN MoMo
    (En production, cet endpoint serait appelé par l'API MTN)
    """
    try:
        result = MobileMoneyService.simulate_mtn_callback(
            db=db,
            transaction_id=callback_data.transaction_id,
            success=callback_data.success
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement du callback: {str(e)}"
        )


@router.post("/mobile-money/callback/orange")
def orange_money_callback(
    callback_data: MobileMoneyCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint de callback pour Orange Money
    (En production, cet endpoint serait appelé par l'API Orange Money)
    """
    try:
        result = MobileMoneyService.simulate_orange_callback(
            db=db,
            transaction_id=callback_data.transaction_id,
            success=callback_data.success
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement du callback: {str(e)}"
        )
