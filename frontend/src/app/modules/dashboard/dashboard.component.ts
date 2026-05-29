import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { Chart } from 'chart.js/auto';
import { AuthService } from '../../core/auth/auth.service';
import {
  DashboardService,
  FinanceDashboardOut,
  FinanceSummaryOut,
} from '../../core/services/dashboard.service';
import { ROLE_LABELS } from '../../core/models/auth.model';
import { ADMIN_NAV_ITEMS } from '../admin/admin-nav';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly dashboard = inject(DashboardService);

  loading = false;
  errorMsg = '';
  summary: FinanceSummaryOut | null = null;
  data: FinanceDashboardOut | null = null;

  dateDebut = '';
  dateFin = '';

  readonly navItems = ADMIN_NAV_ITEMS;

  private chartService: Chart | null = null;
  private chartDaily: Chart | null = null;

  get userLabel(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return 'Utilisateur';
    return `${u.prenom} ${u.nom}`.trim();
  }

  get userInitials(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return '?';
    return `${(u.prenom || '?')[0]}${(u.nom || '?')[0]}`.toUpperCase();
  }

  get roleLabel(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return '';
    return ROLE_LABELS[u.role] ?? u.role;
  }

  get dateAujourdHuiLabel(): string {
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date());
  }

  get objectifPct(): number {
    if (!this.summary || !this.summary.objectif_ca_fcfa) return 0;
    const pct =
      (Number(this.summary.chiffre_affaires) / Number(this.summary.objectif_ca_fcfa)) *
      100;
    return Math.min(100, Math.round(pct));
  }

  ngOnInit(): void {
    this.reload();
  }

  ngOnDestroy(): void {
    this.chartService?.destroy();
    this.chartDaily?.destroy();
  }

  reload(): void {
    this.loading = true;
    this.errorMsg = '';
    this.dashboard.getSummary().subscribe({
      next: (s) => {
        this.summary = s;
        this.loadFinance();
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  private loadFinance(): void {
    this.dashboard.getFinance(this.dateDebut || undefined, this.dateFin || undefined).subscribe({
      next: (d) => {
        this.loading = false;
        this.data = d;
        queueMicrotask(() => this.renderCharts());
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  ouvrirPdf(): void {
    this.dashboard
      .downloadFinancePdf(this.dateDebut || undefined, this.dateFin || undefined)
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'rapport_financier.pdf';
          a.click();
          URL.revokeObjectURL(url);
        },
        error: (err: HttpErrorResponse) => {
          this.errorMsg = this.errorFromHttp(err);
        },
      });
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }

  private renderCharts(): void {
    if (!this.data) return;

    const el1 = document.getElementById('chartService') as HTMLCanvasElement | null;
    if (el1) {
      this.chartService?.destroy();
      this.chartService = new Chart(el1, {
        type: 'bar',
        data: {
          labels: this.data.par_service.map((x) => x.service),
          datasets: [
            {
              label: 'Facturé',
              data: this.data.par_service.map((x) => Number(x.montant_total || 0)),
              backgroundColor: '#3b82f6',
            },
            {
              label: 'Encaissé',
              data: this.data.par_service.map((x) => Number(x.montant_regle || 0)),
              backgroundColor: '#22c55e',
            },
          ],
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
      });
    }

    const el2 = document.getElementById('chartDaily') as HTMLCanvasElement | null;
    if (el2) {
      this.chartDaily?.destroy();
      this.chartDaily = new Chart(el2, {
        type: 'line',
        data: {
          labels: this.data.par_jour.map((x) => x.jour),
          datasets: [
            {
              label: 'Encaissé / jour',
              data: this.data.par_jour.map((x) => Number(x.montant_regle || 0)),
              borderColor: '#2563eb',
              tension: 0.3,
            },
          ],
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
      });
    }
  }

  private errorFromHttp(err: HttpErrorResponse): string {
    const d = err.error?.detail;
    if (typeof d === 'string') return d;
    return `Erreur ${err.status || 500}. Réessayez.`;
  }
}
