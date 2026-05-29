import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PatientCaisse {
  id: string;
  code_patient: string;
  nom: string;
  prenom: string;
  telephone: string | null;
  medecin_id: string | null;
  assureur: string | null;
  medecin_nom?: string | null;
  batiment?: string | null;
  type_consultation_label?: string | null;
  motif_consultation?: string | null;
  montant_consultation_fcfa?: number | null;
  remise_passage_fcfa?: number | null;
}

export interface LigneFactureIn {
  designation: string;
  quantite: number;
  prix_unitaire: number;
  remise_montant: number;
}

export interface LigneFactureOut extends LigneFactureIn {
  id: string;
  ordre: number;
  montant_ligne: number;
}

export interface FactureOut {
  id: string;
  numero_facture: string;
  patient_id: string;
  statut: string;
  remise_globale: number;
  montant_total: number;
  montant_regle: number;
  restant_a_payer: number;
  devise: string;
  commentaire?: string | null;
  created_at: string | null;
  lignes: LigneFactureOut[];
  patient: PatientCaisse | null;
  medecin_nom?: string | null;
  batiment?: string | null;
  type_consultation_label?: string | null;
  code_patient?: string | null;
  paiements?: PaiementOut[];
}

export const MODE_PAIEMENT_LABELS: Record<string, string> = {
  especes: 'Espèces (Cash)',
  mtn_momo: 'MTN MoMo',
  orange_money: 'Orange Money',
  carte: 'Carte bancaire',
  assurance: 'Assurance',
};

export interface PaiementOut {
  id: string;
  facture_id: string;
  montant: number;
  mode_paiement: 'especes' | 'mtn_momo' | 'orange_money' | 'carte' | 'assurance';
  statut: string;
  reference_transaction: string | null;
  commentaire: string | null;
  created_at: string | null;
}

export interface MobilePaymentInitOut {
  payment: PaiementOut;
  qr_png_base64: string;
  qr_payload: string;
  instructions: string[];
  campay_active?: boolean;
  telephone?: string | null;
  payment_link?: string | null;
}

export interface PaymentStatusOut {
  payment_id: string;
  statut: string;
  facture_statut: string;
  montant_regle: number;
  restant_a_payer: number;
}

@Injectable({ providedIn: 'root' })
export class CaisseService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api`;

  constructor(private http: HttpClient) {}

  rechercherPatients(q: string): Observable<PatientCaisse[]> {
    const params = new HttpParams().set('q', q);
    return this.http.get<PatientCaisse[]>(`${this.api}/patients`, { params });
  }

  /** Chargement par ID exact (recommandé à la caisse). */
  chargerPatientParCode(code: string): Observable<PatientCaisse> {
    const codeNorm = encodeURIComponent(code.trim().toUpperCase());
    return this.http.get<PatientCaisse>(
      `${this.api}/patients/lookup/${codeNorm}`
    );
  }

  chargerQrPatient(code: string) {
    const codeNorm = encodeURIComponent(code.trim().toUpperCase());
    return this.http.get(`${this.api}/patients/qr/${codeNorm}`, {
      responseType: 'blob',
    });
  }

  creerFactureConsultation(
    patientId: string,
    commentaire: string,
    lignes: LigneFactureIn[]
  ): Observable<FactureOut> {
    return this.http.post<FactureOut>(`${this.api}/invoices`, {
      patient_id: patientId,
      commentaire: commentaire || null,
      lignes,
    });
  }

  /** Facture consultation unique à afficher à la caisse. */
  getFactureConsultationActive(patientId: string): Observable<FactureOut> {
    const params = new HttpParams().set('patient_id', patientId);
    return this.http.get<FactureOut>(`${this.api}/invoices/consultation-active`, {
      params,
    });
  }

  encaisser(
    factureId: string,
    montant: number,
    mode:
      | 'especes'
      | 'mtn_momo'
      | 'orange_money'
      | 'carte'
      | 'assurance',
    referenceTransaction: string | null
  ): Observable<PaiementOut> {
    return this.http.post<PaiementOut>(`${this.api}/payments`, {
      facture_id: factureId,
      montant,
      mode_paiement: mode,
      reference_transaction: referenceTransaction || null,
    });
  }

  listerPaiementsFacture(factureId: string): Observable<PaiementOut[]> {
    const params = new HttpParams().set('facture_id', factureId);
    return this.http.get<PaiementOut[]>(`${this.api}/payments`, { params });
  }

  initierPaiementMobile(
    factureId: string,
    provider: 'orange_money' | 'mtn_momo',
    montant: number,
    referenceTransaction: string | null,
    telephone: string | null
  ): Observable<MobilePaymentInitOut> {
    return this.http.post<MobilePaymentInitOut>(
      `${this.api}/payments/mobile/initiate`,
      {
        facture_id: factureId,
        provider,
        montant,
        reference_transaction: referenceTransaction || null,
        telephone: telephone?.trim() || null,
      }
    );
  }

  statutPaiementMobile(paymentId: string): Observable<PaymentStatusOut> {
    return this.http.get<PaymentStatusOut>(
      `${this.api}/payments/mobile/${paymentId}/status`
    );
  }

  confirmerPaiementMobile(paymentId: string): Observable<PaymentStatusOut> {
    return this.http.post<PaymentStatusOut>(
      `${this.api}/payments/mobile/${paymentId}/confirm`,
      {}
    );
  }

  getInvoicePdfUrl(invoiceId: string): string {
    return `${this.api}/invoices/${invoiceId}/pdf`;
  }

  telechargerFacturePdf(factureId: string) {
    return this.http.get(`${this.api}/invoices/${factureId}/pdf`, {
      responseType: 'blob',
    });
  }

  getCaisseWebSocketUrl(): string {
    const base = environment.apiUrl?.trim();
    if (base) {
      const normalized = base.replace(/\/+$/, '');
      const wsBase = normalized.startsWith('https://')
        ? normalized.replace('https://', 'wss://')
        : normalized.replace('http://', 'ws://');
      return `${wsBase}/api/webhooks/ws/caisse`;
    }
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/api/webhooks/ws/caisse`;
  }
}
