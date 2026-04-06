import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Insurance {
  id: string;
  nom_compagnie: string;
  taux_couverture: number;
  plafond_annuel_fcfa: number | null;
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
  compagnie_assurance: string;
  montant_total: number;
  part_assurance: number;
  date_emission: string;
  statut: string;
}

export interface InsuranceValidatePaymentRequest {
  facture_ids: string[];
  reference_paiement: string;
  montant_paye: number;
}

@Injectable({
  providedIn: 'root'
})
export class InsuranceService {
  private apiUrl = `${environment.apiUrl}/insurance`;

  constructor(private http: HttpClient) {}

  getCompanies(): Observable<Insurance[]> {
    return this.http.get<Insurance[]>(`${this.apiUrl}/companies`);
  }

  calculateCoverage(request: InsuranceCalculateRequest): Observable<InsuranceCalculateResponse> {
    return this.http.post<InsuranceCalculateResponse>(`${this.apiUrl}/calculate`, request);
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

  validatePayment(request: InsuranceValidatePaymentRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/claims/validate`, request);
  }
}
