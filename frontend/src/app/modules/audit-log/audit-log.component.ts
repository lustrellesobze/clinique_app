import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/auth/auth.service';
import { ROLE_LABELS } from '../../core/models/auth.model';
import {
  AuditLogEntry,
  AuditLogList,
  AuditService,
  AuditUserOption,
} from '../../core/services/audit.service';
import { ADMIN_NAV_ITEMS } from '../admin/admin-nav';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  templateUrl: './audit-log.component.html',
  styleUrls: ['./audit-log.component.scss'],
})
export class AuditLogComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly audit = inject(AuditService);

  readonly navItems = ADMIN_NAV_ITEMS;
  readonly categories = [
    { value: 'toutes', label: 'Toutes les actions' },
    { value: 'FACTURE', label: 'Facture' },
    { value: 'PAIEMENT', label: 'Paiement' },
    { value: 'PATIENT', label: 'Patient' },
    { value: 'PRESCRIPTION', label: 'Prescription' },
    { value: 'ANNULATION', label: 'Annulation' },
    { value: 'SYSTÈME', label: 'Système' },
  ];

  users: AuditUserOption[] = [];
  data: AuditLogList | null = null;
  loading = false;
  errorMsg = '';

  filterUser = '';
  filterCategorie = 'toutes';
  filterRecherche = '';
  filterDateDebut = '';
  filterDateFin = '';

  ngOnInit(): void {
    const today = new Date().toISOString().slice(0, 10);
    this.filterDateDebut = today;
    this.filterDateFin = today;
    this.audit.listUsers().subscribe({
      next: (u) => (this.users = u),
      error: () => (this.users = []),
    });
    this.load();
  }

  get userLabel(): string {
    const u = this.auth.getCurrentUser();
    return u ? `${u.prenom} ${u.nom}`.trim() : 'Utilisateur';
  }

  get userInitials(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return '?';
    return `${(u.prenom || '?')[0]}${(u.nom || '?')[0]}`.toUpperCase();
  }

  get roleLabel(): string {
    const u = this.auth.getCurrentUser();
    return u ? (ROLE_LABELS[u.role] ?? u.role) : '';
  }

  get journalDateLabel(): string {
    if (!this.filterDateDebut) return '';
    const d = new Date(this.filterDateDebut + 'T12:00:00');
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(d);
  }

  load(): void {
    this.loading = true;
    this.errorMsg = '';
    this.audit
      .listLogs({
        user_id: this.filterUser || undefined,
        categorie: this.filterCategorie,
        recherche: this.filterRecherche,
        date_debut: this.filterDateDebut,
        date_fin: this.filterDateFin,
        limit: 200,
      })
      .subscribe({
        next: (d) => {
          this.data = d;
          this.loading = false;
        },
        error: (err: HttpErrorResponse) => {
          this.loading = false;
          this.errorMsg = err.error?.detail || `Erreur ${err.status}`;
        },
      });
  }

  formatTime(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  catClass(entry: AuditLogEntry): string {
    const m: Record<string, string> = {
      FACTURE: 'cat-facture',
      PAIEMENT: 'cat-paiement',
      PATIENT: 'cat-patient',
      PRESCRIPTION: 'cat-prescription',
      ANNULATION: 'cat-annulation',
      'SYSTÈME': 'cat-systeme',
    };
    return m[entry.categorie] || 'cat-systeme';
  }

  statutClass(entry: AuditLogEntry): string {
    return `pill-${this.catClass(entry).replace('cat-', '')}`;
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
