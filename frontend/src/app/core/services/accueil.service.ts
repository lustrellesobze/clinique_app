import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface MedecinOption {
  id: string;
  nom: string;
  prenom: string;
}

export interface InscriptionPayload {
  nom: string;
  prenom: string;
  date_naissance: string | null;
  sexe: 'M' | 'F' | 'autre';
  telephone: string | null;
  email: string | null;
  contact_urgence: string | null;
  poids_kg: number | null;
  taille_cm: number | null;
  temperature_c: number | null;
  tension: string | null;
  motif_consultation: string;
  type_consultation:
    | 'generale'
    | 'rendez_vous'
    | 'specialiste'
    | 'urgence';
  medecin_id: string;
  derniere_date_regles: string | null;
  est_assure: boolean;
  compagnie_assurance: string | null;
  date_validite_assurance: string | null;
  numero_assure: string | null;
  montant_consultation_fcfa: number;
  remise_fcfa: number;
}

export interface InscriptionResponse {
  patient: {
    id: string;
    code_patient: string;
    nom: string;
    prenom: string;
    date_naissance: string | null;
    sexe: string | null;
    telephone: string | null;
    email: string | null;
  };
  passage: {
    id: string;
    total_fcfa: number;
    statut: string;
  };
  message_transfert: string;
}

@Injectable({ providedIn: 'root' })
export class AccueilService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api`;

  constructor(private http: HttpClient) {}

  listeMedecins(): Observable<MedecinOption[]> {
    return this.http.get<MedecinOption[]>(`${this.api}/accueil/medecins`);
  }

  enregistrerPatient(body: InscriptionPayload): Observable<InscriptionResponse> {
    return this.http.post<InscriptionResponse>(
      `${this.api}/accueil/inscriptions`,
      body
    );
  }
}
