import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { InsuranceService, Insurance, InsuranceClaim } from '../../core/services/insurance.service';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-assurances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './assurances.component.html',
  styleUrls: ['./assurances.component.scss']
})
export class AssurancesComponent implements OnInit {
  readonly auth = inject(AuthService);
  
  // Données
  companies: Insurance[] = [];
  claims: InsuranceClaim[] = [];
  filteredClaims: InsuranceClaim[] = [];
  
  // Filtres
  filterCompagnie: string = '';
  filterDateDebut: string = '';
  filterDateFin: string = '';
  filterStatut: string = '';
  
  // Sélection
  selectedClaims: Set<string> = new Set();
  
  // Validation de paiement
  showValidationForm: boolean = false;
  validationForm = {
    reference_paiement: '',
    montant_paye: 0
  };
  
  // États
  loading: boolean = false;
  error: string = '';
  successMessage: string = '';

  constructor(private insuranceService: InsuranceService) {}

  ngOnInit(): void {
    this.loadCompanies();
    this.loadClaims();
  }

  loadCompanies(): void {
    this.insuranceService.getCompanies().subscribe({
      next: (data) => {
        this.companies = data;
      },
      error: (err) => {
        this.error = 'Erreur lors du chargement des compagnies';
        console.error(err);
      }
    });
  }

  loadClaims(): void {
    this.loading = true;
    this.error = '';
    
    this.insuranceService.getPendingClaims(
      this.filterCompagnie || undefined,
      this.filterDateDebut || undefined,
      this.filterDateFin || undefined
    ).subscribe({
      next: (data) => {
        this.claims = data;
        this.applyFilters();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Erreur lors du chargement des créances';
        this.loading = false;
        console.error(err);
      }
    });
  }

  applyFilters(): void {
    this.filteredClaims = this.claims.filter(claim => {
      // Filtre par statut
      if (this.filterStatut && claim.statut !== this.filterStatut) {
        return false;
      }
      return true;
    });
  }

  onFilterChange(): void {
    this.loadClaims();
  }

  onStatutFilterChange(): void {
    this.applyFilters();
  }

  toggleClaimSelection(claimId: string): void {
    if (this.selectedClaims.has(claimId)) {
      this.selectedClaims.delete(claimId);
    } else {
      this.selectedClaims.add(claimId);
    }
  }

  selectAll(): void {
    if (this.selectedClaims.size === this.filteredClaims.length) {
      this.selectedClaims.clear();
    } else {
      this.filteredClaims.forEach(claim => this.selectedClaims.add(claim.facture_id));
    }
  }

  get totalSelected(): number {
    return Array.from(this.selectedClaims)
      .map(id => this.filteredClaims.find(c => c.facture_id === id))
      .filter(c => c !== undefined)
      .reduce((sum, claim) => sum + (claim?.part_assurance || 0), 0);
  }

  showValidation(): void {
    if (this.selectedClaims.size === 0) {
      this.error = 'Veuillez sélectionner au moins une créance';
      return;
    }
    
    this.validationForm.montant_paye = this.totalSelected;
    this.showValidationForm = true;
    this.error = '';
  }

  cancelValidation(): void {
    this.showValidationForm = false;
    this.validationForm = {
      reference_paiement: '',
      montant_paye: 0
    };
  }

  validatePayment(): void {
    if (!this.validationForm.reference_paiement) {
      this.error = 'Veuillez saisir une référence de paiement';
      return;
    }

    this.loading = true;
    this.error = '';

    this.insuranceService.validatePayment({
      facture_ids: Array.from(this.selectedClaims),
      reference_paiement: this.validationForm.reference_paiement,
      montant_paye: this.validationForm.montant_paye
    }).subscribe({
      next: (response) => {
        this.successMessage = response.message || 'Paiement validé avec succès';
        this.selectedClaims.clear();
        this.showValidationForm = false;
        this.validationForm = {
          reference_paiement: '',
          montant_paye: 0
        };
        this.loadClaims();
        this.loading = false;
        
        // Effacer le message après 5 secondes
        setTimeout(() => {
          this.successMessage = '';
        }, 5000);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erreur lors de la validation du paiement';
        this.loading = false;
        console.error(err);
      }
    });
  }

  exportToPDF(): void {
    // TODO: Implémenter l'export PDF
    alert('Fonctionnalité d\'export PDF à venir');
  }

  exportToExcel(): void {
    // TODO: Implémenter l'export Excel
    alert('Fonctionnalité d\'export Excel à venir');
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
