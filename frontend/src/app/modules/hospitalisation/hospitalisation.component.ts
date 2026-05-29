import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive } from '@angular/router';
import {
  HospitalizationService,
  Room,
  HospitalizationCreate,
  HospitalizationAdminRow,
  HospitalizationDashboard,
  HospitalizationDischarge,
} from '../../core/services/hospitalization.service';
import { AuthService } from '../../core/auth/auth.service';
import { ROLE_LABELS } from '../../core/models/auth.model';
import { ADMIN_NAV_ITEMS } from '../admin/admin-nav';

@Component({
  selector: 'app-hospitalisation',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  templateUrl: './hospitalisation.component.html',
  styleUrls: ['./hospitalisation.component.scss'],
})
export class HospitalisationComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly hospitalizationService = inject(HospitalizationService);

  readonly navItems = ADMIN_NAV_ITEMS;

  currentView: 'list' | 'admission' | 'discharge' | 'detail' = 'list';

  dashboard: HospitalizationDashboard | null = null;
  rooms: Room[] = [];
  selectedHospitalization: HospitalizationAdminRow | null = null;
  detailPatient: HospitalizationAdminRow | null = null;

  filterTypeChambre = '';

  admissionForm = {
    patient_id: '',
    patient_search: '',
    patient_label: '',
    room_id: '',
    medecin_id: '',
    motif_hospitalisation: '',
    acompte_verse_fcfa: 0,
    date_admission: new Date().toISOString().slice(0, 16),
  };

  dischargeForm = {
    date_sortie: new Date().toISOString().slice(0, 16),
    mode_paiement: 'especes',
    reference_paiement: '',
  };

  loading = false;
  error: string | null = null;
  successMessage: string | null = null;

  get isAdmin(): boolean {
    return this.auth.getCurrentUser()?.role === 'admin';
  }

  get userLabel(): string {
    const u = this.auth.getCurrentUser();
    return u ? `${u.prenom} ${u.nom}` : '';
  }

  get userInitials(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return '?';
    return `${(u.prenom || '?')[0]}${(u.nom || '?')[0]}`.toUpperCase();
  }

  get roleLabel(): string {
    const u = this.auth.getCurrentUser();
    return u ? ROLE_LABELS[u.role] ?? u.role : '';
  }

  get hospitalizedPatients(): HospitalizationAdminRow[] {
    return this.dashboard?.patients ?? [];
  }

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loadDashboard();
    this.loadRooms();
  }

  loadDashboard(): void {
    this.loading = true;
    this.hospitalizationService.getDashboard().subscribe({
      next: (data) => {
        this.dashboard = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Erreur lors du chargement du tableau de bord';
        this.loading = false;
        console.error(err);
      },
    });
  }

  loadRooms(): void {
    this.hospitalizationService.getAvailableRooms(this.filterTypeChambre || undefined).subscribe({
      next: (data) => {
        this.rooms = data;
      },
      error: (err) => console.error(err),
    });
  }

  filterRooms(): void {
    this.loadRooms();
  }

  get availableRooms(): Room[] {
    return this.rooms.filter((r) => r.est_disponible);
  }

  get occupiedRooms(): Room[] {
    return this.rooms.filter((r) => !r.est_disponible);
  }

  selectRoom(room: Room): void {
    this.admissionForm.room_id = room.id;
    this.admissionForm.acompte_verse_fcfa = Math.ceil(room.tarif_journalier_fcfa * 0.5);
  }

  get selectedRoom(): Room | undefined {
    return this.rooms.find((r) => r.id === this.admissionForm.room_id);
  }

  showAdmissionForm(): void {
    this.currentView = 'admission';
    this.error = null;
    this.successMessage = null;
  }

  showList(): void {
    this.currentView = 'list';
    this.detailPatient = null;
    this.selectedHospitalization = null;
    this.resetAdmissionForm();
    this.refresh();
  }

  resetAdmissionForm(): void {
    this.admissionForm = {
      patient_id: '',
      patient_search: '',
      patient_label: '',
      room_id: '',
      medecin_id: '',
      motif_hospitalisation: '',
      acompte_verse_fcfa: 0,
      date_admission: new Date().toISOString().slice(0, 16),
    };
  }

  searchPatient(): void {
    const q = this.admissionForm.patient_search.trim();
    if (!q) {
      this.error = 'Saisissez un code ou un nom de patient';
      return;
    }
    this.error = null;
    this.hospitalizationService.lookupPatient(q).subscribe({
      next: (p) => {
        this.admissionForm.patient_id = p.id;
        this.admissionForm.patient_label = `${p.nom} ${p.prenom} (${p.code_patient})`;
        this.admissionForm.patient_search = p.code_patient;
      },
      error: () => {
        this.error = `Aucun patient trouvé pour « ${q} »`;
        this.admissionForm.patient_id = '';
        this.admissionForm.patient_label = '';
      },
    });
  }

  admitPatient(): void {
    if (!this.admissionForm.patient_id || !this.admissionForm.room_id) {
      this.error = 'Veuillez sélectionner un patient et une chambre';
      return;
    }

    const admissionData: HospitalizationCreate = {
      patient_id: this.admissionForm.patient_id,
      room_id: this.admissionForm.room_id,
      medecin_id: this.admissionForm.medecin_id || undefined,
      motif_hospitalisation: this.admissionForm.motif_hospitalisation || undefined,
      acompte_verse_fcfa: this.admissionForm.acompte_verse_fcfa,
      date_admission: this.admissionForm.date_admission,
    };

    this.loading = true;
    this.error = null;

    this.hospitalizationService.admitPatient(admissionData).subscribe({
      next: (response) => {
        this.successMessage = `Patient ${response.patient_name} admis en chambre ${response.room_numero}`;
        this.loading = false;
        setTimeout(() => this.showList(), 2000);
      },
      error: (err) => {
        this.error = err.error?.detail || "Erreur lors de l'admission";
        this.loading = false;
      },
    });
  }

  viewPatient(row: HospitalizationAdminRow): void {
    this.detailPatient = row;
    this.currentView = 'detail';
  }

  selectForDischarge(row: HospitalizationAdminRow): void {
    this.selectedHospitalization = row;
    this.currentView = 'discharge';
    this.dischargeForm.date_sortie = new Date().toISOString().slice(0, 16);
    this.error = null;
    this.successMessage = null;
  }

  get estimatedTotal(): number {
    if (!this.selectedHospitalization) return 0;
    const dateAdmission = new Date(this.selectedHospitalization.date_admission);
    const dateSortie = new Date(this.dischargeForm.date_sortie);
    const jours =
      Math.ceil((dateSortie.getTime() - dateAdmission.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    return Math.max(1, jours) * this.selectedHospitalization.tarif_journalier;
  }

  get resteAPayer(): number {
    if (!this.selectedHospitalization) return 0;
    return Math.max(0, this.estimatedTotal - this.selectedHospitalization.acomptes_fcfa);
  }

  dischargePatient(): void {
    if (!this.selectedHospitalization) return;

    const dischargeData: HospitalizationDischarge = {
      hospitalization_id: this.selectedHospitalization.id,
      date_sortie: this.dischargeForm.date_sortie,
      mode_paiement: this.dischargeForm.mode_paiement,
      reference_paiement: this.dischargeForm.reference_paiement || undefined,
    };

    this.loading = true;
    this.error = null;

    this.hospitalizationService.dischargePatient(dischargeData).subscribe({
      next: (response) => {
        this.successMessage = `Sortie enregistrée. Facture ${response.numero_facture}. Reste : ${response.reste_a_payer} FCFA`;
        this.loading = false;
        setTimeout(() => this.showList(), 2500);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erreur lors de la sortie';
        this.loading = false;
      },
    });
  }

  soldeClass(solde: number): string {
    if (solde >= 100000) return 'solde-high';
    if (solde >= 30000) return 'solde-mid';
    return 'solde-low';
  }

  roomTypeLabel(type: string): string {
    const map: Record<string, string> = {
      commune: 'Commune',
      individuelle: 'Individuelle',
      vip: 'VIP',
    };
    return map[type?.toLowerCase()] ?? type;
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
