import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ImagingItemDetail {
  id: string;
  nom_examen: string;
  prix_unitaire: number;
  quantite: number;
}

export interface ImagingPrescriptionPending {
  id: string;
  patient_name: string;
  patient_id: string;
  medecin_name: string;
  date_prescription: string;
  items: ImagingItemDetail[];
  montant_total: number;
}

export interface ImagingInvoiceCreate {
  prescription_id: string;
  montant_total: number;
  remise_fidelite: number;
  part_assurance: number;
  part_patient: number;
  mode_paiement: string;
  reference_paiement?: string;
}

export interface ImagingInvoiceResponse {
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
export class ImagingService {
  private apiUrl = '/api/imaging';

  constructor(private http: HttpClient) {}

  getPendingPrescriptions(): Observable<ImagingPrescriptionPending[]> {
    return this.http.get<ImagingPrescriptionPending[]>(`${this.apiUrl}/pending`);
  }

  createInvoice(data: ImagingInvoiceCreate): Observable<ImagingInvoiceResponse> {
    return this.http.post<ImagingInvoiceResponse>(`${this.apiUrl}/invoices`, data);
  }
}
