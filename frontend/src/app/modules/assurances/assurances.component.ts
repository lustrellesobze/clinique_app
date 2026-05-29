import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  InsuranceService,
  Insurance,
  InsuranceClaim,
  InsuranceCompanyDetail,
  InsuranceCompanyPayload,
  DEFAULT_TAUX,
  TauxParCategorie,
} from '../../core/services/insurance.service';
import { AuthService } from '../../core/auth/auth.service';

type Onglet = 'compagnies' | 'creances';

@Component({
  selector: 'app-assurances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './assurances.component.html',
  styleUrls: ['./assurances.component.scss'],
})
export class AssurancesComponent implements OnInit {
  readonly auth = inject(AuthService);

  onglet: Onglet = 'compagnies';
  readonly isAdmin = () => this.auth.hasRole('admin');

  catalog: InsuranceCompanyDetail[] = [];
  companies: Insurance[] = [];
  claims: InsuranceClaim[] = [];
  filteredClaims: InsuranceClaim[] = [];

  filterCompagnie = '';
  filterDateDebut = '';
  filterDateFin = '';
  filterStatut = '';
  selectedClaims = new Set<string>();
  showValidationForm = false;
  validationForm = { reference_paiement: '', montant_paye: 0 };

  loading = false;
  error = '';
  successMessage = '';

  showCompanyForm = false;
  editingCompanyId: string | null = null;
  companyForm: InsuranceCompanyPayload = this.emptyCompanyForm();
  exclusionsText = '';

  constructor(private insuranceService: InsuranceService) {}

  ngOnInit(): void {
    this.loadCatalog();
    this.loadCompanies();
    this.loadClaims();
  }

  emptyCompanyForm(): InsuranceCompanyPayload {
    return {
      nom_compagnie: '',
      taux_par_categorie: { ...DEFAULT_TAUX },
      plafond_annuel_fcfa: null,
      franchise_fcfa: null,
      franchise_libelle: 'Aucune',
      exclusions_list: [],
      est_active: true,
    };
  }

  setOnglet(tab: Onglet): void {
    this.onglet = tab;
  }

  loadCatalog(): void {
    this.insuranceService.getCompaniesManage().subscribe({
      next: (data) => {
        this.catalog = data;
      },
      error: (err) => {
        console.error(err);
        this.error = 'Erreur lors du chargement des compagnies';
      },
    });
  }

  loadCompanies(): void {
    this.insuranceService.getCompanies().subscribe({
      next: (data) => {
        this.companies = data;
      },
      error: (err) => console.error(err),
    });
  }

  loadClaims(): void {
    this.loading = true;
    this.error = '';
    this.insuranceService
      .getPendingClaims(
        this.filterCompagnie || undefined,
        this.filterDateDebut || undefined,
        this.filterDateFin || undefined
      )
      .subscribe({
        next: (data) => {
          this.claims = data;
          this.applyFilters();
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Erreur lors du chargement des créances';
          this.loading = false;
          console.error(err);
        },
      });
  }

  applyFilters(): void {
    this.filteredClaims = this.claims.filter((claim) => {
      if (this.filterStatut && claim.statut_creance !== this.filterStatut) return false;
      return true;
    });
  }

  onFilterChange(): void {
    this.loadClaims();
  }

  onStatutFilterChange(): void {
    this.applyFilters();
  }

  openNewCompany(): void {
    this.editingCompanyId = null;
    this.companyForm = this.emptyCompanyForm();
    this.exclusionsText = '';
    this.showCompanyForm = true;
    this.error = '';
  }

  openEditCompany(c: InsuranceCompanyDetail): void {
    this.editingCompanyId = c.id;
    this.companyForm = {
      nom_compagnie: c.nom_compagnie,
      taux_par_categorie: { ...c.taux_par_categorie },
      plafond_annuel_fcfa: c.plafond_annuel_fcfa,
      franchise_fcfa: c.franchise_fcfa,
      franchise_libelle: c.franchise_libelle,
      exclusions_list: [...(c.exclusions_list || [])],
      est_active: c.est_active,
    };
    this.exclusionsText = (c.exclusions_list || []).join(', ');
    this.showCompanyForm = true;
    this.error = '';
  }

  cancelCompanyForm(): void {
    this.showCompanyForm = false;
    this.editingCompanyId = null;
  }

  saveCompany(): void {
    if (!this.companyForm.nom_compagnie.trim()) {
      this.error = 'Le nom de la compagnie est obligatoire';
      return;
    }
    this.companyForm.exclusions_list = this.exclusionsText
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    this.loading = true;
    this.error = '';

    const done = () => {
      this.loading = false;
      this.showCompanyForm = false;
      this.successMessage = 'Compagnie enregistrée';
      this.loadCatalog();
      this.loadCompanies();
      setTimeout(() => (this.successMessage = ''), 4000);
    };

    if (this.editingCompanyId) {
      this.insuranceService.updateCompany(this.editingCompanyId, this.companyForm).subscribe({
        next: () => done(),
        error: (err) => {
          this.loading = false;
          this.error = err.error?.detail || 'Erreur lors de la mise à jour';
        },
      });
    } else {
      this.insuranceService.createCompany(this.companyForm).subscribe({
        next: () => done(),
        error: (err) => {
          this.loading = false;
          this.error = err.error?.detail || 'Erreur lors de la création';
        },
      });
    }
  }

  toggleCompany(c: InsuranceCompanyDetail): void {
    const req = c.est_active
      ? this.insuranceService.deactivateCompany(c.id)
      : this.insuranceService.activateCompany(c.id);
    req.subscribe({
      next: () => {
        this.loadCatalog();
        this.loadCompanies();
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erreur lors du changement de statut';
      },
    });
  }

  tauxEntries(taux: TauxParCategorie): { key: string; label: string; value: number }[] {
    return [
      { key: 'consultation', label: 'Consultation', value: taux.consultation },
      { key: 'imagerie', label: 'Imagerie', value: taux.imagerie },
      { key: 'chirurgie', label: 'Chirurgie', value: taux.chirurgie },
      { key: 'esthetique', label: 'Esthétique', value: taux.esthetique },
      { key: 'hospitalisation', label: 'Hospitalisation', value: taux.hospitalisation },
    ];
  }

  tauxClass(value: number): string {
    if (value >= 80) return 'taux-high';
    if (value <= 0) return 'taux-zero';
    return 'taux-mid';
  }

  formatFcfa(n: number | null | undefined): string {
    if (n == null) return '—';
    return `${Number(n).toLocaleString('fr-FR')} FCFA`;
  }

  formatClaimDate(d: string): string {
    if (!d) return '';
    const today = new Date().toISOString().slice(0, 10);
    if (d === today) return "Aujourd'hui";
    const [, m, day] = d.split('-');
    return `${day}/${m}`;
  }

  actionCreance(action: string, claim: InsuranceClaim): void {
    if (action === 'detail') {
      alert(`Facture ${claim.numero_facture}\nPatient: ${claim.patient_prenom} ${claim.patient_nom}\nMontant assurance: ${claim.part_assurance} FCFA`);
      return;
    }
    if (action === 'relancer') {
      this.successMessage = `Relance envoyée pour ${claim.compagnie_assurance}`;
      setTimeout(() => (this.successMessage = ''), 3000);
      return;
    }
    if (action === 'cloturer' || action === 'traiter') {
      this.toggleClaimSelection(claim.facture_id);
      this.showValidation();
    }
  }

  toggleClaimSelection(claimId: string): void {
    if (this.selectedClaims.has(claimId)) this.selectedClaims.delete(claimId);
    else this.selectedClaims.add(claimId);
  }

  selectAll(): void {
    if (this.selectedClaims.size === this.filteredClaims.length) {
      this.selectedClaims.clear();
    } else {
      this.filteredClaims.forEach((c) => this.selectedClaims.add(c.facture_id));
    }
  }

  get totalSelected(): number {
    return Array.from(this.selectedClaims)
      .map((id) => this.filteredClaims.find((c) => c.facture_id === id))
      .filter((c) => c !== undefined)
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
    this.validationForm = { reference_paiement: '', montant_paye: 0 };
  }

  validatePayment(): void {
    if (!this.validationForm.reference_paiement) {
      this.error = 'Veuillez saisir une référence de paiement';
      return;
    }
    this.loading = true;
    this.insuranceService
      .validatePayment({
        facture_ids: Array.from(this.selectedClaims),
        reference_paiement: this.validationForm.reference_paiement,
        montant_paye: this.validationForm.montant_paye,
      })
      .subscribe({
        next: (response) => {
          this.successMessage = response.message || 'Paiement validé avec succès';
          this.selectedClaims.clear();
          this.showValidationForm = false;
          this.validationForm = { reference_paiement: '', montant_paye: 0 };
          this.loadClaims();
          this.loading = false;
          setTimeout(() => (this.successMessage = ''), 5000);
        },
        error: (err) => {
          this.error = err.error?.detail || 'Erreur lors de la validation du paiement';
          this.loading = false;
        },
      });
  }

  exportToPDF(): void {
    alert("Fonctionnalité d'export PDF à venir");
  }

  exportToExcel(): void {
    alert("Fonctionnalité d'export Excel à venir");
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
