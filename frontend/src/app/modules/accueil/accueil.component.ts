import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import {
  AccueilService,
  InscriptionPayload,
  InscriptionResponse,
  MedecinOption,
} from '../../core/services/accueil.service';

@Component({
  selector: 'app-accueil',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './accueil.component.html',
  styleUrls: ['./accueil.component.scss'],
})
export class AccueilComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly accueil = inject(AccueilService);

  medecins: MedecinOption[] = [];
  success: InscriptionResponse | null = null;
  errorMsg = '';
  submitting = false;

  readonly assureurs = [
    'CNPS',
    'Activa',
    'Allianz',
    'Sanlam',
    'Autre / mutuelle',
  ];

  form = this.fb.group({
    nom: ['', Validators.required],
    prenom: ['', Validators.required],
    date_naissance: ['', Validators.required],
    sexe: ['M' as 'M' | 'F' | 'autre', Validators.required],
    telephone: ['', Validators.required],
    email: [''],
    contact_urgence: [''],
    derniere_date_regles: [''],
    poids_kg: [null as number | null],
    taille_cm: [null as number | null],
    temperature_c: [null as number | null],
    tension: [''],
    motif_consultation: [''],
    type_consultation: [
      'generale' as InscriptionPayload['type_consultation'],
      Validators.required,
    ],
    medecin_id: ['', Validators.required],
    est_assure: ['non' as 'oui' | 'non'],
    compagnie_assurance: [''],
    date_validite_assurance: [''],
    numero_assure: [''],
    montant_consultation_fcfa: [5000, [Validators.required, Validators.min(0)]],
    remise_fcfa: [0, [Validators.required, Validators.min(0)]],
  });

  get totalFcfa(): number {
    const m = Number(this.form.get('montant_consultation_fcfa')?.value ?? 0);
    const r = Number(this.form.get('remise_fcfa')?.value ?? 0);
    return Math.max(0, m - r);
  }

  ngOnInit(): void {
    this.accueil.listeMedecins().subscribe({
      next: (list) => {
        this.medecins = list;
      },
      error: () => {
        this.errorMsg =
          "Impossible de charger la liste des médecins. Vérifiez votre rôle (accueil) et l'API.";
      },
    });
  }

  resetForm(): void {
    this.form.reset({
      nom: '',
      prenom: '',
      date_naissance: '',
      sexe: 'M',
      telephone: '',
      email: '',
      contact_urgence: '',
      derniere_date_regles: '',
      poids_kg: null,
      taille_cm: null,
      temperature_c: null,
      tension: '',
      motif_consultation: '',
      type_consultation: 'generale',
      medecin_id: '',
      est_assure: 'non',
      compagnie_assurance: '',
      date_validite_assurance: '',
      numero_assure: '',
      montant_consultation_fcfa: 5000,
      remise_fcfa: 0,
    });
    this.errorMsg = '';
  }

  nouveauDossier(): void {
    this.success = null;
    this.resetForm();
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const estAssure = v.est_assure === 'oui';

    const payload: InscriptionPayload = {
      nom: (v.nom ?? '').trim(),
      prenom: (v.prenom ?? '').trim(),
      date_naissance: v.date_naissance || null,
      sexe: (v.sexe ?? 'M') as InscriptionPayload['sexe'],
      telephone: v.telephone?.trim() || null,
      email: v.email?.trim() || null,
      contact_urgence: v.contact_urgence?.trim() || null,
      poids_kg: v.poids_kg != null ? Number(v.poids_kg) : null,
      taille_cm: v.taille_cm != null ? Number(v.taille_cm) : null,
      temperature_c: v.temperature_c != null ? Number(v.temperature_c) : null,
      tension: v.tension?.trim() || null,
      motif_consultation: v.motif_consultation?.trim() || '',
      type_consultation: (v.type_consultation ??
        'generale') as InscriptionPayload['type_consultation'],
      medecin_id: v.medecin_id ?? '',
      derniere_date_regles:
        v.sexe === 'F' && v.derniere_date_regles
          ? v.derniere_date_regles
          : null,
      est_assure: estAssure,
      compagnie_assurance: estAssure
        ? v.compagnie_assurance?.trim() || null
        : null,
      date_validite_assurance: estAssure
        ? v.date_validite_assurance || null
        : null,
      numero_assure: estAssure ? v.numero_assure?.trim() || null : null,
      montant_consultation_fcfa: Number(v.montant_consultation_fcfa),
      remise_fcfa: Number(v.remise_fcfa),
    };

    this.submitting = true;
    this.errorMsg = '';
    this.accueil.enregistrerPatient(payload).subscribe({
      next: (res) => {
        this.submitting = false;
        this.success = res;
      },
      error: (err: HttpErrorResponse) => {
        this.submitting = false;
        const d = err.error?.detail;
        if (typeof d === 'string') {
          this.errorMsg = d;
        } else if (Array.isArray(d)) {
          this.errorMsg = d
            .map((x: { msg?: string }) => x?.msg)
            .filter(Boolean)
            .join(' ');
        } else {
          this.errorMsg = `Erreur ${err.status}. Réessayez ou vérifiez l'API.`;
        }
      },
    });
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
