import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/auth/auth.service';
import { ROLE_LABELS } from '../../core/models/auth.model';
import {
  FacturationService,
  FactureAdmin,
  FacturesAdminList,
  RapportPeriode,
} from '../../core/services/facturation.service';
import { ADMIN_NAV_ITEMS } from '../admin/admin-nav';

@Component({
  selector: 'app-facturation',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  templateUrl: './facturation.component.html',
  styleUrls: ['./facturation.component.scss'],
})
export class FacturationComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly facturation = inject(FacturationService);

  readonly navItems = ADMIN_NAV_ITEMS;

  loading = false;
  errorMsg = '';
  data: FacturesAdminList | null = null;

  filterDateDebut = '';
  filterDateFin = '';
  filterStatut = 'tous';
  filterService = 'tous';
  filterRecherche = '';

  rapportPeriode: RapportPeriode = 'mensuel';
  rapportDateRef = '';

  ngOnInit(): void {
    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
    this.filterDateFin = this.toIsoDate(today);
    this.filterDateDebut = this.toIsoDate(monthStart);
    this.rapportDateRef = this.filterDateFin;
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

  load(): void {
    this.loading = true;
    this.errorMsg = '';
    this.facturation
      .listFactures({
        date_debut: this.filterDateDebut || undefined,
        date_fin: this.filterDateFin || undefined,
        statut: this.filterStatut,
        service: this.filterService,
        recherche: this.filterRecherche,
      })
      .subscribe({
        next: (d) => {
          this.data = d;
          this.loading = false;
        },
        error: (err: HttpErrorResponse) => {
          this.loading = false;
          this.errorMsg = this.errorFromHttp(err);
        },
      });
  }

  exportPdf(): void {
    this.downloadReport('pdf');
  }

  exportExcel(): void {
    this.downloadReport('excel');
  }

  private downloadReport(kind: 'pdf' | 'excel'): void {
    const dateRef = this.rapportDateRef || this.filterDateFin;
    const req =
      kind === 'pdf'
        ? this.facturation.downloadReportPdf(this.rapportPeriode, dateRef)
        : this.facturation.downloadReportExcel(this.rapportPeriode, dateRef);
    req.subscribe({
      next: (blob) => {
        const ext = kind === 'pdf' ? 'pdf' : 'csv';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rapport_${this.rapportPeriode}_${dateRef}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  statutClass(f: FactureAdmin): string {
    return `statut-${f.statut}`;
  }

  formatDate(d: string): string {
    if (!d) return '';
    const [y, m, day] = d.split('-');
    return `${day}/${m}`;
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }

  private toIsoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  private errorFromHttp(err: HttpErrorResponse): string {
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    return `Erreur ${err.status || 500}. Réessayez.`;
  }
}
