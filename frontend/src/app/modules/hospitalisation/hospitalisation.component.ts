import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { 
  HospitalizationService, 
  Room, 
  HospitalizationCreate,
  HospitalizationResponse,
  HospitalizationDischarge
} from '../../core/services/hospitalization.service';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-hospitalisation',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './hospitalisation.component.html',
  styleUrls: ['./hospitalisation.component.scss']
})
export class HospitalisationComponent implements OnInit {
  readonly auth = inject(AuthService);
  
  // Vues
  currentView: 'list' | 'admission' | 'discharge' = 'list';
  
  // Données
  rooms: Room[] = [];
  activeHospitalizations: HospitalizationResponse[] = [];
  selectedHospitalization: HospitalizationResponse | null = null;
  
  // Filtres
  filterTypeChambre: string = '';
  
  // Formulaire d'admission
  admissionForm = {
    patient_id: '',
    patient_search: '',
    room_id: '',
    medecin_id: '',
    motif_hospitalisation: '',
    acompte_verse_fcfa: 0,
    date_admission: new Date().toISOString().slice(0, 16)
  };
  
  // Formulaire de clôture
  dischargeForm = {
    date_sortie: new Date().toISOString().slice(0, 16),
    mode_paiement: 'especes',
    reference_paiement: ''
  };
  
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;

  constructor(private hospitalizationService: HospitalizationService) {}

  ngOnInit(): void {
    this.loadRooms();
    this.loadActiveHospitalizations();
  }

  loadRooms(): void {
    this.loading = true;
    this.hospitalizationService.getAvailableRooms(this.filterTypeChambre || undefined).subscribe({
      next: (data) => {
        this.rooms = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Erreur lors du chargement des chambres';
        this.loading = false;
        console.error(err);
      }
    });
  }

  loadActiveHospitalizations(): void {
    this.hospitalizationService.getActiveHospitalizations().subscribe({
      next: (data) => {
        this.activeHospitalizations = data;
      },
      error: (err) => {
        console.error('Erreur lors du chargement des hospitalisations:', err);
      }
    });
  }

  filterRooms(): void {
    this.loadRooms();
  }

  get availableRooms(): Room[] {
    return this.rooms.filter(r => r.est_disponible);
  }

  get occupiedRooms(): Room[] {
    return this.rooms.filter(r => !r.est_disponible);
  }

  selectRoom(room: Room): void {
    this.admissionForm.room_id = room.id;
    // Calculer l'acompte minimum (50%)
    this.admissionForm.acompte_verse_fcfa = Math.ceil(room.tarif_journalier_fcfa * 0.5);
  }

  get selectedRoom(): Room | undefined {
    return this.rooms.find(r => r.id === this.admissionForm.room_id);
  }

  showAdmissionForm(): void {
    this.currentView = 'admission';
    this.error = null;
    this.successMessage = null;
  }

  showList(): void {
    this.currentView = 'list';
    this.resetAdmissionForm();
    this.loadRooms();
    this.loadActiveHospitalizations();
  }

  resetAdmissionForm(): void {
    this.admissionForm = {
      patient_id: '',
      patient_search: '',
      room_id: '',
      medecin_id: '',
      motif_hospitalisation: '',
      acompte_verse_fcfa: 0,
      date_admission: new Date().toISOString().slice(0, 16)
    };
  }

  admitPatient(): void {
    if (!this.admissionForm.patient_id || !this.admissionForm.room_id) {
      this.error = 'Veuillez remplir tous les champs obligatoires';
      return;
    }

    const admissionData: HospitalizationCreate = {
      patient_id: this.admissionForm.patient_id,
      room_id: this.admissionForm.room_id,
      medecin_id: this.admissionForm.medecin_id || undefined,
      motif_hospitalisation: this.admissionForm.motif_hospitalisation || undefined,
      acompte_verse_fcfa: this.admissionForm.acompte_verse_fcfa,
      date_admission: this.admissionForm.date_admission
    };

    this.loading = true;
    this.error = null;

    this.hospitalizationService.admitPatient(admissionData).subscribe({
      next: (response) => {
        this.successMessage = `Patient ${response.patient_name} admis avec succès en chambre ${response.room_numero}`;
        this.loading = false;
        setTimeout(() => this.showList(), 2000);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erreur lors de l\'admission du patient';
        this.loading = false;
        console.error(err);
      }
    });
  }

  selectForDischarge(hospitalization: HospitalizationResponse): void {
    this.selectedHospitalization = hospitalization;
    this.currentView = 'discharge';
    this.dischargeForm.date_sortie = new Date().toISOString().slice(0, 16);
  }

  get estimatedTotal(): number {
    if (!this.selectedHospitalization) return 0;
    const dateAdmission = new Date(this.selectedHospitalization.date_admission);
    const dateSortie = new Date(this.dischargeForm.date_sortie);
    const jours = Math.ceil((dateSortie.getTime() - dateAdmission.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    return jours * this.selectedHospitalization.tarif_journalier;
  }

  get resteAPayer(): number {
    if (!this.selectedHospitalization) return 0;
    return Math.max(0, this.estimatedTotal - this.selectedHospitalization.acompte_verse_fcfa);
  }

  dischargePatient(): void {
    if (!this.selectedHospitalization) return;

    const dischargeData: HospitalizationDischarge = {
      hospitalization_id: this.selectedHospitalization.id,
      date_sortie: this.dischargeForm.date_sortie,
      mode_paiement: this.dischargeForm.mode_paiement,
      reference_paiement: this.dischargeForm.reference_paiement || undefined
    };

    this.loading = true;
    this.error = null;

    this.hospitalizationService.dischargePatient(dischargeData).subscribe({
      next: (response) => {
        this.successMessage = `Séjour clôturé avec succès. Facture: ${response.numero_facture}. Reste à payer: ${response.reste_a_payer} FCFA`;
        this.loading = false;
        setTimeout(() => this.showList(), 3000);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erreur lors de la clôture du séjour';
        this.loading = false;
        console.error(err);
      }
    });
  }

  // Fonction helper pour chercher un patient (à implémenter avec un vrai service)
  searchPatient(): void {
    // TODO: Implémenter la recherche de patient
    // Pour l'instant, utiliser l'ID du patient de test
    if (this.admissionForm.patient_search) {
      // Simuler une recherche - en production, appeler un service
      this.admissionForm.patient_id = this.admissionForm.patient_search;
    }
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
