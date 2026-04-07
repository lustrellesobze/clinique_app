import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PharmacyItemDetail {
  id: string;
  nom_item: string;
  description?: string | null;
  prix_unitaire: number;
  quantite: number;
}

export interface PharmacyPrescriptionPending {
  id: string;
  patient_name: string;
  patient_id: string;
  medecin_name: string;
  date_prescription: string;
  items: PharmacyItemDetail[];
  montant_total: number;
}

export interface PharmacyInvoiceCreate {
  prescription_id: string;
  montant_total: number;
  remise_fidelite: number;
  part_assurance: number;
  part_patient: number;
  mode_paiement?: string;
}

export interface PharmacyInvoiceResponse {
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

@Injectable({ providedIn: 'root' })
export class PharmacyService {
  private apiUrl = '/api/pharmacy';

  constructor(private http: HttpClient) {}

  getPendingPrescriptions(): Observable<PharmacyPrescriptionPending[]> {
    return this.http.get<PharmacyPrescriptionPending[]>(`${this.apiUrl}/pending`);
  }

  substituteItem(itemId: string, equivalent_nom: string, motif?: string): Observable<PharmacyItemDetail> {
    return this.http.put<PharmacyItemDetail>(`${this.apiUrl}/items/${itemId}/substitute`, {
      equivalent_nom,
      motif: motif || null,
    });
  }

  createInvoice(data: PharmacyInvoiceCreate): Observable<PharmacyInvoiceResponse> {
    return this.http.post<PharmacyInvoiceResponse>(`${this.apiUrl}/invoices`, data);
  }
}
