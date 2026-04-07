"""
Routes API pour la gestion des ordonnances
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.prescription import Prescription
from app.models.patient import Patient
from app.services.pdf_service import PDFService


router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.get("/{prescription_id}/pdf")
def download_prescription_pdf(
    prescription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Télécharge une ordonnance en PDF"""
    # Récupérer l'ordonnance
    prescription = db.get(Prescription, prescription_id)
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordonnance non trouvée"
        )
    
    # Récupérer le patient
    patient = db.get(Patient, prescription.patient_id)
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé"
        )
    
    # Générer le PDF
    pdf_buffer = PDFService.generate_prescription_pdf(
        prescription=prescription,
        patient=patient
    )
    
    # Retourner le PDF
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ordonnance_{prescription.id}.pdf"
        }
    )

