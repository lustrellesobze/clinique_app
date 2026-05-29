"""Conversion modèle Insurance ↔ schémas API."""

from decimal import Decimal

from app.models.insurance import Insurance
from app.schemas.insurance import (
    InsuranceCompanyDetailOut,
    InsuranceCompanyCreate,
    InsuranceCompanyUpdate,
    TauxParCategorie,
)
from app.services.insurance_details import parse_details, serialize_details


def insurance_to_detail(ins: Insurance) -> InsuranceCompanyDetailOut:
    details = parse_details(ins.exclusions, ins.taux_couverture)
    taux = details["taux_par_categorie"]
    return InsuranceCompanyDetailOut(
        id=ins.id,
        nom_compagnie=ins.nom_compagnie,
        taux_couverture=ins.taux_couverture,
        plafond_annuel_fcfa=ins.plafond_annuel_fcfa,
        est_active=ins.est_active,
        taux_par_categorie=TauxParCategorie(**taux),
        franchise_fcfa=details.get("franchise_fcfa"),
        franchise_libelle=details.get("franchise_libelle") or "Aucune",
        exclusions_list=details.get("exclusions_list") or [],
    )


def apply_create(ins: Insurance, data: InsuranceCompanyCreate) -> None:
    taux = data.taux_par_categorie.model_dump()
    ins.nom_compagnie = data.nom_compagnie.strip()
    ins.taux_couverture = int(taux.get("consultation", 80))
    ins.plafond_annuel_fcfa = data.plafond_annuel_fcfa
    ins.est_active = data.est_active
    ins.exclusions = serialize_details(
        taux_par_categorie=taux,
        franchise_fcfa=data.franchise_fcfa,
        franchise_libelle=data.franchise_libelle,
        exclusions_list=data.exclusions_list,
    )


def apply_update(ins: Insurance, data: InsuranceCompanyUpdate) -> None:
    current = parse_details(ins.exclusions, ins.taux_couverture)
    if data.nom_compagnie is not None:
        ins.nom_compagnie = data.nom_compagnie.strip()
    if data.taux_par_categorie is not None:
        current["taux_par_categorie"] = data.taux_par_categorie.model_dump()
        ins.taux_couverture = int(current["taux_par_categorie"].get("consultation", 80))
    if data.plafond_annuel_fcfa is not None:
        ins.plafond_annuel_fcfa = data.plafond_annuel_fcfa
    if data.franchise_fcfa is not None:
        current["franchise_fcfa"] = float(data.franchise_fcfa)
    if data.franchise_libelle is not None:
        current["franchise_libelle"] = data.franchise_libelle
    if data.exclusions_list is not None:
        current["exclusions_list"] = data.exclusions_list
    if data.est_active is not None:
        ins.est_active = data.est_active
    fcfa = current.get("franchise_fcfa")
    franchise_dec = Decimal(str(fcfa)) if fcfa is not None else None
    ins.exclusions = serialize_details(
        taux_par_categorie=current["taux_par_categorie"],
        franchise_fcfa=franchise_dec,
        franchise_libelle=current.get("franchise_libelle"),
        exclusions_list=current.get("exclusions_list") or [],
    )
