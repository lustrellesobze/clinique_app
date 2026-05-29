import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import {
  CaisseService,
  FactureOut,
  MODE_PAIEMENT_LABELS,
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
  readonly modePaiementLabels = MODE_PAIEMENT_LABELS;
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
  showFactureModal = false;
  qrPatientObjectUrl: string | null = null;
  private ws: WebSocket | null = null;
  private readonly codePatientPattern = /^P-\d{4}-\d{5}$/i;

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
    telephone_paiement: ['', [Validators.minLength(8)]],
  });

  /** Modes nécessitant un push Campay sur le téléphone du client. */
  get isMobileMoneyMode(): boolean {
    const mode = this.paymentForm.get('mode_paiement')?.value;
    return mode === 'orange_money' || mode === 'mtn_momo' || mode === 'mixte';
  }

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

  get facturePayee(): boolean {
    return (
      !!this.factureSelected &&
      Number(this.factureSelected.restant_a_payer) <= 0
    );
  }

  get paymentRecapLines(): string[] {
    const confirmed = this.paiementsFacture.filter(
      (p) => p.statut === 'confirme'
    );
    let especes = 0;
    let orange = 0;
    let mtn = 0;
    for (const p of confirmed) {
      const m = Number(p.montant) || 0;
      if (p.mode_paiement === 'especes') {
        especes += m;
      } else if (p.mode_paiement === 'orange_money') {
        orange += m;
      } else if (p.mode_paiement === 'mtn_momo') {
        mtn += m;
      }
    }
    const lines: string[] = [];
    if (especes > 0) {
      lines.push(`Espèces (Cash) : ${especes.toLocaleString('fr-FR')} FCFA`);
    }
    if (orange > 0) {
      lines.push(`Orange Money : ${orange.toLocaleString('fr-FR')} FCFA`);
    }
    if (mtn > 0) {
      lines.push(`MTN MoMo : ${mtn.toLocaleString('fr-FR')} FCFA`);
    }
    return lines;
  }

  get isPaiementMixte(): boolean {
    return this.paymentRecapLines.length > 1;
  }

  get caissierNom(): string {
    const u = this.auth.getCurrentUser();
    return u ? `${u.prenom} ${u.nom}`.trim() : '—';
  }

  get paymentModeDisplay(): string {
    if (this.isPaiementMixte) {
      return 'Mixte — ' + this.paymentRecapLines.join(' · ');
    }
    const last = this.paiementsFacture.filter((p) => p.statut === 'confirme').pop();
    if (last) {
      return this.labelMode(last.mode_paiement);
    }
    return '—';
  }

  get paymentReference(): string {
    const refs = this.paiementsFacture
      .filter((p) => p.statut === 'confirme' && p.reference_transaction)
      .map((p) => p.reference_transaction);
    return refs.length ? refs.join(' / ') : '—';
  }

  ngOnInit(): void {
    this.connectRealtime();
  }

  ngOnDestroy(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.qrPatientObjectUrl) {
      URL.revokeObjectURL(this.qrPatientObjectUrl);
    }
  }

  /** ID patient (P-2026-XXXXX) : chargement direct + facture préremplie. */
  chargerParId(): void {
    const q = (this.searchForm.get('q')?.value ?? '').trim();
    if (q.length < 3) {
      this.searchingError = 'Saisissez le code patient (ex. P-2026-00123).';
      return;
    }
    this.resetAlerts();
    this.loadingSearch = true;
    this.caisse.chargerPatientParCode(q).subscribe({
      next: (p) => {
        this.loadingSearch = false;
        this.patients = [p];
        this.searchingError = '';
        this.choisirPatient(p);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingSearch = false;
        this.searchingError = this.errorFromHttp(err);
      },
    });
  }

  onSearchPatient(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }
    const q = (this.searchForm.get('q')?.value ?? '').trim();
    if (this.codePatientPattern.test(q)) {
      this.chargerParId();
      return;
    }
    this.resetAlerts();
    this.loadingSearch = true;
    this.caisse.rechercherPatients(q).subscribe({
      next: (rows) => {
        this.loadingSearch = false;
        this.patients = rows;
        if (rows.length === 0) {
          this.searchingError = 'Aucun patient trouvé pour ce critère.';
        } else {
          this.searchingError = '';
          if (rows.length === 1) {
            this.choisirPatient(rows[0]);
          }
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
    if (p.montant_consultation_fcfa != null) {
      const label = p.type_consultation_label || 'Consultation';
      this.invoiceForm.patchValue({
        designation: `Consultation — ${label}`,
        quantite: 1,
        prix_unitaire: Number(p.montant_consultation_fcfa),
        remise_montant: Number(p.remise_passage_fcfa ?? 0),
      });
    }
    this.paymentForm.patchValue({
      telephone_paiement: p.telephone?.trim() || '',
    });
    this.chargerFactures(p.id);
  }

  private telephonePourMobile(): string | null {
    const t = String(this.paymentForm.get('telephone_paiement')?.value ?? '').trim();
    return t || this.patientSelected?.telephone?.trim() || null;
  }

  /** Une seule facture consultation (en attente prioritaire). */
  get factureEnAttente(): boolean {
    const f = this.factureSelected;
    if (!f) return false;
    return (
      Number(f.restant_a_payer) > 0 &&
      ['en_attente', 'partielle', 'brouillon'].includes(f.statut)
    );
  }

  private chargerFactures(patientId: string, keepFactureId?: string): void {
    this.caisse.getFactureConsultationActive(patientId).subscribe({
      next: (inv) => {
        this.factures = [inv];
        const id = keepFactureId && inv.id === keepFactureId ? keepFactureId : inv.id;
        this.selectionnerFacture(id);
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 404) {
          this.factures = [];
          this.factureSelected = null;
          this.paiementsFacture = [];
          return;
        }
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

  labelMode(mode: string): string {
    return this.modePaiementLabels[mode] ?? mode;
  }

  selectionnerFacture(factureId: string): void {
    const inv = this.factures.find((x) => x.id === factureId) ?? null;
    this.factureSelected = inv;
    if (inv?.paiements?.length) {
      this.paiementsFacture = inv.paiements;
    }
    if (inv && this.patientSelected) {
      this.patientSelected = {
        ...this.patientSelected,
        medecin_nom: inv.medecin_nom ?? this.patientSelected.medecin_nom,
        batiment: inv.batiment ?? this.patientSelected.batiment,
        type_consultation_label:
          inv.type_consultation_label ??
          this.patientSelected.type_consultation_label,
      };
    }
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
      if (!inv.paiements?.length) {
        this.chargerPaiements(inv.id);
      }
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
      const tel = this.telephonePourMobile();
      if (!tel) {
        this.paying = false;
        this.errorMsg =
          'Saisissez le numéro Mobile Money du client (ex. 670000001 ou +237 6XX XX XX XX).';
        return;
      }
      const ref = String(
        this.paymentForm.get('reference_transaction')?.value ?? ''
      ).trim();
      const label = mode === 'orange_money' ? 'Orange Money' : 'MTN MoMo';
      this.caisse
        .initierPaiementMobile(
          this.factureSelected.id,
          mode,
          montant,
          ref || null,
          tel
        )
        .subscribe({
          next: (init) => {
            this.paying = false;
            this.mobileInit = init;
            this.mobileStatus = null;
            this.successMsg = `Paiement ${label} initié. Notification envoyée ; QR affiché en secours si besoin.`;
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
      const factureId = this.factureSelected.id;
      const telMixte = this.telephonePourMobile();
      if (mobile > 0 && !telMixte) {
        this.paying = false;
        this.errorMsg = 'Numéro Mobile Money requis pour la partie mobile.';
        return;
      }
      const lancerMobileQr = () => {
        this.caisse
          .initierPaiementMobile(
            factureId,
            mobileMode,
            mobile,
            mobileRef || null,
            telMixte
          )
          .subscribe({
            next: (init) => {
              this.paying = false;
              this.mobileInit = init;
              this.mobileStatus = null;
              this.successMsg =
                'Partie espèces enregistrée. Notification Mobile Money envoyée ; QR Campay affiché en secours.';
              this.chargerFactures(this.patientSelected!.id);
              this.chargerPaiements(factureId);
            },
            error: (err: HttpErrorResponse) => this.onPaymentError(err),
          });
      };
      if (cash > 0) {
        this.caisse.encaisser(factureId, cash, 'especes', null).subscribe({
          next: () => {
            if (mobile > 0) {
              lancerMobileQr();
              return;
            }
            this.afterPaymentSuccess(
              'Paiement en espèces enregistré. Vous pouvez imprimer la facture.'
            );
          },
          error: (err: HttpErrorResponse) => this.onPaymentError(err),
        });
        return;
      }
      if (mobile > 0) {
        lancerMobileQr();
        return;
      }
      this.paying = false;
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
      next: () => {
        this.afterPaymentSuccess(
          'Paiement enregistré. Imprimez ou téléchargez la facture.'
        );
        this.ouvrirApercuFactureApresPaiement();
      },
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
        this.successMsg =
          'Paiement confirmé. Ouvrez la facture pour l’imprimer ou la remettre au patient.';
        this.ouvrirApercuFactureApresPaiement();
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

  ouvrirApercuFacture(): void {
    if (!this.factureSelected) {
      return;
    }
    this.showFactureModal = true;
    this.loadQrPatientImage();
  }

  fermerApercuFacture(): void {
    this.showFactureModal = false;
  }

  private loadQrPatientImage(): void {
    const code =
      this.factureSelected?.code_patient ?? this.patientSelected?.code_patient;
    if (!code) {
      return;
    }
    if (this.qrPatientObjectUrl) {
      URL.revokeObjectURL(this.qrPatientObjectUrl);
      this.qrPatientObjectUrl = null;
    }
    this.caisse.chargerQrPatient(code).subscribe({
      next: (blob) => {
        this.qrPatientObjectUrl = URL.createObjectURL(blob);
      },
      error: () => {
        this.qrPatientObjectUrl = null;
      },
    });
  }

  imprimerApercuFacture(): void {
    if (this.factureSelected) {
      this.imprimerFacture(this.factureSelected.id);
      return;
    }
    window.print();
  }

  ouvrirPdfFacture(factureId?: string): void {
    this.telechargerFacture(factureId, true);
  }

  imprimerFacture(factureId?: string): void {
    const id = factureId ?? this.factureSelected?.id;
    if (!id) {
      return;
    }
    this.caisse.telechargerFacturePdf(id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const w = window.open(url, '_blank');
        if (w) {
          w.addEventListener('load', () => {
            w.print();
          });
        }
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  telechargerFacture(factureId?: string, openInTab = false): void {
    const id = factureId ?? this.factureSelected?.id;
    const numero =
      this.factures.find((f) => f.id === id)?.numero_facture ??
      this.factureSelected?.numero_facture ??
      'facture';
    if (!id) {
      return;
    }
    this.caisse.telechargerFacturePdf(id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        if (openInTab) {
          window.open(url, '_blank');
          return;
        }
        const a = document.createElement('a');
        a.href = url;
        a.download = `${numero}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  private afterPaymentSuccess(message: string): void {
    this.paying = false;
    this.successMsg = message;
    const factureId = this.factureSelected?.id;
    if (this.patientSelected) {
      this.chargerFactures(this.patientSelected.id, factureId);
    } else if (factureId) {
      this.chargerPaiements(factureId);
    }
  }

  private ouvrirApercuFactureApresPaiement(): void {
    setTimeout(() => {
      if (this.facturePayee && this.factureSelected) {
        this.ouvrirApercuFacture();
      }
    }, 400);
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
