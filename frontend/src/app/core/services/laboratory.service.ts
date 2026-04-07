import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PrescriptionItemDetail {
  id: string;
  nom_examen: string;
  prix_unitaire: number;
  quantite: number;
}

export interface PrescriptionPending {
  id: string;
  patient_name: string;
  patient_id: string;
  medecin_name: string;
  date_prescription: string;
  items: PrescriptionItemDetail[];
  montant_total: number;
}

export interface LaboratoryInvoiceCreate {
  prescription_id: string;
  montant_total: number;
  remise_fidelite: number;
  part_assurance: number;
  part_patient: number;
  mode_paiement: string;
  reference_paiement?: string;
}

export interface LaboratoryInvoiceResponse {
  id: string;
  numero_facture: string;
  patient_id: string;
  patient_name: string;
  montant_total: number;
  part_assurance: number;
  part_patient: number;
  statut: string;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class LaboratoryService {
  private apiUrl = '/api/laboratory';

  constructor(private http: HttpClient) {}

  getPendingPrescriptions(): Observable<PrescriptionPending[]> {
    return this.http.get<PrescriptionPending[]>(`${this.apiUrl}/pending`);
  }

  createInvoice(data: LaboratoryInvoiceCreate): Observable<LaboratoryInvoiceResponse> {
    return this.http.post<LaboratoryInvoiceResponse>(`${this.apiUrl}/invoices`, data);
  }
}
