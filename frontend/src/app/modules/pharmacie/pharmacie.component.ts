import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { AuthService } from '../../core/auth/auth.service';
import {
  PharmacyPrescriptionPending,
  PharmacyService,
  PharmacyInvoiceCreate,
} from '../../core/services/pharmacy.service';

@Component({
  selector: 'app-pharmacie',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './pharmacie.component.html',
  styleUrls: ['./pharmacie.component.scss'],
})
export class PharmacieComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);

  prescriptions: PharmacyPrescriptionPending[] = [];
  selectedPrescription: PharmacyPrescriptionPending | null = null;
  loading = false;
  error: string | null = null;

  modePaiement = 'especes';
  remiseFidelite = 0;
  partAssurance = 0;
  subEquivalent = '';
  subMotif = '';
  selectedItemId = '';

  private refreshSubscription?: Subscription;

  constructor(private pharmacyService: PharmacyService) {}

  ngOnInit(): void {
    this.loadPrescriptions();
    this.refreshSubscription = interval(30000)
      .pipe(switchMap(() => this.pharmacyService.getPendingPrescriptions()))
      .subscribe({
        next: (data) => (this.prescriptions = data),
        error: () => {},
      });
  }

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  loadPrescriptions(): void {
    this.loading = true;
    this.error = null;
    this.pharmacyService.getPendingPrescriptions().subscribe({
      next: (data) => {
        this.prescriptions = data;
        this.loading = false;
      },
      error: () => {
        this.error = 'Erreur lors du chargement des ordonnances';
        this.loading = false;
      },
    });
  }

  selectPrescription(p: PharmacyPrescriptionPending): void {
    this.selectedPrescription = p;
    this.remiseFidelite = 0;
    this.partAssurance = 0;
    this.subEquivalent = '';
    this.subMotif = '';
    this.selectedItemId = '';
  }

  get partPatient(): number {
    if (!this.selectedPrescription) return 0;
    return this.selectedPrescription.montant_total - this.remiseFidelite - this.partAssurance;
  }

  substituteSelectedItem(): void {
    if (!this.selectedItemId || !this.subEquivalent.trim()) return;
    this.pharmacyService
      .substituteItem(this.selectedItemId, this.subEquivalent.trim(), this.subMotif.trim())
      .subscribe({
        next: () => {
          this.subEquivalent = '';
          this.subMotif = '';
          this.selectedItemId = '';
          this.loadPrescriptions();
        },
        error: () => {
          this.error = "Erreur lors de l'enregistrement de l'équivalent";
        },
      });
  }

  createInvoice(): void {
    if (!this.selectedPrescription) return;
    const payload: PharmacyInvoiceCreate = {
      prescription_id: this.selectedPrescription.id,
      montant_total: this.selectedPrescription.montant_total,
      remise_fidelite: this.remiseFidelite,
      part_assurance: this.partAssurance,
      part_patient: this.partPatient,
      mode_paiement: this.modePaiement,
    };
    this.loading = true;
    this.pharmacyService.createInvoice(payload).subscribe({
      next: (res) => {
        alert(`Facture créée: ${res.numero_facture}`);
        this.selectedPrescription = null;
        this.loadPrescriptions();
      },
      error: () => {
        this.error = 'Erreur lors de la création de facture';
        this.loading = false;
      },
    });
  }

  cancelSelection(): void {
    this.selectedPrescription = null;
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
