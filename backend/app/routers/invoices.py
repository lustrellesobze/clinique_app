"""
Routes API pour la gestion des factures
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.invoice import Facture
from app.models.patient import Patient
from app.models.insurance import Insurance
from app.services.pdf_service import PDFService


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/{facture_id}/pdf")
def download_invoice_pdf(
    facture_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Télécharge une facture en PDF"""
    # Récupérer la facture
    facture = db.get(Facture, facture_id)
    
    if not facture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )
    
    # Récupérer le patient
    patient = db.get(Patient, facture.patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé"
        )
    
    # Récupérer l'assurance si applicable
    insurance = None
    if patient.assurance_id:
        insurance = db.get(Insurance, patient.assurance_id)
    
    # Générer le PDF
    pdf_buffer = PDFService.generate_invoice_pdf(
        facture=facture,
        patient=patient,
        insurance=insurance
    )
    
    # Retourner le PDF
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{facture.numero_facture}.pdf"
        }
    )

