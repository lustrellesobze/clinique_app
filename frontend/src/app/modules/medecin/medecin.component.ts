import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  FormArray,
  FormBuilder,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import { AuthService } from '../../core/auth/auth.service';
import {
  DoctorPatient,
  MedecinService,
  PatientRecordOut,
} from '../../core/services/medecin.service';

@Component({
  selector: 'app-medecin',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './medecin.component.html',
  styleUrls: ['./medecin.component.scss'],
})
export class MedecinComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly medecin = inject(MedecinService);

  loading = false;
  saving = false;
  successMsg = '';
  errorMsg = '';

  allPatients: DoctorPatient[] = [];
  filteredPatients: DoctorPatient[] = [];
  selectedPatient: DoctorPatient | null = null;
  record: PatientRecordOut | null = null;
  selectedPassageId = '';
  searchTerm = '';

  consultationForm = this.fb.group({
    observations: [''],
    diagnostic: [''],
    poids_kg: [null as number | null],
    taille_cm: [null as number | null],
    temperature_c: [null as number | null],
    tension: [''],
  });

  prescriptionForm = this.fb.group({
    type_prescription: [
      'pharmacie' as
        | 'pharmacie'
        | 'laboratoire'
        | 'imagerie'
        | 'hospitalisation'
        | 'specialiste'
        | 'chirurgie'
        | 'orl',
      Validators.required,
    ],
    notes: [''],
    items: this.fb.array([]),
    transfer_destination: [
      'pharmacie' as
        | 'pharmacie'
        | 'laboratoire'
        | 'imagerie'
        | 'hospitalisation'
        | 'specialiste'
        | 'chirurgie'
        | 'orl',
      Validators.required,
    ],
  });

  get itemsArray(): FormArray {
    return this.prescriptionForm.get('items') as FormArray;
  }

  ngOnInit(): void {
    this.ajouterItem();
    this.chargerPatients();
  }

  chargerPatients(): void {
    this.loading = true;
    this.medecin.listePatientsAffectes().subscribe({
      next: (rows) => {
        this.loading = false;
        this.allPatients = rows;
        this.filteredPatients = rows;
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  filtrerPatients(): void {
    const t = this.searchTerm.trim().toLowerCase();
    if (!t) {
      this.filteredPatients = this.allPatients;
      return;
    }
    this.filteredPatients = this.allPatients.filter((p) =>
      [p.code_patient, p.nom, p.prenom, p.telephone || '']
        .join(' ')
        .toLowerCase()
        .includes(t)
    );
  }

  choisirPatient(p: DoctorPatient): void {
    this.selectedPatient = p;
    this.selectedPassageId = p.passage_id;
    this.medecin.dossierPatient(p.patient_id).subscribe({
      next: (rec) => {
        this.record = rec;
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  ajouterItem(): void {
    this.itemsArray.push(
      this.fb.group({
        nom_item: ['', Validators.required],
        description: [''],
        quantite: [1, [Validators.required, Validators.min(1)]],
        prix_unitaire: [0, [Validators.required, Validators.min(0)]],
      })
    );
  }

  supprimerItem(index: number): void {
    if (this.itemsArray.length <= 1) return;
    this.itemsArray.removeAt(index);
  }

  enregistrerEtTransferer(): void {
    if (!this.selectedPatient) {
      this.errorMsg = 'Selectionnez un patient.';
      return;
    }
    if (this.prescriptionForm.invalid) {
      this.prescriptionForm.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.resetAlerts();
    const c = this.consultationForm.getRawValue();
    const p = this.prescriptionForm.getRawValue();
    const items = (p.items || []) as Array<{
      nom_item?: string;
      description?: string | null;
      quantite?: number;
      prix_unitaire?: number;
    }>;

    this.medecin
      .updateConsultation(this.selectedPassageId, {
        observations: c.observations ?? undefined,
        diagnostic: c.diagnostic ?? undefined,
        statut: 'attente_paiement',
        poids_kg: c.poids_kg,
        taille_cm: c.taille_cm,
        temperature_c: c.temperature_c,
        tension: c.tension,
      })
      .subscribe({
        next: () => {
          this.medecin
            .creerPrescription({
              patient_id: this.selectedPatient!.patient_id,
              passage_accueil_id: this.selectedPassageId,
              type_prescription: p.type_prescription!,
              notes: p.notes || null,
              items: items.map((x) => ({
                nom_item: x.nom_item || '',
                description: x.description || null,
                quantite: Number(x.quantite || 1),
                prix_unitaire: Number(x.prix_unitaire || 0),
              })),
            })
            .subscribe({
              next: (created) => {
                this.medecin
                  .transfererPrescription(
                    created.id,
                    p.transfer_destination!,
                    'Transfert depuis interface medecin'
                  )
                  .subscribe({
                    next: () => {
                      this.saving = false;
                      this.successMsg = `Prescription transferee vers ${p.transfer_destination}.`;
                      this.choisirPatient(this.selectedPatient!);
                    },
                    error: (err: HttpErrorResponse) => {
                      this.saving = false;
                      this.errorMsg = this.errorFromHttp(err);
                    },
                  });
              },
              error: (err: HttpErrorResponse) => {
                this.saving = false;
                this.errorMsg = this.errorFromHttp(err);
              },
            });
        },
        error: (err: HttpErrorResponse) => {
          this.saving = false;
          this.errorMsg = this.errorFromHttp(err);
        },
      });
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }

  private resetAlerts(): void {
    this.successMsg = '';
    this.errorMsg = '';
  }

  private errorFromHttp(err: HttpErrorResponse): string {
    const d = err.error?.detail;
    if (typeof d === 'string') return d;
    return `Erreur ${err.status || 500}`;
  }
}
