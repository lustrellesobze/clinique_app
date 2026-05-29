import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { Chart } from 'chart.js/auto';
import { AuthService } from '../../core/auth/auth.service';
import { ROLE_LABELS } from '../../core/models/auth.model';
import { DashboardService, StatsReportOut } from '../../core/services/dashboard.service';
import {
  FacturationService,
  RapportPeriode,
} from '../../core/services/facturation.service';
import { ADMIN_NAV_ITEMS } from '../admin/admin-nav';

const JOURS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];

@Component({
  selector: 'app-rapports',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  templateUrl: './rapports.component.html',
  styleUrls: ['./rapports.component.scss'],
})
export class RapportsComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly dashboard = inject(DashboardService);
  private readonly facturation = inject(FacturationService);

  readonly navItems = ADMIN_NAV_ITEMS;
  readonly periodes: { value: RapportPeriode; label: string }[] = [
    { value: 'journalier', label: 'Journalier' },
    { value: 'hebdomadaire', label: 'Hebdomadaire' },
    { value: 'mensuel', label: 'Mensuel' },
    { value: 'trimestriel', label: 'Trimestriel' },
  ];

  stats: StatsReportOut | null = null;
  loading = false;
  errorMsg = '';
  rapportPeriode: RapportPeriode = 'mensuel';
  rapportDateRef = '';

  private chartCa: Chart | null = null;

  ngOnInit(): void {
    this.rapportDateRef = new Date().toISOString().slice(0, 10);
    this.load();
  }

  ngOnDestroy(): void {
    this.chartCa?.destroy();
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

  formatCaM(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} M`;
    return `${Math.round(n).toLocaleString('fr-FR')}`;
  }

  load(): void {
    this.loading = true;
    this.errorMsg = '';
    this.dashboard.getStatsReport().subscribe({
      next: (s) => {
        this.stats = s;
        this.loading = false;
        queueMicrotask(() => this.renderChart());
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        this.errorMsg = err.error?.detail || `Erreur ${err.status}`;
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
    const req =
      kind === 'pdf'
        ? this.facturation.downloadReportPdf(this.rapportPeriode, this.rapportDateRef)
        : this.facturation.downloadReportExcel(this.rapportPeriode, this.rapportDateRef);
    req.subscribe({
      next: (blob) => {
        const ext = kind === 'pdf' ? 'pdf' : 'csv';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rapport_${this.rapportPeriode}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = err.error?.detail || 'Erreur export';
      },
    });
  }

  barColor(i: number): string {
    const colors = ['#2563eb', '#16a34a', '#ea580c', '#9333ea', '#dc2626', '#64748b'];
    return colors[i % colors.length];
  }

  private renderChart(): void {
    if (!this.stats?.ca_7_jours?.length) return;
    const el = document.getElementById('chartCa7') as HTMLCanvasElement | null;
    if (!el) return;
    this.chartCa?.destroy();
    const labels = this.stats.ca_7_jours.map((x) => {
      const d = new Date(x.jour + 'T12:00:00');
      const j = JOURS[d.getDay()];
      const isToday = x.jour === new Date().toISOString().slice(0, 10);
      return isToday ? 'Auj.' : j;
    });
    this.chartCa = new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'CA (FCFA)',
            data: this.stats.ca_7_jours.map((x) => Number(x.montant_regle || 0)),
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            fill: true,
            tension: 0.3,
          },
        ],
      },
      options: { responsive: true, plugins: { legend: { display: false } } },
    });
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
