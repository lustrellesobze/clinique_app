"""
Service pour la gestion des assurances et calcul de couverture
"""
import json
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.insurance import Insurance
from app.models.patient import Patient
from app.models.invoice import Facture, FactureStatut
from app.schemas.insurance import InsuranceCalculateResponse
from app.services.insurance_details import (
    parse_details,
    taux_for_acte,
    is_acte_excluded,
)


class InsuranceService:
    """Service pour gérer les calculs d'assurance"""
    
    @staticmethod
    def calculate_coverage(
        patient_id: str,
        montant_total: Decimal,
        type_acte: str,
        db: Session
    ) -> InsuranceCalculateResponse:
        """
        Calcule la répartition assurance/patient
        
        Algorithme:
        1. Vérifier si patient assuré
        2. Vérifier validité assurance
        3. Récupérer taux de couverture
        4. Vérifier exclusions
        5. Calculer part assurance
        6. Vérifier plafond annuel
        7. Calculer part patient
        """
        # Récupérer le patient
        patient = db.get(Patient, patient_id)
        if not patient:
            return InsuranceCalculateResponse(
                est_assure=False,
                part_patient=montant_total,
                message="Patient non trouvé"
            )
        
        # Vérifier si le patient a une assurance
        if not patient.assurance_id:
            return InsuranceCalculateResponse(
                est_assure=False,
                part_patient=montant_total,
                message="Patient non assuré"
            )
        
        # Récupérer l'assurance
        insurance = db.get(Insurance, patient.assurance_id)
        if not insurance or not insurance.est_active:
            return InsuranceCalculateResponse(
                est_assure=False,
                part_patient=montant_total,
                message="Assurance inactive ou non trouvée"
            )
        
        details = parse_details(insurance.exclusions, insurance.taux_couverture)
        if is_acte_excluded(details, type_acte):
            return InsuranceCalculateResponse(
                est_assure=True,
                taux_couverture=0,
                part_assurance=Decimal("0"),
                part_patient=montant_total,
                est_exclu=True,
                message=f"Acte '{type_acte}' exclu de la couverture",
            )

        taux_pct = taux_for_acte(details, type_acte)
        taux = Decimal(taux_pct) / Decimal("100")
        part_assurance = montant_total * taux
        
        # Vérifier le plafond annuel
        plafond_restant = None
        if insurance.plafond_annuel_fcfa:
            # Calculer le total déjà utilisé cette année
            year_start = datetime(datetime.now().year, 1, 1)
            total_utilise = db.query(
                Facture.part_assurance
            ).filter(
                and_(
                    Facture.patient_id == patient_id,
                    Facture.created_at >= year_start,
                    Facture.part_assurance.isnot(None)
                )
            ).all()
            
            total_utilise_sum = sum(
                [Decimal(str(t[0])) for t in total_utilise if t[0] is not None],
                Decimal("0")
            )
            
            plafond_restant = insurance.plafond_annuel_fcfa - total_utilise_sum
            
            # Si le plafond est dépassé
            if plafond_restant <= 0:
                return InsuranceCalculateResponse(
                    est_assure=True,
                    taux_couverture=taux_pct,
                    part_assurance=Decimal("0"),
                    part_patient=montant_total,
                    plafond_restant=Decimal("0"),
                    message="Plafond annuel dépassé"
                )
            
            # Si la part assurance dépasse le plafond restant
            if part_assurance > plafond_restant:
                part_assurance = plafond_restant
                plafond_restant = Decimal("0")
            else:
                plafond_restant -= part_assurance
        
        # Calculer la part patient
        part_patient = montant_total - part_assurance
        
        return InsuranceCalculateResponse(
            est_assure=True,
            taux_couverture=taux_pct,
            part_assurance=part_assurance,
            part_patient=part_patient,
            plafond_restant=plafond_restant,
            message="Calcul effectué avec succès"
        )
    
    @staticmethod
    def get_pending_claims(
        compagnie_id: Optional[str],
        date_debut: Optional[date],
        date_fin: Optional[date],
        db: Session
    ) -> list[Facture]:
        """
        Récupère les créances assurance en attente
        """
        query = select(Facture).where(
            and_(
                Facture.part_assurance.isnot(None),
                Facture.part_assurance > 0,
                Facture.statut.in_([FactureStatut.en_attente, FactureStatut.partielle])
            )
        )
        
        # Filtrer par date si spécifié
        if date_debut:
            query = query.where(Facture.created_at >= datetime.combine(date_debut, datetime.min.time()))
        if date_fin:
            query = query.where(Facture.created_at <= datetime.combine(date_fin, datetime.max.time()))
        
        # TODO: Filtrer par compagnie (nécessite une jointure avec Patient et Insurance)
        
        return db.scalars(query).all()
    
    @staticmethod
    def validate_payment(
        facture_ids: list[str],
        reference_paiement: str,
        montant_paye: Decimal,
        db: Session
    ) -> bool:
        """
        Marque les factures comme payées par l'assurance
        """
        try:
            for facture_id in facture_ids:
                facture = db.get(Facture, facture_id)
                if facture and facture.part_assurance:
                    # Mettre à jour le montant réglé
                    facture.montant_regle = float(facture.montant_regle or 0) + float(facture.part_assurance)
                    
                    # Mettre à jour le statut
                    if facture.montant_regle >= facture.montant_total:
                        facture.statut = FactureStatut.payee
                    else:
                        facture.statut = FactureStatut.partielle
                    
                    # Ajouter la référence dans le commentaire
                    if facture.commentaire:
                        facture.commentaire += f"\nPaiement assurance: {reference_paiement}"
                    else:
                        facture.commentaire = f"Paiement assurance: {reference_paiement}"
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
