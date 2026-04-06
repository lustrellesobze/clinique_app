import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LaboratoryService, PrescriptionPending, LaboratoryInvoiceCreate } from '../../core/services/laboratory.service';
import { AuthService } from '../../core/auth/auth.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-laboratoire',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './laboratoire.component.html',
  styleUrls: ['./laboratoire.component.scss']
})
export class LaboratoireComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  
  prescriptions: PrescriptionPending[] = [];
  selectedPrescription: PrescriptionPending | null = null;
  loading = false;
  error: string | null = null;
  
  // Formulaire de facturation
  modePaiement = 'especes';
  remiseFidelite = 0;
  partAssurance = 0;
  
  private refreshSubscription?: Subscription;

  constructor(private laboratoryService: LaboratoryService) {}

  ngOnInit(): void {
    this.loadPrescriptions();
    
    // Rafraîchissement automatique toutes les 30 secondes
    this.refreshSubscription = interval(30000)
      .pipe(switchMap(() => this.laboratoryService.getPendingPrescriptions()))
      .subscribe({
        next: (data) => {
          this.prescriptions = data;
        },
        error: (err) => {
          console.error('Erreur lors du rafraîchissement:', err);
        }
      });
  }

  ngOnDestroy(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  loadPrescriptions(): void {
    this.loading = true;
    this.error = null;
    
    this.laboratoryService.getPendingPrescriptions().subscribe({
      next: (data) => {
        this.prescriptions = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Erreur lors du chargement des prescriptions';
        this.loading = false;
        console.error(err);
      }
    });
  }

  selectPrescription(prescription: PrescriptionPending): void {
    this.selectedPrescription = prescription;
    this.remiseFidelite = 0;
    this.partAssurance = 0;
  }

  get partPatient(): number {
    if (!this.selectedPrescription) return 0;
    return this.selectedPrescription.montant_total - this.remiseFidelite - this.partAssurance;
  }

  createInvoice(): void {
    if (!this.selectedPrescription) return;
    
    const invoiceData: LaboratoryInvoiceCreate = {
      prescription_id: this.selectedPrescription.id,
      montant_total: this.selectedPrescription.montant_total,
      remise_fidelite: this.remiseFidelite,
      part_assurance: this.partAssurance,
      part_patient: this.partPatient,
      mode_paiement: this.modePaiement
    };
    
    this.loading = true;
    this.laboratoryService.createInvoice(invoiceData).subscribe({
      next: (response) => {
        alert(`Facture créée avec succès: ${response.numero_facture}`);
        this.selectedPrescription = null;
        this.loadPrescriptions();
      },
      error: (err) => {
        this.error = 'Erreur lors de la création de la facture';
        this.loading = false;
        console.error(err);
      }
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
