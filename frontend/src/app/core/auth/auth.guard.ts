import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  Router,
} from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    // Vérifier si connecté
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return false;
    }

    // Vérifier le rôle si la route le précise
    const allowedRoles = route.data?.['roles'] as string[] | undefined;
    if (allowedRoles && allowedRoles.length > 0) {
      if (!this.authService.hasRole(allowedRoles)) {
        // Connecté mais pas le bon rôle → rediriger vers sa page
        this.authService.redirectByRole();
        return false;
      }
    }

    return true;
  }
}
