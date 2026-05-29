import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  FormArray,
  FormBuilder,
  ReactiveFormsModule,
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin, Observable, of, switchMap } from 'rxjs';
import {
  DoctorLookup,
  DoctorPatient,
  MedecinService,
  PatientRecordOut,
  PrescriptionItemIn,
  PrescriptionOut,
  TransferDestination,
} from '../../core/services/medecin.service';

import { AuthService } from '../../core/auth/auth.service';

/** Ligne examen (hors FormArray — affichage fiable) */
export interface ExamenLigne {
  uid: number;
  nom: string;
  actif: boolean;
}

/** Confirmation affichée après transfert */
export interface TransfertLigne {
  libelle: string;
  detail: string;
  icone: string;
}

const LIBELLE_DESTINATION: Record<TransferDestination, string> = {
  pharmacie: 'Pharmacie',
  laboratoire: 'Laboratoire',
  imagerie: 'Imagerie',
  hospitalisation: 'Hospitalisation',
  specialiste: 'Spécialiste',
  chirurgie: 'Chirurgie',
  orl: 'ORL',
};

@Component({
  selector: 'app-medecin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './medecin.component.html',
  styleUrls: ['./medecin.component.scss'],
})
export class MedecinComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly medecin = inject(MedecinService);
  private readonly cdr = inject(ChangeDetectorRef);

  now = new Date();
  loadingSearch = false;
  saving = false;
  successMsg = '';
  errorMsg = '';
  transfertLignes: TransfertLigne[] = [];

  allPatients: DoctorPatient[] = [];

  searchForm = this.fb.group({
    code: [''],
  });
  selectedPatient: DoctorLookup | null = null;
  record: PatientRecordOut | null = null;
  selectedPassageId = '';

  /** Orientations optionnelles (hospitalisation, spécialiste…) */
  extraOrientations: TransferDestination[] = [];

  /** Examens en liste simple (évite les bugs FormArray imbriqués) */
  examensLignes: ExamenLigne[] = [];
  private examenUidSeq = 0;

  readonly examensCourants = [
    'Numération Formule Sanguine (NFS)',
    'Glycémie à jeun',
    'Créatininémie',
    'BU (Bandelette urinaire)',
  ];

  /** Formulaire consultation + médicaments */
  dossierForm = this.fb.group({
    observations: [''],
    diagnostic: [''],
    medicaments: this.fb.array([]),
  });

  ngOnInit(): void {
    this.medecin.listePatientsAffectes().subscribe({
      next: (rows) => {
        this.allPatients = rows;
      },
      error: () => {},
    });
  }

  get medicamentsArray(): FormArray {
    return this.dossierForm.get('medicaments') as FormArray;
  }

  /** Médicaments renseignés (transfert auto pharmacie à l'enregistrement) */
  get nbMedicamentsRenseignes(): number {
    return this.buildMedicamentItems().length;
  }

  /** Examens cochés et nommés (transfert auto laboratoire à l'enregistrement) */
  get nbExamensActifs(): number {
    return this.buildExamenItems().length;
  }

  get medecinLibelle(): string {
    const u = this.auth.getCurrentUser();
    if (!u) return 'Médecin';
    return `Dr ${u.prenom} ${u.nom} (${u.service || 'Médecine générale'})`;
  }

  get dateHeureEntete(): string {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(this.now);
  }

  trackByIndex(index: number): number {
    return index;
  }

  trackExamenUid(_: number, ex: ExamenLigne): number {
    return ex.uid;
  }

  get sexeLabel(): string {
    const s = this.selectedPatient?.sexe;
    if (s === 'M') return 'Masculin';
    if (s === 'F') return 'Féminin';
    return s || '—';
  }

  get derniereConsultationLabel(): string {
    const d =
      this.record?.derniere_consultation || this.selectedPatient?.derniere_consultation;
    if (!d) return '—';
    return new Intl.DateTimeFormat('fr-FR').format(new Date(d));
  }

  private createMedicamentGroup() {
    return this.fb.group({
      nom: [''],
      quantite_libelle: [''],
      instructions: [''],
    });
  }

  private reinitialiserPrescriptions(): void {
    this.dossierForm.setControl('medicaments', this.fb.array([]));
    this.examensLignes = [];
    this.examenUidSeq = 0;
  }

  rechercherPatient(): void {
    const code = (this.searchForm.get('code')?.value ?? '').trim();
    if (!code) {
      this.errorMsg = 'Saisissez un ID patient.';
      return;
    }
    this.resetAlerts();
    this.loadingSearch = true;
    this.medecin.lookupParCode(code).subscribe({
      next: (p) => {
        this.loadingSearch = false;
        this.selectionnerPatient(p);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingSearch = false;
        this.errorMsg = this.errorFromHttp(err);
        this.selectedPatient = null;
        this.record = null;
      },
    });
  }

  selectionnerPatient(
    p: DoctorLookup | DoctorPatient,
    options?: { conserverMessages?: boolean }
  ): void {
    if (!options?.conserverMessages) {
      this.resetAlerts();
    }
    this.extraOrientations = [];
    this.reinitialiserPrescriptions();
    this.dossierForm.patchValue({ observations: '', diagnostic: '' });

    const base: DoctorLookup =
      'age_ans' in p
        ? p
        : {
            ...p,
            date_naissance: null,
            sexe: null,
            age_ans: null,
            derniere_consultation: null,
            allergies_connues: 'Aucune connue',
          };

    this.selectedPatient = base;
    this.selectedPassageId = base.passage_id;
    this.searchForm.patchValue({ code: base.code_patient });

    this.medecin.dossierPatient(base.patient_id).subscribe({
      next: (rec) => {
        this.record = rec;
        this.selectedPatient = {
          ...base,
          age_ans: rec.age_ans ?? base.age_ans,
          sexe: rec.sexe ?? base.sexe,
          date_naissance: rec.date_naissance ?? base.date_naissance,
          derniere_consultation:
            rec.derniere_consultation ?? base.derniere_consultation,
          allergies_connues: rec.allergies_connues,
          assureur: rec.assureur ?? base.assureur,
        };
        const passage = rec.passages.find((x) => x.passage_id === base.passage_id);
        if (passage) {
          const parsed = this.parseMotif(passage.motif_consultation);
          this.dossierForm.patchValue({
            observations: parsed.observations,
            diagnostic: parsed.diagnostic,
          });
        }
      },
      error: (err: HttpErrorResponse) => {
        this.errorMsg = this.errorFromHttp(err);
      },
    });
  }

  ajouterMedicament(): void {
    this.medicamentsArray.push(this.createMedicamentGroup());
    this.cdr.markForCheck();
  }

  supprimerMedicament(index: number): void {
    this.medicamentsArray.removeAt(index);
    this.cdr.markForCheck();
  }

  ajouterExamen(nom = ''): void {
    this.examensLignes = [
      ...this.examensLignes,
      { uid: ++this.examenUidSeq, nom, actif: true },
    ];
    this.cdr.detectChanges();
  }

  ajouterExamenCourant(libelle: string): void {
    const exists = this.examensLignes.some(
      (x) => x.nom.trim().toLowerCase() === libelle.trim().toLowerCase()
    );
    if (exists) return;
    this.ajouterExamen(libelle);
  }

  supprimerExamen(uid: number): void {
    this.examensLignes = this.examensLignes.filter((x) => x.uid !== uid);
    this.cdr.detectChanges();
  }

  onExamenNomInput(ex: ExamenLigne, value: string): void {
    ex.nom = value;
  }

  onExamenActifChange(ex: ExamenLigne, checked: boolean): void {
    ex.actif = checked;
  }

  toggleOrientation(dest: TransferDestination): void {
    if (dest === 'pharmacie' || dest === 'laboratoire') return;
    const i = this.extraOrientations.indexOf(dest);
    if (i >= 0) {
      this.extraOrientations.splice(i, 1);
    } else {
      this.extraOrientations.push(dest);
    }
  }

  orientationActive(dest: TransferDestination): boolean {
    return this.extraOrientations.includes(dest);
  }

  annuler(): void {
    this.selectedPatient = null;
    this.record = null;
    this.searchForm.reset({ code: '' });
    this.extraOrientations = [];
    this.reinitialiserPrescriptions();
    this.dossierForm.patchValue({ observations: '', diagnostic: '' });
    this.resetAlerts();
  }

  enregistrerEtTransferer(): void {
    if (!this.selectedPatient) {
      this.errorMsg = 'Recherchez et sélectionnez un patient.';
      return;
    }

    const meds = this.buildMedicamentItems();
    const exams = this.buildExamenItems();
    const extras = [...this.extraOrientations];

    if (
      !this.dossierForm.value.observations?.trim() &&
      !this.dossierForm.value.diagnostic?.trim() &&
      meds.length === 0 &&
      exams.length === 0 &&
      extras.length === 0
    ) {
      this.errorMsg =
        'Renseignez au moins les observations, un diagnostic, une prescription ou une orientation.';
      return;
    }

    this.saving = true;
    this.resetAlerts();
    const c = this.dossierForm.getRawValue();

    this.medecin
      .updateConsultation(this.selectedPassageId, {
        observations: c.observations ?? undefined,
        diagnostic: c.diagnostic ?? undefined,
        statut: 'en_consultation',
      })
      .pipe(
        switchMap(() => {
          const tasks: Observable<PrescriptionOut>[] = [];

          if (meds.length) {
            tasks.push(
              this.medecin.creerPrescription({
                patient_id: this.selectedPatient!.patient_id,
                passage_accueil_id: this.selectedPassageId,
                type_prescription: 'pharmacie',
                notes: 'Ordonnance pharmacie — sans contrôle stock',
                items: meds,
              })
            );
          }
          if (exams.length) {
            tasks.push(
              this.medecin.creerPrescription({
                patient_id: this.selectedPatient!.patient_id,
                passage_accueil_id: this.selectedPassageId,
                type_prescription: 'laboratoire',
                notes: 'Prescription examens laboratoire',
                items: exams,
              })
            );
          }
          for (const dest of extras) {
            tasks.push(
              this.medecin.creerPrescription({
                patient_id: this.selectedPatient!.patient_id,
                passage_accueil_id: this.selectedPassageId,
                type_prescription: dest,
                notes: `Orientation vers ${dest}`,
                items: [
                  {
                    nom_item: `Orientation ${dest}`,
                    description: c.diagnostic || null,
                    quantite: 1,
                    prix_unitaire: 0,
                  },
                ],
              })
            );
          }

          if (!tasks.length) return of<PrescriptionOut[]>([]);
          return forkJoin(tasks);
        }),
        switchMap((created) => {
          if (!created.length) {
            return of(null);
          }
          const transfers = created.map((pr) =>
            this.medecin.transfererPrescription(
              pr.id,
              pr.type_prescription as TransferDestination,
              'Transfert depuis interface médecin'
            )
          );
          return forkJoin(transfers);
        }),
        switchMap(() =>
          this.medecin.updateConsultation(this.selectedPassageId, {
            statut: 'attente_paiement',
          })
        )
      )
      .subscribe({
        next: () => {
          this.saving = false;
          this.afficherConfirmationTransfert(meds.length, exams.length, extras);
          if (this.selectedPatient) {
            this.selectionnerPatient(this.selectedPatient, {
              conserverMessages: true,
            });
          }
          this.cdr.detectChanges();
          setTimeout(() => this.scrollVersConfirmation(), 100);
        },
        error: (err: HttpErrorResponse) => {
          this.saving = false;
          this.errorMsg = this.errorFromHttp(err);
          this.transfertLignes = [];
          this.cdr.detectChanges();
        },
      });
  }

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }

  private buildMedicamentItems(): PrescriptionItemIn[] {
    const items: PrescriptionItemIn[] = [];
    for (const ctrl of this.medicamentsArray.controls) {
      const v = ctrl.getRawValue();
      if (!v.nom?.trim()) continue;
      const desc = [
        v.quantite_libelle?.trim()
          ? `Quantité: ${v.quantite_libelle.trim()}`
          : '',
        v.instructions?.trim()
          ? `Instructions: ${v.instructions.trim()}`
          : '',
      ]
        .filter(Boolean)
        .join('\n');
      items.push({
        nom_item: v.nom.trim(),
        description: desc || null,
        quantite: 1,
        prix_unitaire: 0,
      });
    }
    return items;
  }

  private buildExamenItems(): PrescriptionItemIn[] {
    return this.examensLignes
      .filter((ex) => ex.actif && ex.nom.trim())
      .map((ex) => ({
        nom_item: ex.nom.trim(),
        description: null,
        quantite: 1,
        prix_unitaire: 0,
      }));
  }

  private parseMotif(motif: string): { observations: string; diagnostic: string } {
    let observations = '';
    let diagnostic = '';
    const obsIdx = motif.indexOf('Observations medecin:');
    const diagIdx = motif.indexOf('Diagnostic:');
    if (obsIdx >= 0) {
      const start = obsIdx + 'Observations medecin:'.length;
      const end = diagIdx >= 0 ? diagIdx : motif.length;
      observations = motif.slice(start, end).trim();
    }
    if (diagIdx >= 0) {
      diagnostic = motif.slice(diagIdx + 'Diagnostic:'.length).trim();
    }
    return { observations, diagnostic };
  }

  private afficherConfirmationTransfert(
    nbMedicaments: number,
    nbExamens: number,
    extras: TransferDestination[]
  ): void {
    this.errorMsg = '';
    this.transfertLignes = [];

    if (nbMedicaments > 0) {
      this.transfertLignes.push({
        icone: '💊',
        libelle: 'Pharmacie',
        detail:
          nbMedicaments === 1
            ? '1 médicament transféré — ordonnance disponible à la pharmacie.'
            : `${nbMedicaments} médicaments transférés — ordonnance disponible à la pharmacie.`,
      });
    }
    if (nbExamens > 0) {
      this.transfertLignes.push({
        icone: '🔬',
        libelle: 'Laboratoire',
        detail:
          nbExamens === 1
            ? '1 examen transféré — prescription disponible au laboratoire.'
            : `${nbExamens} examens transférés — prescription disponible au laboratoire.`,
      });
    }
    for (const dest of extras) {
      const lib = LIBELLE_DESTINATION[dest] ?? dest;
      this.transfertLignes.push({
        icone: '📋',
        libelle: lib,
        detail: `Orientation enregistrée vers ${lib}.`,
      });
    }

    if (this.transfertLignes.length > 0) {
      this.successMsg =
        'Consultation enregistrée. Les prescriptions ont été transférées :';
    } else {
      this.successMsg =
        'Consultation enregistrée (observations et diagnostic sauvegardés).';
    }
  }

  private scrollVersConfirmation(): void {
    const el = document.getElementById('medecin-transfert-confirmation');
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  fermerConfirmation(): void {
    this.resetAlerts();
  }

  private resetAlerts(): void {
    this.successMsg = '';
    this.errorMsg = '';
    this.transfertLignes = [];
  }

  private errorFromHttp(err: HttpErrorResponse): string {
    const d = err.error?.detail;
    if (typeof d === 'string') return d;
    return `Erreur ${err.status || 500}`;
  }
}
