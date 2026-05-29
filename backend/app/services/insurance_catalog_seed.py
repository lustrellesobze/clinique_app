"""Catalogue des assurances à créer / mettre à jour (seed)."""

from decimal import Decimal

from app.services.insurance_details import serialize_details

# (nom, taux_consultation défaut, plafond, actif, taux cat., franchise, exclusions texte)
CATALOG_INSURANCES: list[dict] = [
    {
        "nom_compagnie": "CNPS (Caisse Nationale de Prévoyance Sociale)",
        "taux_couverture": 80,
        "plafond_annuel_fcfa": Decimal("500000"),
        "est_active": True,
        "taux": {
            "consultation": 80,
            "imagerie": 70,
            "chirurgie": 50,
            "esthetique": 0,
            "hospitalisation": 100,
        },
        "franchise_libelle": "2 000 FCFA par consultation",
        "franchise_fcfa": Decimal("2000"),
        "exclusions_list": ["Chirurgie esthétique", "Dentaire cosmétique"],
    },
    {
        "nom_compagnie": "ASCOMA (Association Camerounaise de Mutualité)",
        "taux_couverture": 60,
        "plafond_annuel_fcfa": Decimal("300000"),
        "est_active": True,
        "taux": {
            "consultation": 60,
            "imagerie": 50,
            "chirurgie": 40,
            "esthetique": 0,
            "hospitalisation": 80,
        },
        "franchise_libelle": "Aucune",
        "franchise_fcfa": None,
        "exclusions_list": [],
    },
    {
        "nom_compagnie": "AXA Assurances",
        "taux_couverture": 70,
        "plafond_annuel_fcfa": Decimal("400000"),
        "est_active": False,
        "taux": {
            "consultation": 70,
            "imagerie": 60,
            "chirurgie": 45,
            "esthetique": 0,
            "hospitalisation": 75,
        },
        "franchise_libelle": "Aucune",
        "franchise_fcfa": None,
        "exclusions_list": ["esthetique"],
    },
    {
        "nom_compagnie": "ACTIVA Assurance",
        "taux_couverture": 75,
        "plafond_annuel_fcfa": Decimal("450000"),
        "est_active": True,
        "taux": {
            "consultation": 75,
            "imagerie": 65,
            "chirurgie": 45,
            "esthetique": 0,
            "hospitalisation": 90,
        },
        "franchise_libelle": "Aucune",
        "franchise_fcfa": None,
        "exclusions_list": [],
    },
    {
        "nom_compagnie": "Allianz",
        "taux_couverture": 70,
        "plafond_annuel_fcfa": Decimal("350000"),
        "est_active": True,
        "taux": {
            "consultation": 70,
            "imagerie": 60,
            "chirurgie": 40,
            "esthetique": 0,
            "hospitalisation": 85,
        },
        "franchise_libelle": "Aucune",
        "franchise_fcfa": None,
        "exclusions_list": [],
    },
    {
        "nom_compagnie": "Sanlam",
        "taux_couverture": 65,
        "plafond_annuel_fcfa": Decimal("320000"),
        "est_active": True,
        "taux": {
            "consultation": 65,
            "imagerie": 55,
            "chirurgie": 35,
            "esthetique": 0,
            "hospitalisation": 80,
        },
        "franchise_libelle": "Aucune",
        "franchise_fcfa": None,
        "exclusions_list": [],
    },
]


def build_exclusions_field(entry: dict) -> str:
    return serialize_details(
        taux_par_categorie=entry["taux"],
        franchise_fcfa=entry.get("franchise_fcfa"),
        franchise_libelle=entry.get("franchise_libelle"),
        exclusions_list=entry.get("exclusions_list") or [],
    )
