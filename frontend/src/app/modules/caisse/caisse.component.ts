import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import {
  CaisseService,
  FactureOut,
  LigneFactureIn,
  MobilePaymentInitOut,
  PaiementOut,
  PaymentStatusOut,
  PatientCaisse,
} from '../../core/services/caisse.service';

@Component({
  selector: 'app-caisse',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './caisse.component.html',
  styleUrls: ['./caisse.component.scss'],
})
export class CaisseComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly caisse = inject(CaisseService);

  loadingSearch = false;
  searchingError = '';
  creatingInvoice = false;
  paying = false;
  successMsg = '';
  errorMsg = '';

  patients: PatientCaisse[] = [];
  patientSelected: PatientCaisse | null = null;
  factures: FactureOut[] = [];
  factureSelected: FactureOut | null = null;
  paiementsFacture: PaiementOut[] = [];
  mobileInit: MobilePaymentInitOut | null = null;
  mobileStatus: PaymentStatusOut | null = null;
  private ws: WebSocket | null = null;

  searchForm = this.fb.group({
    q: ['', [Validators.required, Validators.minLength(2)]],
  });

  invoiceForm = this.fb.group({
    designation: ['Consultation', [Validators.required]],
    quantite: [1, [Validators.required, Validators.min(1)]],
    prix_unitaire: [5000, [Validators.required, Validators.min(0)]],
    remise_montant: [0, [Validators.required, Validators.min(0)]],
    commentaire: [''],
  });

  paymentForm = this.fb.group({
    montant: [0, [Validators.required, Validators.min(1)]],
    mode_paiement: [
      'especes' as
        | 'especes'
        | 'mtn_momo'
        | 'orange_money'
        | 'carte'
        | 'assurance'
        | 'mixte',
      Validators.required,
    ],
    reference_transaction: [''],
    montant_recu: [0, [Validators.min(0)]],
    montant_especes: [0, [Validators.min(0)]],
    montant_mobile: [0, [Validators.min(0)]],
    mode_mobile: ['orange_money' as 'orange_money' | 'mtn_momo'],
    reference_mobile: [''],
  });

  get totalSaisie(): number {
    const qte = Number(this.invoiceForm.get('quantite')?.value ?? 0);
    const pu = Number(this.invoiceForm.get('prix_unitaire')?.value ?? 0);
    const rem = Number(this.invoiceForm.get('remise_montant')?.value ?? 0);
    return Math.max(0, qte * pu - rem);
  }

  get monnaieARendre(): number {
    const recu = Number(this.paymentForm.get('montant_recu')?.value ?? 0);
    const montant = Number(this.paymentForm.get('montant')?.value ?? 0);
    return Math.max(0, recu - montant);
  }

  ngOnInit(): void {
    this.connectRealtime();
  }

  ngOnDestroy(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  onSearchPatient(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }
    this.resetAlerts();
    this.loadingSearch = true;
    const q = (this.searchForm.get('q')?.value ?? '').trim();
    this.caisse.rechercherPatients(q).subscribe({
      next: (rows) => {
        this.loadingSearch = false;
        this.patients = rows;
        if (rows.length === 0) {
          this.searchingError = 'Aucun patient trouvé pour ce critère.';
        } else {
          this.searchingError = '';
        }
      },
      error: (err: HttpErrorResponse) => {
        this.loadingSearch = false;
        this.searchingError = this.errorFromHttp(err);
      },
    });
  }

  choisirPatient(p: PatientCaisse): void {
    this.patientSelected = p;
    this.factureSelected = null;
    this.paiementsFacture = [];
    this.mobileInit = null;
    this.mobileStatus = null;
    this.paymentForm.patchValue({ montant: 0, mode_paiement: 'especes' });
    this.chargerFactures(p.id);
  }

  private chargerFactures(patientId: string): void {
    this.caisse.listerFacturesPatient(patientId).subscribe({
      next: (rows) => {
        this.factures = rows;
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  creerFacture(): void {
    if (!this.patientSelected) {
      this.errorMsg = 'Sélectionnez un patient avant de créer la facture.';
      return;
    }
    if (this.invoiceForm.invalid) {
      this.invoiceForm.markAllAsTouched();
      return;
    }
    this.resetAlerts();
    this.creatingInvoice = true;
    const ligne: LigneFactureIn = {
      designation: String(this.invoiceForm.get('designation')?.value ?? '').trim(),
      quantite: Number(this.invoiceForm.get('quantite')?.value ?? 1),
      prix_unitaire: Number(this.invoiceForm.get('prix_unitaire')?.value ?? 0),
      remise_montant: Number(this.invoiceForm.get('remise_montant')?.value ?? 0),
    };
    const commentaire = String(this.invoiceForm.get('commentaire')?.value ?? '').trim();
    this.caisse
      .creerFactureConsultation(this.patientSelected.id, commentaire, [ligne])
      .subscribe({
        next: (inv) => {
          this.creatingInvoice = false;
          this.successMsg = `Facture créée: ${inv.numero_facture}`;
          this.chargerFactures(this.patientSelected!.id);
          this.selectionnerFacture(inv.id);
        },
        error: (err: HttpErrorResponse) => {
          this.creatingInvoice = false;
          this.errorMsg = this.errorFromHttp(err);
        },
      });
  }

  selectionnerFacture(factureId: string): void {
    const inv = this.factures.find((x) => x.id === factureId) ?? null;
    this.factureSelected = inv;
    if (inv) {
      const remaining = Number(inv.restant_a_payer) || 0;
      this.paymentForm.patchValue({
        montant: remaining,
        montant_recu: remaining,
        montant_especes: remaining,
        montant_mobile: 0,
        mode_paiement: 'especes',
        reference_transaction: '',
        reference_mobile: '',
      });
      this.chargerPaiements(inv.id);
    }
  }

  private chargerPaiements(factureId: string): void {
    this.caisse.listerPaiementsFacture(factureId).subscribe({
      next: (rows) => {
        this.paiementsFacture = rows;
      },
      error: () => {
        this.paiementsFacture = [];
      },
    });
  }

  encaisser(): void {
    if (!this.factureSelected) {
      this.errorMsg = 'Sélectionnez une facture à encaisser.';
      return;
    }
    if (this.paymentForm.invalid) {
      this.paymentForm.markAllAsTouched();
      return;
    }
    this.resetAlerts();
    this.paying = true;
    const montant = Number(this.paymentForm.get('montant')?.value ?? 0);
    const mode = this.paymentForm.get('mode_paiement')?.value ?? 'especes';
    const restant = Number(this.factureSelected.restant_a_payer ?? 0);

    if (mode === 'carte') {
      this.paying = false;
      this.errorMsg =
        "Paiement par carte indisponible pour le moment (terminal non fourni).";
      return;
    }

    if (mode === 'mtn_momo' || mode === 'orange_money') {
      const ref = String(
        this.paymentForm.get('reference_transaction')?.value ?? ''
      ).trim();
      this.caisse
        .initierPaiementMobile(this.factureSelected.id, mode, montant, ref || null)
        .subscribe({
          next: (init) => {
            this.paying = false;
            this.mobileInit = init;
            this.mobileStatus = null;
            this.successMsg =
              'Paiement mobile initié. Scanner le QR puis confirmer.';
            this.chargerPaiements(this.factureSelected!.id);
          },
          error: (err: HttpErrorResponse) => this.onPaymentError(err),
        });
      return;
    }

    if (mode === 'mixte') {
      const cash = Number(this.paymentForm.get('montant_especes')?.value ?? 0);
      const mobile = Number(this.paymentForm.get('montant_mobile')?.value ?? 0);
      const mobileMode =
        this.paymentForm.get('mode_mobile')?.value === 'mtn_momo'
          ? 'mtn_momo'
          : 'orange_money';
      const mobileRef = String(
        this.paymentForm.get('reference_mobile')?.value ?? ''
      ).trim();
      const sum = cash + mobile;
      if (sum <= 0) {
        this.paying = false;
        this.errorMsg = 'Saisissez au moins une partie de paiement.';
        return;
      }
      if (sum > restant) {
        this.paying = false;
        this.errorMsg = `Le total mixte (${sum}) dépasse le reste à payer (${restant}).`;
        return;
      }
      if (mobile > 0 && !mobileRef) {
        this.paying = false;
        this.errorMsg = 'Référence mobile obligatoire pour la partie mobile.';
        return;
      }
      if (cash > 0) {
        this.caisse
          .encaisser(this.factureSelected.id, cash, 'especes', null)
          .subscribe({
            next: () => {
              if (mobile > 0) {
                this.caisse
                  .encaisser(this.factureSelected!.id, mobile, mobileMode, mobileRef)
                  .subscribe({
                    next: () => this.afterPaymentSuccess('Paiement mixte enregistré.'),
                    error: (err: HttpErrorResponse) => this.onPaymentError(err),
                  });
                return;
              }
              this.afterPaymentSuccess('Paiement en espèces enregistré.');
            },
            error: (err: HttpErrorResponse) => this.onPaymentError(err),
          });
        return;
      }
      this.caisse
        .encaisser(this.factureSelected.id, mobile, mobileMode, mobileRef)
        .subscribe({
          next: () => this.afterPaymentSuccess('Paiement mobile enregistré.'),
          error: (err: HttpErrorResponse) => this.onPaymentError(err),
        });
      return;
    }

    if (montant > restant) {
      this.paying = false;
      this.errorMsg = `Le montant dépasse le reste à payer (${restant}).`;
      return;
    }
    const ref =
      mode === 'especes'
        ? null
        : String(this.paymentForm.get('reference_transaction')?.value ?? '').trim();

    this.caisse.encaisser(this.factureSelected.id, montant, mode, ref).subscribe({
      next: () => this.afterPaymentSuccess('Paiement enregistré avec succès.'),
      error: (err: HttpErrorResponse) => this.onPaymentError(err),
    });
  }

  verifierStatutMobile(): void {
    if (!this.mobileInit?.payment.id) {
      return;
    }
    this.caisse.statutPaiementMobile(this.mobileInit.payment.id).subscribe({
      next: (s) => {
        this.mobileStatus = s;
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  confirmerMobileMock(): void {
    if (!this.mobileInit?.payment.id) {
      return;
    }
    this.paying = true;
    this.caisse.confirmerPaiementMobile(this.mobileInit.payment.id).subscribe({
      next: (s) => {
        this.paying = false;
        this.mobileStatus = s;
        this.successMsg = 'Paiement mobile confirmé.';
        if (this.patientSelected) {
          this.chargerFactures(this.patientSelected.id);
        }
        if (this.factureSelected) {
          this.chargerPaiements(this.factureSelected.id);
        }
      },
      error: (err: HttpErrorResponse) => this.onPaymentError(err),
    });
  }

  ouvrirPdfFacture(factureId: string): void {
    window.open(this.caisse.getInvoicePdfUrl(factureId), '_blank');
  }

  private afterPaymentSuccess(message: string): void {
    this.paying = false;
    this.successMsg = message;
    if (this.patientSelected) {
      this.chargerFactures(this.patientSelected.id);
    }
    if (this.factureSelected) {
      this.chargerPaiements(this.factureSelected.id);
    }
  }

  private onPaymentError(err: HttpErrorResponse): void {
    this.paying = false;
    this.errorMsg = this.errorFromHttp(err);
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }

  private errorFromHttp(err: HttpErrorResponse): string {
    const d = err.error?.detail;
    if (typeof d === 'string') {
      return d;
    }
    if (Array.isArray(d)) {
      return d
        .map((x: { msg?: string }) => x?.msg)
        .filter(Boolean)
        .join(' ');
    }
    return `Erreur ${err.status || 500}. Réessayez.`;
  }

  private resetAlerts(): void {
    this.successMsg = '';
    this.errorMsg = '';
  }

  private connectRealtime(): void {
    try {
      this.ws = new WebSocket(this.caisse.getCaisseWebSocketUrl());
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data ?? '{}') as {
            event?: string;
            invoice_id?: string;
            payment_status?: string;
          };
          if (msg.event === 'mobile_payment_updated') {
            this.successMsg = `Mise à jour mobile reçue: ${msg.payment_status ?? 'ok'}`;
            if (this.patientSelected) {
              this.chargerFactures(this.patientSelected.id);
            }
            if (this.factureSelected?.id && msg.invoice_id === this.factureSelected.id) {
              this.chargerPaiements(this.factureSelected.id);
            }
          }
        } catch {
          // Ignore malformed ws payload
        }
      };
      this.ws.onclose = () => {
        window.setTimeout(() => this.connectRealtime(), 3000);
      };
    } catch {
      // Ignore WS init failure in local offline mode
    }
  }
}
