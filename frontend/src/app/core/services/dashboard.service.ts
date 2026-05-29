import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface FinanceByServiceOut {
  service: string;
  montant_total: number;
  montant_regle: number;
  restant: number;
  factures: number;
}

export interface FinanceDailyOut {
  jour: string; // YYYY-MM-DD
  montant_regle: number;
}

export interface FinanceDashboardOut {
  date_debut: string;
  date_fin: string;
  total_montant: number;
  total_regle: number;
  total_restant: number;
  par_service: FinanceByServiceOut[];
  par_jour: FinanceDailyOut[];
}

export interface ServicePopulaire {
  service: string;
  libelle: string;
  nombre: number;
  pourcentage: number | null;
}

export interface ServiceRentabilite {
  service: string;
  libelle: string;
  pourcentage: number;
  montant_fcfa: number;
}

export interface StatsReportOut {
  periode_label: string;
  ca_mois: number;
  ca_mois_variation_pct: number | null;
  patients_mois: number;
  patients_variation_pct: number | null;
  taux_recouvrement: number;
  factures_emises: number;
  ca_7_jours: FinanceDailyOut[];
  services_rentabilite: ServiceRentabilite[];
}

export interface FinanceSummaryOut {
  date_jour: string;
  chiffre_affaires: number;
  chiffre_affaires_hier: number;
  variation_pct: number | null;
  objectif_ca_fcfa: number;
  factures_total: number;
  factures_payees: number;
  factures_en_attente: number;
  factures_impayees: number;
  patients_enregistres: number;
  services_plus_consultes: ServicePopulaire[];
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api/dashboard`;

  constructor(private http: HttpClient) {}

  getSummary(): Observable<FinanceSummaryOut> {
    return this.http.get<FinanceSummaryOut>(`${this.api}/summary`);
  }

  getStatsReport(): Observable<StatsReportOut> {
    return this.http.get<StatsReportOut>(`${this.api}/stats-report`);
  }

  getFinance(dateDebut?: string, dateFin?: string): Observable<FinanceDashboardOut> {
    let params = new HttpParams();
    if (dateDebut) params = params.set('date_debut', dateDebut);
    if (dateFin) params = params.set('date_fin', dateFin);
    return this.http.get<FinanceDashboardOut>(`${this.api}/finance`, { params });
  }

  downloadFinancePdf(dateDebut?: string, dateFin?: string) {
    let params = new HttpParams();
    if (dateDebut) params = params.set('date_debut', dateDebut);
    if (dateFin) params = params.set('date_fin', dateFin);
    return this.http.get(`${this.api}/finance/pdf`, { params, responseType: 'blob' });
  }
}
