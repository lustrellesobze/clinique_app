from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FinanceByServiceOut(BaseModel):
    service: str
    montant_total: Decimal
    montant_regle: Decimal
    restant: Decimal
    factures: int


class FinanceDailyOut(BaseModel):
    jour: date
    montant_regle: Decimal


class FinanceDashboardOut(BaseModel):
    date_debut: date
    date_fin: date
    total_montant: Decimal
    total_regle: Decimal
    total_restant: Decimal
    par_service: list[FinanceByServiceOut]
    par_jour: list[FinanceDailyOut]


class ServicePopulaireOut(BaseModel):
    service: str
    libelle: str
    nombre: int
    pourcentage: float | None = None


class FactureAdminOut(BaseModel):
    id: str
    numero_facture: str
    patient_nom: str
    patient_prenom: str
    service: str
    service_label: str
    montant_total: Decimal
    montant_regle: Decimal
    statut: str
    statut_label: str
    date_emission: date


class FacturesQuickStatsOut(BaseModel):
    total_facture: Decimal
    payees_count: int
    payees_montant: Decimal
    en_attente_count: int
    en_attente_montant: Decimal
    impayees_count: int
    impayees_montant: Decimal


class FacturesAdminListOut(BaseModel):
    total: int
    factures: list[FactureAdminOut]
    stats: FacturesQuickStatsOut


class ServiceRentabiliteOut(BaseModel):
    service: str
    libelle: str
    pourcentage: float
    montant_fcfa: Decimal


class StatsReportOut(BaseModel):
    """Statistiques & rapports (écran admin)."""

    periode_label: str
    ca_mois: Decimal
    ca_mois_variation_pct: float | None = None
    patients_mois: int
    patients_variation_pct: float | None = None
    taux_recouvrement: float
    factures_emises: int
    ca_7_jours: list[FinanceDailyOut]
    services_rentabilite: list[ServiceRentabiliteOut]


class FinanceSummaryOut(BaseModel):
    """Indicateurs du jour (écran admin tableau de bord)."""

    date_jour: date
    chiffre_affaires: Decimal
    chiffre_affaires_hier: Decimal
    variation_pct: float | None = None
    objectif_ca_fcfa: Decimal
    factures_total: int
    factures_payees: int
    factures_en_attente: int
    factures_impayees: int
    patients_enregistres: int
    services_plus_consultes: list[ServicePopulaireOut] = []
