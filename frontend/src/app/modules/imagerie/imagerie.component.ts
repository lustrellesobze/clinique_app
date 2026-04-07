import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ImagingService, ImagingPrescriptionPending, ImagingInvoiceCreate } from '../../core/services/imaging.service';
import { AuthService } from '../../core/auth/auth.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-imagerie',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './imagerie.component.html',
  styleUrls: ['./imagerie.component.scss']
})
export class ImagerieComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  
  prescriptions: ImagingPrescriptionPending[] = [];
  selectedPrescription: ImagingPrescriptionPending | null = null;
  loading = false;
  error: string | null = null;
  
  modePaiement = 'especes';
  remiseFidelite = 0;
  partAssurance = 0;
  
  private refreshSubscription?: Subscription;

  constructor(private imagingService: ImagingService) {}

  ngOnInit(): void {
    this.loadPrescriptions();
    
    this.refreshSubscription = interval(30000)
      .pipe(switchMap(() => this.imagingService.getPendingPrescriptions()))
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
    
    this.imagingService.getPendingPrescriptions().subscribe({
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

  selectPrescription(prescription: ImagingPrescriptionPending): void {
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
    
    const invoiceData: ImagingInvoiceCreate = {
      prescription_id: this.selectedPrescription.id,
      montant_total: this.selectedPrescription.montant_total,
      remise_fidelite: this.remiseFidelite,
      part_assurance: this.partAssurance,
      part_patient: this.partPatient,
      mode_paiement: this.modePaiement
    };
    
    this.loading = true;
    this.imagingService.createInvoice(invoiceData).subscribe({
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
