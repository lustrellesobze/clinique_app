"""
Liste canonique des médecins (accueil « Médecin attribué » + comptes de connexion).
nom / prénom sans préfixe « Dr » — l’interface ajoute « Dr » à l’affichage.
"""

from app.models.user import UserRole

# email, nom (famille), prénom, service
MEDECINS_DEMO: list[tuple[str, str, str, str]] = [
    ("medecin@demo.cm", "OWONA", "Jean", "Médecine"),
    ("medecin2@demo.cm", "NGUEMA", "Marie", "Médecine générale"),
    ("medecin3@demo.cm", "FOTSO", "Paul", "Pédiatrie"),
    ("medecin4@demo.cm", "MBARGA", "Eric", "Cardiologie"),
    ("medecin5@demo.cm", "TCHOUA", "Sophie", "Gynécologie"),
]

MEDECINS_AS_SEED_USERS: list[tuple] = [
    (UserRole.medecin, email, nom, prenom, service)
    for email, nom, prenom, service in MEDECINS_DEMO
]
