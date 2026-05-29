import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TauxParCategorie {
  consultation: number;
  imagerie: number;
  chirurgie: number;
  esthetique: number;
  hospitalisation: number;
}

export interface Insurance {
  id: string;
  nom_compagnie: string;
  taux_couverture: number;
  plafond_annuel_fcfa: number | null;
  est_active: boolean;
}

export interface InsuranceCompanyDetail extends Insurance {
  taux_par_categorie: TauxParCategorie;
  franchise_fcfa: number | null;
  franchise_libelle: string;
  exclusions_list: string[];
}

export interface InsuranceCompanyPayload {
  nom_compagnie: string;
  taux_par_categorie: TauxParCategorie;
  plafond_annuel_fcfa: number | null;
  franchise_fcfa: number | null;
  franchise_libelle: string | null;
  exclusions_list: string[];
  est_active: boolean;
}

export interface InsuranceCalculateRequest {
  patient_id: string;
  montant_total: number;
  type_acte: string;
}

export interface InsuranceCalculateResponse {
  est_assure: boolean;
  taux_couverture: number;
  part_assurance: number;
  part_patient: number;
  plafond_restant: number | null;
  est_exclu: boolean;
  message: string | null;
}

export interface InsuranceClaim {
  facture_id: string;
  numero_facture: string;
  patient_nom: string;
  patient_prenom: string;
  patient_code?: string | null;
  compagnie_assurance: string;
  montant_total: number;
  part_assurance: number;
  date_emission: string;
  statut: string;
  statut_creance: string;
  statut_creance_label: string;
}

export interface InsuranceValidatePaymentRequest {
  facture_ids: string[];
  reference_paiement: string;
  montant_paye: number;
}

export const DEFAULT_TAUX: TauxParCategorie = {
  consultation: 80,
  imagerie: 70,
  chirurgie: 50,
  esthetique: 0,
  hospitalisation: 100,
};

@Injectable({
  providedIn: 'root',
})
export class InsuranceService {
  private readonly apiUrl = `${environment.apiUrl.replace(/\/+$/, '')}/api/insurance`;

  constructor(private http: HttpClient) {}

  getCompanies(): Observable<Insurance[]> {
    return this.http.get<Insurance[]>(`${this.apiUrl}/companies`);
  }

  getCompaniesManage(): Observable<InsuranceCompanyDetail[]> {
    return this.http.get<InsuranceCompanyDetail[]>(`${this.apiUrl}/companies/manage`);
  }

  createCompany(payload: InsuranceCompanyPayload): Observable<InsuranceCompanyDetail> {
    return this.http.post<InsuranceCompanyDetail>(`${this.apiUrl}/companies`, payload);
  }

  updateCompany(
    id: string,
    payload: Partial<InsuranceCompanyPayload>
  ): Observable<InsuranceCompanyDetail> {
    return this.http.put<InsuranceCompanyDetail>(`${this.apiUrl}/companies/${id}`, payload);
  }

  activateCompany(id: string): Observable<InsuranceCompanyDetail> {
    return this.http.patch<InsuranceCompanyDetail>(
      `${this.apiUrl}/companies/${id}/activate`,
      {}
    );
  }

  deactivateCompany(id: string): Observable<InsuranceCompanyDetail> {
    return this.http.patch<InsuranceCompanyDetail>(
      `${this.apiUrl}/companies/${id}/deactivate`,
      {}
    );
  }

  calculateCoverage(
    request: InsuranceCalculateRequest
  ): Observable<InsuranceCalculateResponse> {
    return this.http.post<InsuranceCalculateResponse>(
      `${this.apiUrl}/calculate`,
      request
    );
  }

  getPendingClaims(
    compagnieId?: string,
    dateDebut?: string,
    dateFin?: string
  ): Observable<InsuranceClaim[]> {
    let params = new HttpParams();
    if (compagnieId) params = params.set('compagnie_id', compagnieId);
    if (dateDebut) params = params.set('date_debut', dateDebut);
    if (dateFin) params = params.set('date_fin', dateFin);

    return this.http.get<InsuranceClaim[]>(`${this.apiUrl}/claims/pending`, { params });
  }

  validatePayment(request: InsuranceValidatePaymentRequest): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/claims/validate`, request);
  }
}
