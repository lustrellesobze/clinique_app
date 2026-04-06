"""
Router pour le module Hospitalisation
"""
from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models import Hospitalization, Room, Patient, User, Facture, LigneFacture
from app.schemas.hospitalization import (
    RoomResponse,
    HospitalizationCreate,
    HospitalizationResponse,
    HospitalizationDischarge,
    HospitalizationDischargeResponse
)

router = APIRouter(prefix="/hospitalization", tags=["hospitalization"])


@router.get("/rooms", response_model=List[RoomResponse])
async def get_available_rooms(
    type_chambre: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des chambres disponibles
    """
    # Vérifier les permissions
    if current_user.role not in ["resp_hospit", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Construire la requête
    query = db.query(Room)
    
    if type_chambre:
        query = query.filter(Room.type_chambre == type_chambre)
    
    rooms = query.order_by(Room.numero).all()
    
    return rooms


@router.post("/admissions", response_model=HospitalizationResponse)
async def admit_patient(
    admission_data: HospitalizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admet un patient en hospitalisation
    """
    # Vérifier les permissions
    if current_user.role not in ["resp_hospit", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Vérifier que la chambre existe et est disponible
    room = db.query(Room).filter(Room.id == admission_data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    if not room.est_disponible:
        raise HTTPException(status_code=400, detail="Chambre non disponible")
    
    # Vérifier l'acompte minimum (50% du tarif journalier)
    acompte_minimum = room.tarif_journalier_fcfa * Decimal("0.5")
    if admission_data.acompte_verse_fcfa < acompte_minimum:
        raise HTTPException(
            status_code=400,
            detail=f"Acompte insuffisant. Minimum requis: {acompte_minimum} FCFA"
        )
    
    # Vérifier que le patient existe
    patient = db.query(Patient).filter(Patient.id == admission_data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Créer l'hospitalisation
    hospitalization = Hospitalization(
        patient_id=admission_data.patient_id,
        room_id=admission_data.room_id,
        medecin_id=admission_data.medecin_id,
        date_admission=admission_data.date_admission,
        motif_hospitalisation=admission_data.motif_hospitalisation,
        acompte_verse_fcfa=admission_data.acompte_verse_fcfa,
        montant_total_fcfa=0,
        statut="en_cours"
    )
    db.add(hospitalization)
    
    # Marquer la chambre comme occupée
    room.est_disponible = False
    
    db.commit()
    db.refresh(hospitalization)
    
    # Récupérer le médecin si spécifié
    medecin_name = None
    if admission_data.medecin_id:
        medecin = db.query(User).filter(User.id == admission_data.medecin_id).first()
        if medecin:
            medecin_name = f"Dr. {medecin.nom} {medecin.prenom}"
    
    return HospitalizationResponse(
        id=hospitalization.id,
        patient_id=hospitalization.patient_id,
        patient_name=f"{patient.nom} {patient.prenom}",
        room_numero=room.numero,
        room_type=room.type_chambre,
        medecin_name=medecin_name,
        date_admission=hospitalization.date_admission,
        date_sortie=hospitalization.date_sortie,
        motif_hospitalisation=hospitalization.motif_hospitalisation,
        acompte_verse_fcfa=hospitalization.acompte_verse_fcfa,
        montant_total_fcfa=hospitalization.montant_total_fcfa,
        statut=hospitalization.statut,
        tarif_journalier=room.tarif_journalier_fcfa,
        nombre_jours=0
    )


@router.get("/active", response_model=List[HospitalizationResponse])
async def get_active_hospitalizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des hospitalisations en cours
    """
    # Vérifier les permissions
    if current_user.role not in ["resp_hospit", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    hospitalizations = db.query(Hospitalization).filter(
        Hospitalization.statut == "en_cours"
    ).order_by(Hospitalization.date_admission.desc()).all()
    
    result = []
    for hosp in hospitalizations:
        patient = db.query(Patient).filter(Patient.id == hosp.patient_id).first()
        room = db.query(Room).filter(Room.id == hosp.room_id).first()
        
        medecin_name = None
        if hosp.medecin_id:
            medecin = db.query(User).filter(User.id == hosp.medecin_id).first()
            if medecin:
                medecin_name = f"Dr. {medecin.nom} {medecin.prenom}"
        
        # Calculer le nombre de jours
        nombre_jours = (datetime.now() - hosp.date_admission).days + 1
        
        result.append(HospitalizationResponse(
            id=hosp.id,
            patient_id=hosp.patient_id,
            patient_name=f"{patient.nom} {patient.prenom}" if patient else "Inconnu",
            room_numero=room.numero if room else "Inconnue",
            room_type=room.type_chambre if room else "Inconnue",
            medecin_name=medecin_name,
            date_admission=hosp.date_admission,
            date_sortie=hosp.date_sortie,
            motif_hospitalisation=hosp.motif_hospitalisation,
            acompte_verse_fcfa=hosp.acompte_verse_fcfa,
            montant_total_fcfa=hosp.montant_total_fcfa,
            statut=hosp.statut,
            tarif_journalier=room.tarif_journalier_fcfa if room else 0,
            nombre_jours=nombre_jours
        ))
    
    return result


@router.post("/discharge", response_model=HospitalizationDischargeResponse)
async def discharge_patient(
    discharge_data: HospitalizationDischarge,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clôture une hospitalisation et génère la facture finale
    """
    # Vérifier les permissions
    if current_user.role not in ["resp_hospit", "admin"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Récupérer l'hospitalisation
    hospitalization = db.query(Hospitalization).filter(
        Hospitalization.id == discharge_data.hospitalization_id
    ).first()
    
    if not hospitalization:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")
    
    if hospitalization.statut != "en_cours":
        raise HTTPException(status_code=400, detail="Cette hospitalisation n'est pas en cours")
    
    # Récupérer la chambre
    room = db.query(Room).filter(Room.id == hospitalization.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    # Calculer le nombre de jours
    nombre_jours = (discharge_data.date_sortie - hospitalization.date_admission).days + 1
    if nombre_jours < 1:
        nombre_jours = 1
    
    # Calculer le montant total
    montant_total = room.tarif_journalier_fcfa * nombre_jours
    
    # Générer le numéro de facture
    year = datetime.now().year
    count = db.query(Facture).filter(
        Facture.numero_facture.like(f"FACT-HOSPIT-{year}-%")
    ).count()
    numero_facture = f"FACT-HOSPIT-{year}-{count + 1:05d}"
    
    # Créer la facture
    facture = Facture(
        numero_facture=numero_facture,
        patient_id=hospitalization.patient_id,
        montant_total_fcfa=montant_total,
        remise_fcfa=0,
        part_assurance_fcfa=0,
        part_patient_fcfa=montant_total - hospitalization.acompte_verse_fcfa,
        statut="payee" if discharge_data.mode_paiement else "en_attente",
        type_facture="hospitalisation"
    )
    db.add(facture)
    db.flush()
    
    # Ajouter les lignes de facture
    ligne = LigneFacture(
        facture_id=facture.id,
        designation=f"Hospitalisation - Chambre {room.numero} ({room.type_chambre})",
        quantite=nombre_jours,
        prix_unitaire_fcfa=room.tarif_journalier_fcfa,
        montant_total_fcfa=montant_total
    )
    db.add(ligne)
    
    # Mettre à jour l'hospitalisation
    hospitalization.date_sortie = discharge_data.date_sortie
    hospitalization.montant_total_fcfa = montant_total
    hospitalization.statut = "cloture"
    
    # Libérer la chambre
    room.est_disponible = True
    
    db.commit()
    db.refresh(facture)
    
    reste_a_payer = montant_total - hospitalization.acompte_verse_fcfa
    
    return HospitalizationDischargeResponse(
        hospitalization_id=hospitalization.id,
        facture_id=facture.id,
        numero_facture=facture.numero_facture,
        nombre_jours=nombre_jours,
        montant_total=montant_total,
        acompte_verse=hospitalization.acompte_verse_fcfa,
        reste_a_payer=reste_a_payer if reste_a_payer > 0 else 0
    )

