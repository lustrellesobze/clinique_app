import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type RapportPeriode = 'journalier' | 'hebdomadaire' | 'mensuel' | 'trimestriel';

export interface FactureAdmin {
  id: string;
  numero_facture: string;
  patient_nom: string;
  patient_prenom: string;
  service: string;
  service_label: string;
  montant_total: number;
  montant_regle: number;
  statut: string;
  statut_label: string;
  date_emission: string;
}

export interface FacturesQuickStats {
  total_facture: number;
  payees_count: number;
  payees_montant: number;
  en_attente_count: number;
  en_attente_montant: number;
  impayees_count: number;
  impayees_montant: number;
}

export interface FacturesAdminList {
  total: number;
  factures: FactureAdmin[];
  stats: FacturesQuickStats;
}

@Injectable({ providedIn: 'root' })
export class FacturationService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api/dashboard`;

  constructor(private http: HttpClient) {}

  listFactures(params: {
    date_debut?: string;
    date_fin?: string;
    statut?: string;
    service?: string;
    recherche?: string;
  }): Observable<FacturesAdminList> {
    let p = new HttpParams();
    if (params.date_debut) p = p.set('date_debut', params.date_debut);
    if (params.date_fin) p = p.set('date_fin', params.date_fin);
    if (params.statut && params.statut !== 'tous') p = p.set('statut', params.statut);
    if (params.service && params.service !== 'tous') p = p.set('service', params.service);
    if (params.recherche?.trim()) p = p.set('recherche', params.recherche.trim());
    return this.http.get<FacturesAdminList>(`${this.api}/factures`, { params: p });
  }

  downloadReportPdf(periode: RapportPeriode, dateRef: string): Observable<Blob> {
    const params = new HttpParams()
      .set('periode', periode)
      .set('date_ref', dateRef);
    return this.http.get(`${this.api}/reports/pdf`, {
      params,
      responseType: 'blob',
    });
  }

  downloadReportExcel(periode: RapportPeriode, dateRef: string): Observable<Blob> {
    const params = new HttpParams()
      .set('periode', periode)
      .set('date_ref', dateRef);
    return this.http.get(`${this.api}/reports/excel`, {
      params,
      responseType: 'blob',
    });
  }
}
