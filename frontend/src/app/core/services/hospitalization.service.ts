import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Room {
  id: string;
  numero: string;
  type_chambre: string;
  tarif_journalier_fcfa: number;
  est_disponible: boolean;
  description?: string;
}

export interface HospitalizationCreate {
  patient_id: string;
  room_id: string;
  medecin_id?: string;
  motif_hospitalisation?: string;
  acompte_verse_fcfa: number;
  date_admission: string;
}

export interface HospitalizationResponse {
  id: string;
  patient_id: string;
  patient_name: string;
  room_numero: string;
  room_type: string;
  medecin_name?: string;
  date_admission: string;
  date_sortie?: string;
  motif_hospitalisation?: string;
  acompte_verse_fcfa: number;
  montant_total_fcfa: number;
  statut: string;
  tarif_journalier: number;
  nombre_jours: number;
}

export interface HospitalizationStats {
  chambres_occupees: number;
  chambres_total: number;
  ca_hospitalisation_fcfa: number;
  duree_moyenne_jours: number;
  patients_hospitalises: number;
  sejours_clotures: number;
}

export interface HospitalizationAdminRow {
  id: string;
  patient_id: string;
  patient_code: string;
  patient_name: string;
  room_numero: string;
  room_type: string;
  room_label: string;
  medecin_name?: string;
  date_admission: string;
  nombre_jours: number;
  frais_chambre_fcfa: number;
  total_facture_fcfa: number;
  acomptes_fcfa: number;
  solde_fcfa: number;
  motif_hospitalisation?: string;
  tarif_journalier: number;
  statut: string;
}

export interface HospitalizationDashboard {
  stats: HospitalizationStats;
  patients: HospitalizationAdminRow[];
  rooms_available: number;
}

export interface HospitalizationDischarge {
  hospitalization_id: string;
  date_sortie: string;
  mode_paiement: string;
  reference_paiement?: string;
}

export interface HospitalizationDischargeResponse {
  hospitalization_id: string;
  facture_id: string;
  numero_facture: string;
  nombre_jours: number;
  montant_total: number;
  acompte_verse: number;
  reste_a_payer: number;
}

export interface PatientLookupMini {
  id: string;
  code_patient: string;
  nom: string;
  prenom: string;
}

@Injectable({
  providedIn: 'root',
})
export class HospitalizationService {
  private readonly apiUrl = `${environment.apiUrl.replace(/\/+$/, '')}/api/hospitalization`;

  constructor(private http: HttpClient) {}

  getDashboard(): Observable<HospitalizationDashboard> {
    return this.http.get<HospitalizationDashboard>(`${this.apiUrl}/dashboard`);
  }

  getAvailableRooms(typeChambre?: string): Observable<Room[]> {
    let params = new HttpParams();
    if (typeChambre) {
      params = params.set('type_chambre', typeChambre);
    }
    return this.http.get<Room[]>(`${this.apiUrl}/rooms`, { params });
  }

  admitPatient(data: HospitalizationCreate): Observable<HospitalizationResponse> {
    return this.http.post<HospitalizationResponse>(`${this.apiUrl}/admissions`, data);
  }

  getActiveHospitalizations(): Observable<HospitalizationResponse[]> {
    return this.http.get<HospitalizationResponse[]>(`${this.apiUrl}/active`);
  }

  dischargePatient(data: HospitalizationDischarge): Observable<HospitalizationDischargeResponse> {
    return this.http.post<HospitalizationDischargeResponse>(`${this.apiUrl}/discharge`, data);
  }

  lookupPatient(code: string): Observable<PatientLookupMini> {
    const api = `${environment.apiUrl.replace(/\/+$/, '')}/api/patients/lookup/${encodeURIComponent(code.trim().toUpperCase())}`;
    return this.http.get<PatientLookupMini>(api);
  }
}
