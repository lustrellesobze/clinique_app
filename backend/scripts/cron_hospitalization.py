"""
Script CRON pour facturation journalière automatique des hospitalisations.

Exécution recommandée: tous les jours à 00:01
Windows Task Scheduler: python scripts/cron_hospitalization.py

Ce script:
1. Récupère tous les séjours en cours (date_sortie = NULL)
2. Crée une facture quotidienne pour chaque séjour
3. Vérifie si l'acompte est suffisant
4. Envoie des alertes si nécessaire
5. Logue toutes les opérations
"""
import sys
import logging
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models.hospitalization import Hospitalization
from app.models.invoice import Facture, FactureStatut
from app.models.patient import Patient
from app.models.room import Room
from app.models.user import User

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cron_hospitalization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_invoice_number(db: Session) -> str:
    """Génère un numéro de facture unique au format FACT-HOSPIT-YYYY-XXXXX"""
    year = datetime.now().year
    prefix = f"FACT-HOSPIT-{year}-"
    
    # Compter les factures d'hospitalisation de l'année
    count = db.query(Facture).filter(
        Facture.numero_facture.like(f"{prefix}%")
    ).count()
    
    return f"{prefix}{str(count + 1).zfill(5)}"


def calculate_days_since_admission(date_admission: datetime) -> int:
    """Calcule le nombre de jours depuis l'admission"""
    now = datetime.now()
    delta = now - date_admission
    return max(1, delta.days)  # Minimum 1 jour


def daily_billing() -> None:
    """
    Fonction principale de facturation journalière.
    
    Pour chaque séjour en cours:
    - Crée une facture quotidienne
    - Vérifie l'acompte
    - Logue l'opération
    """
    db: Session = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("DÉBUT DE LA FACTURATION JOURNALIÈRE DES HOSPITALISATIONS")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # Récupérer tous les séjours en cours
        active_hospitalizations = db.scalars(
            select(Hospitalization)
            .options(
                joinedload(Hospitalization.patient),
                joinedload(Hospitalization.room),
                joinedload(Hospitalization.medecin)
            )
            .where(Hospitalization.date_sortie.is_(None))
        ).all()
        
        logger.info(f"Nombre de séjours en cours: {len(active_hospitalizations)}")
        
        if not active_hospitalizations:
            logger.info("Aucun séjour en cours. Fin du traitement.")
            return
        
        invoices_created = 0
        total_amount = Decimal("0")
        warnings = []
        
        for hosp in active_hospitalizations:
            try:
                # Calculer le nombre de jours
                days = calculate_days_since_admission(hosp.date_admission)
                
                # Calculer le montant journalier
                daily_rate = hosp.room.tarif_journalier_fcfa
                
                # Générer le numéro de facture
                invoice_number = generate_invoice_number(db)
                
                # Créer la facture quotidienne
                invoice = Facture(
                    numero_facture=invoice_number,
                    patient_id=hosp.patient_id,
                    montant_total=float(daily_rate),
                    montant_regle=0.0,  # Sera déduit de l'acompte à la sortie
                    statut=FactureStatut.en_attente,
                    commentaire=f"Facturation journalière - Chambre {hosp.room.numero} - Jour {days}"
                )
                
                db.add(invoice)
                invoices_created += 1
                total_amount += daily_rate
                
                # Calculer le total accumulé
                total_accumulated = daily_rate * days
                
                # Vérifier si l'acompte est suffisant
                if hosp.acompte_verse_fcfa < total_accumulated:
                    warning_msg = (
                        f"[ALERTE] Patient: {hosp.patient.nom} {hosp.patient.prenom} "
                        f"(Chambre {hosp.room.numero}) - "
                        f"Acompte insuffisant: {hosp.acompte_verse_fcfa} FCFA / "
                        f"Total accumulé: {total_accumulated} FCFA"
                    )
                    warnings.append(warning_msg)
                    logger.warning(warning_msg)
                
                logger.info(
                    f"[OK] Facture créée: {invoice_number} - "
                    f"Patient: {hosp.patient.nom} {hosp.patient.prenom} - "
                    f"Chambre: {hosp.room.numero} - "
                    f"Montant: {daily_rate} FCFA - "
                    f"Jour: {days}"
                )
                
            except Exception as e:
                logger.error(
                    f"[ERREUR] Erreur lors du traitement du séjour {hosp.id}: {str(e)}"
                )
                continue
        
        # Commit toutes les factures
        db.commit()
        
        # Résumé
        logger.info("=" * 80)
        logger.info("RÉSUMÉ DE LA FACTURATION")
        logger.info(f"Factures créées: {invoices_created}")
        logger.info(f"Montant total facturé: {total_amount} FCFA")
        logger.info(f"Alertes acompte insuffisant: {len(warnings)}")
        logger.info("=" * 80)
        
        if warnings:
            logger.warning("\n[ALERTES ACOMPTE INSUFFISANT]:")
            for warning in warnings:
                logger.warning(warning)
        
        logger.info("FIN DE LA FACTURATION JOURNALIÈRE - SUCCÈS")
        
    except Exception as e:
        logger.error(f"[ERREUR CRITIQUE]: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        daily_billing()
    except Exception as e:
        logger.critical(f"Le script a échoué: {str(e)}")
        sys.exit(1)
