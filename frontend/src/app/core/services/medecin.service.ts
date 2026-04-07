import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface DoctorPatient {
  patient_id: string;
  passage_id: string;
  code_patient: string;
  nom: string;
  prenom: string;
  telephone: string | null;
  assureur: string | null;
  statut_passage: string;
  type_consultation: string;
  created_at: string | null;
}

export interface ConsultationOut {
  passage_id: string;
  patient_id: string;
  statut: string;
  motif_consultation: string;
  poids_kg: number | null;
  taille_cm: number | null;
  temperature_c: number | null;
  tension: string | null;
}

export interface PrescriptionItemIn {
  nom_item: string;
  description: string | null;
  quantite: number;
  prix_unitaire: number;
}

export interface PrescriptionOut {
  id: string;
  patient_id: string;
  medecin_id: string;
  passage_accueil_id: string | null;
  type_prescription: string;
  statut: string;
  notes: string | null;
  created_at: string | null;
  items: {
    id: string;
    nom_item: string;
    description: string | null;
    quantite: number;
    prix_unitaire: number;
  }[];
}

export interface PatientRecordOut {
  patient_id: string;
  code_patient: string;
  nom: string;
  prenom: string;
  telephone: string | null;
  assureur: string | null;
  passages: ConsultationOut[];
  prescriptions: PrescriptionOut[];
}

@Injectable({ providedIn: 'root' })
export class MedecinService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api`;

  constructor(private http: HttpClient) {}

  listePatientsAffectes(): Observable<DoctorPatient[]> {
    return this.http.get<DoctorPatient[]>(`${this.api}/doctor/patients`);
  }

  dossierPatient(patientId: string): Observable<PatientRecordOut> {
    return this.http.get<PatientRecordOut>(`${this.api}/patients/${patientId}/record`);
  }

  updateConsultation(
    consultationId: string,
    body: {
      observations?: string;
      diagnostic?: string;
      statut?: 'en_consultation' | 'attente_paiement' | 'termine' | 'annule';
      poids_kg?: number | null;
      taille_cm?: number | null;
      temperature_c?: number | null;
      tension?: string | null;
    }
  ): Observable<ConsultationOut> {
    return this.http.put<ConsultationOut>(
      `${this.api}/consultations/${consultationId}`,
      body
    );
  }

  creerPrescription(body: {
    patient_id: string;
    passage_accueil_id?: string | null;
    type_prescription:
      | 'pharmacie'
      | 'laboratoire'
      | 'imagerie'
      | 'hospitalisation'
      | 'specialiste'
      | 'chirurgie'
      | 'orl';
    notes?: string | null;
    items: PrescriptionItemIn[];
  }): Observable<PrescriptionOut> {
    return this.http.post<PrescriptionOut>(`${this.api}/prescriptions`, body);
  }

  transfererPrescription(
    prescriptionId: string,
    destination:
      | 'pharmacie'
      | 'laboratoire'
      | 'imagerie'
      | 'hospitalisation'
      | 'specialiste'
      | 'chirurgie'
      | 'orl',
    commentaire: string | null
  ): Observable<PrescriptionOut> {
    return this.http.post<PrescriptionOut>(
      `${this.api}/prescriptions/${prescriptionId}/transfer`,
      { destination, commentaire }
    );
  }
}
