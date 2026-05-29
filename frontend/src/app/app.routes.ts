import { Routes } from '@angular/router';
import { SplashComponent } from './modules/auth/splash/splash.component';
import { LoginComponent } from './modules/auth/login/login.component';
import { AuthGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  // Page d'accueil = splash screen
  { path: '', component: SplashComponent },

  // Login
  { path: 'login', component: LoginComponent },

  // Mot de passe oublié (lien depuis la page login)
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('./modules/auth/forgot-password/forgot-password.component').then(
        (m) => m.ForgotPasswordComponent
      ),
  },

  // Modules protégés (après connexion)
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./modules/dashboard/dashboard.component').then(
        (m) => m.DashboardComponent
      ),
    canActivate: [AuthGuard],
  },
  {
    path: 'accueil',
    loadComponent: () =>
      import('./modules/accueil/accueil.component').then(
        (m) => m.AccueilComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['infirmiere_accueil', 'admin'] },
  },
  {
    path: 'caisse',
    loadComponent: () =>
      import('./modules/caisse/caisse.component').then((m) => m.CaisseComponent),
    canActivate: [AuthGuard],
    data: { roles: ['caissier_central', 'admin'] },
  },
  {
    path: 'medecin',
    loadComponent: () =>
      import('./modules/medecin/medecin.component').then((m) => m.MedecinComponent),
    canActivate: [AuthGuard],
    data: { roles: ['medecin', 'admin'] },
  },
  {
    path: 'medecin/dashboard',
    loadComponent: () =>
      import('./modules/medecin/medecin.component').then((m) => m.MedecinComponent),
    canActivate: [AuthGuard],
    data: { roles: ['medecin', 'admin'] },
  },
  {
    path: 'pharmacie',
    loadComponent: () =>
      import('./modules/pharmacie/pharmacie.component').then(
        (m) => m.PharmacieComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['caissier_pharmacie', 'admin'] },
  },
  {
    path: 'laboratoire',
    loadComponent: () =>
      import('./modules/laboratoire/laboratoire.component').then(
        (m) => m.LaboratoireComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['caissier_labo', 'admin'] },
  },
  {
    path: 'imagerie',
    loadComponent: () =>
      import('./modules/imagerie/imagerie.component').then(
        (m) => m.ImagerieComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['caissier_imagerie', 'admin'] },
  },
  {
    path: 'hospitalisation',
    loadComponent: () =>
      import('./modules/hospitalisation/hospitalisation.component').then(
        (m) => m.HospitalisationComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['resp_hospit', 'admin'] },
  },
  {
    path: 'rapports',
    loadComponent: () =>
      import('./modules/rapports/rapports.component').then((m) => m.RapportsComponent),
    canActivate: [AuthGuard],
    data: { roles: ['admin', 'comptable'] },
  },
  {
    path: 'audit',
    loadComponent: () =>
      import('./modules/audit-log/audit-log.component').then((m) => m.AuditLogComponent),
    canActivate: [AuthGuard],
    data: { roles: ['admin'] },
  },
  {
    path: 'facturation',
    loadComponent: () =>
      import('./modules/facturation/facturation.component').then(
        (m) => m.FacturationComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['admin', 'comptable'] },
  },
  {
    path: 'assurances',
    loadComponent: () =>
      import('./modules/assurances/assurances.component').then(
        (m) => m.AssurancesComponent
      ),
    canActivate: [AuthGuard],
    data: { roles: ['gestionnaire_assurance', 'comptable', 'admin'] },
  },

  // Alias admin (évite retour au splash via wildcard)
  { path: 'admin', redirectTo: 'dashboard', pathMatch: 'full' },

  // Routes inconnues → splash (accueil)
  { path: '**', redirectTo: '' },
];
