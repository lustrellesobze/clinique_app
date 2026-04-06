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

  // Redirection
  { path: '**', redirectTo: '' },
];
