"""
Script complet pour créer toutes les données de test :
- Utilisateurs
- Patients
- Assurances
- Factures avec assurance
- Notifications
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.patient import Patient, Sexe
from app.models.insurance import Insurance
from app.models.invoice import Facture, FactureStatut, LigneFacture
from app.services.notification_service import NotificationService


def create_users(db: Session):
    """Crée des utilisateurs de test"""
    print("\n📋 Création des utilisateurs...")
    
    users_data = [
        {
            "email": "admin@demo.cm",
            "password": "demo123",
            "nom": "Admin",
            "prenom": "Système",
            "role": UserRole.admin
        },
        {
            "email": "medecin@demo.cm",
            "password": "demo123",
            "nom": "OWONA",
            "prenom": "Jean",
            "service": "Médecine",
            "role": UserRole.medecin,
        },
        {
            "email": "medecin2@demo.cm",
            "password": "demo123",
            "nom": "NGUEMA",
            "prenom": "Marie",
            "service": "Médecine générale",
            "role": UserRole.medecin,
        },
        {
            "email": "medecin3@demo.cm",
            "password": "demo123",
            "nom": "FOTSO",
            "prenom": "Paul",
            "service": "Pédiatrie",
            "role": UserRole.medecin,
        },
        {
            "email": "medecin4@demo.cm",
            "password": "demo123",
            "nom": "MBARGA",
            "prenom": "Eric",
            "service": "Cardiologie",
            "role": UserRole.medecin,
        },
        {
            "email": "medecin5@demo.cm",
            "password": "demo123",
            "nom": "TCHOUA",
            "prenom": "Sophie",
            "service": "Gynécologie",
            "role": UserRole.medecin,
        },
        {
            "email": "infirmier@demo.cm",
            "password": "demo123",
            "nom": "Ngo",
            "prenom": "Marie",
            "role": UserRole.infirmiere_accueil
        },
        {
            "email": "caissier@demo.cm",
            "password": "demo123",
            "nom": "Fotso",
            "prenom": "Paul",
            "role": UserRole.caissier_central
        },
        {
            "email": "labo@demo.cm",
            "password": "demo123",
            "nom": "Tchoua",
            "prenom": "Sophie",
            "role": UserRole.caissier_labo
        },
        {
            "email": "imagerie@demo.cm",
            "password": "demo123",
            "nom": "Mbarga",
            "prenom": "Eric",
            "role": UserRole.caissier_imagerie
        },
        {
            "email": "assurance@demo.cm",
            "password": "demo123",
            "nom": "Njoya",
            "prenom": "Fatima",
            "role": UserRole.gestionnaire_assurance
        },
    ]
    
    created_users = []
    for user_data in users_data:
        # Vérifier si l'utilisateur existe déjà
        existing = db.scalar(select(User).where(User.email == user_data["email"]))
        if existing:
            existing.nom = user_data["nom"]
            existing.prenom = user_data["prenom"]
            if user_data.get("service") is not None:
                existing.service = user_data.get("service")
            print(f"  ⚠️  {user_data['email']} mis à jour")
            created_users.append(existing)
            continue

        from app.core.security import hash_password
        user = User(
            id=str(uuid.uuid4()),
            email=user_data["email"],
            mot_de_passe_hash=hash_password(user_data["password"]),
            nom=user_data["nom"],
            prenom=user_data["prenom"],
            role=user_data["role"],
            service=user_data.get("service"),
            est_actif=True,
        )
        db.add(user)
        created_users.append(user)
        print(f"  ✅ {user_data['email']} - {user_data['role'].value}")
    
    db.commit()
    return created_users


def create_insurances(db: Session):
    """Crée des compagnies d'assurance"""
    print("\n🏥 Création des assurances...")
    
    insurances_data = [
        {
            "nom_compagnie": "SAHAM Assurance",
            "taux_couverture": 80,
            "plafond_annuel_fcfa": 5000000
        },
        {
            "nom_compagnie": "AXA Cameroun",
            "taux_couverture": 70,
            "plafond_annuel_fcfa": 3000000
        },
        {
            "nom_compagnie": "ACTIVA Assurance",
            "taux_couverture": 60,
            "plafond_annuel_fcfa": 2000000
        },
    ]
    
    created_insurances = []
    for ins_data in insurances_data:
        existing = db.scalar(select(Insurance).where(Insurance.nom_compagnie == ins_data["nom_compagnie"]))
        if existing:
            print(f"  ⚠️  {ins_data['nom_compagnie']} existe déjà")
            created_insurances.append(existing)
            continue
        
        insurance = Insurance(
            id=str(uuid.uuid4()),
            nom_compagnie=ins_data["nom_compagnie"],
            taux_couverture=ins_data["taux_couverture"],
            plafond_annuel_fcfa=ins_data["plafond_annuel_fcfa"],
            est_active=True
        )
        db.add(insurance)
        created_insurances.append(insurance)
        print(f"  ✅ {ins_data['nom_compagnie']} - {ins_data['taux_couverture']}%")
    
    db.commit()
    return created_insurances


def create_patients(db: Session, insurances: list):
    """Crée des patients de test"""
    print("\n👥 Création des patients...")
    
    patients_data = [
        {
            "nom": "Dupont",
            "prenom": "Jean",
            "sexe": Sexe.M,
            "date_naissance": datetime(1985, 5, 15),
            "telephone": "+237 670 00 00 01",
            "email": "jean.dupont@email.cm",
            "has_insurance": True
        },
        {
            "nom": "Martin",
            "prenom": "Marie",
            "sexe": Sexe.F,
            "date_naissance": datetime(1990, 8, 22),
            "telephone": "+237 670 00 00 02",
            "email": "marie.martin@email.cm",
            "has_insurance": True
        },
        {
            "nom": "Nguema",
            "prenom": "Paul",
            "sexe": Sexe.M,
            "date_naissance": datetime(1978, 3, 10),
            "telephone": "+237 670 00 00 03",
            "has_insurance": True
        },
        {
            "nom": "Kamdem",
            "prenom": "Sophie",
            "sexe": Sexe.F,
            "date_naissance": datetime(1995, 11, 5),
            "telephone": "+237 670 00 00 04",
            "has_insurance": False
        },
        {
            "nom": "Biya",
            "prenom": "Eric",
            "sexe": Sexe.M,
            "date_naissance": datetime(1982, 7, 18),
            "telephone": "+237 670 00 00 05",
            "has_insurance": False
        },
    ]
    
    created_patients = []
    for idx, patient_data in enumerate(patients_data):
        # Vérifier si le patient existe
        existing = db.scalar(
            select(Patient).where(
                Patient.nom == patient_data["nom"],
                Patient.prenom == patient_data["prenom"]
            )
        )
        if existing:
            print(f"  ⚠️  {patient_data['nom']} {patient_data['prenom']} existe déjà")
            created_patients.append(existing)
            continue
        
        patient = Patient(
            id=str(uuid.uuid4()),
            code_patient=f"PAT-{datetime.now().strftime('%Y%m%d')}-{idx+1:04d}",
            nom=patient_data["nom"],
            prenom=patient_data["prenom"],
            sexe=patient_data["sexe"],
            date_naissance=patient_data["date_naissance"],
            telephone=patient_data["telephone"],
            email=patient_data.get("email"),
            assurance_id=insurances[idx % len(insurances)].id if patient_data["has_insurance"] else None
        )
        db.add(patient)
        created_patients.append(patient)
        
        insurance_info = f" - Assuré: {insurances[idx % len(insurances)].nom_compagnie}" if patient_data["has_insurance"] else ""
        print(f"  ✅ {patient_data['nom']} {patient_data['prenom']}{insurance_info}")
    
    db.commit()
    return created_patients


def create_invoices(db: Session, patients: list):
    """Crée des factures de test"""
    print("\n💰 Création des factures...")
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    created_count = 0
    
    for idx, patient in enumerate(patients):
        # Créer 2-3 factures par patient
        num_invoices = 2 if idx % 2 == 0 else 3
        
        for j in range(num_invoices):
            montant_total = Decimal(30000 + (idx * 15000) + (j * 10000))
            
            # Calculer part assurance si patient assuré
            part_assurance = Decimal(0)
            part_patient = montant_total
            
            if patient.assurance_id:
                insurance = db.get(Insurance, patient.assurance_id)
                taux = Decimal(insurance.taux_couverture)
                part_assurance = montant_total * (taux / 100)
                part_patient = montant_total - part_assurance
            
            # Statuts variés
            statuts = [FactureStatut.en_attente, FactureStatut.partielle, FactureStatut.payee]
            statut = statuts[j % len(statuts)]
            
            facture = Facture(
                id=str(uuid.uuid4()),
                numero_facture=f"FAC-{timestamp}-{created_count + 1:04d}",
                patient_id=patient.id,
                montant_total=float(montant_total),
                montant_regle=float(montant_total) if statut == FactureStatut.payee else float(montant_total * Decimal(0.5)) if statut == FactureStatut.partielle else 0,
                part_assurance=float(part_assurance) if part_assurance > 0 else None,
                part_patient=float(part_patient) if part_assurance > 0 else None,
                statut=statut,
                created_at=datetime.now() - timedelta(days=idx * 2 + j)
            )
            db.add(facture)
            
            # Ajouter des lignes de facture
            lignes_data = [
                {"designation": "Consultation générale", "prix": 15000},
                {"designation": "Analyses laboratoire", "prix": 25000},
                {"designation": "Médicaments", "prix": float(montant_total) - 40000},
            ]
            
            for ordre, ligne_data in enumerate(lignes_data[:2]):  # 2 lignes par facture
                ligne = LigneFacture(
                    id=str(uuid.uuid4()),
                    facture_id=facture.id,
                    ordre=ordre,
                    designation=ligne_data["designation"],
                    quantite=1,
                    prix_unitaire=ligne_data["prix"],
                    remise_montant=0,
                    montant_ligne=ligne_data["prix"]
                )
                db.add(ligne)
            
            created_count += 1
            print(f"  ✅ {facture.numero_facture} - {patient.nom} - {montant_total:,.0f} FCFA ({statut.value})")
    
    db.commit()
    print(f"\n  Total: {created_count} factures créées")


def create_notifications(db: Session, users: list, patients: list):
    """Crée des notifications de test"""
    print("\n🔔 Création des notifications...")
    
    created_count = 0
    
    # Notifications pour chaque utilisateur
    for user in users:
        # 3-5 notifications par utilisateur
        num_notifs = 3 if user.role == UserRole.admin else 5
        
        for i in range(num_notifs):
            if user.role == UserRole.medecin:
                # Notifications d'assignation de patients
                patient = patients[i % len(patients)]
                NotificationService.notify_patient_assignment(
                    db=db,
                    medecin_id=user.id,
                    patient_name=f"{patient.nom} {patient.prenom}"
                )
            elif user.role == UserRole.caissier_central:
                # Notifications de paiement
                NotificationService.notify_payment_received(
                    db=db,
                    caissier_id=user.id,
                    montant=50000 + (i * 10000),
                    facture_numero=f"FAC-2026-{i+1:04d}"
                )
            elif user.role == UserRole.gestionnaire_assurance:
                # Notifications de créances d'assurance
                NotificationService.notify_insurance_claim(
                    db=db,
                    user_id=user.id,
                    montant=100000 + (i * 20000),
                    assurance_name="SAHAM Assurance"
                )
            else:
                # Notifications génériques
                NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    type_notification="alerte",
                    titre=f"Alerte système #{i+1}",
                    message=f"Ceci est une notification de test pour {user.prenom} {user.nom}."
                )
            
            created_count += 1
        
        print(f"  ✅ {num_notifs} notifications pour {user.email}")
    
    print(f"\n  Total: {created_count} notifications créées")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🚀 SEEDER COMPLET - Création de toutes les données de test")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 1. Créer les utilisateurs
        users = create_users(db)
        
        # 2. Créer les assurances
        insurances = create_insurances(db)
        
        # 3. Créer les patients
        patients = create_patients(db, insurances)
        
        # 4. Créer les factures
        create_invoices(db, patients)
        
        # 5. Créer les notifications
        create_notifications(db, users, patients)
        
        print("\n" + "=" * 60)
        print("✅ SEEDER TERMINÉ AVEC SUCCÈS!")
        print("=" * 60)
        print("\n📝 Identifiants de connexion:")
        print("  - Admin: admin@demo.cm / demo123")
        print("  - Médecin: medecin@demo.cm / demo123")
        print("  - Infirmier: infirmier@demo.cm / demo123")
        print("  - Caissier: caissier@demo.cm / demo123")
        print("  - Labo: labo@demo.cm / demo123")
        print("  - Imagerie: imagerie@demo.cm / demo123")
        print("  - Assurance: assurance@demo.cm / demo123")
        print("\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
