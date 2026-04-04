import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, throwError } from 'rxjs';
import {
  LoginRequest,
  LoginResponse,
  UserInfo,
  ROLE_ROUTES,
} from '../models/auth.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Base API (FastAPI : préfixe /api sur les routeurs) */
  private readonly API_URL = `${environment.apiUrl.replace(/\/+$/, '')}/api`;
  private readonly TOKEN_KEY = 'clinique_token';
  private readonly USER_KEY = 'clinique_user';

  // Observable du user courant — tous les composants peuvent s'y abonner
  private currentUserSubject = new BehaviorSubject<UserInfo | null>(
    this.getUserFromStorage()
  );
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  // ─── LOGIN ────────────────────────────────────────────────────────────
  login(credentials: LoginRequest): Observable<LoginResponse> {
    // FastAPI attend un form-data pour OAuth2PasswordRequestForm
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    return this.http.post<LoginResponse>(`${this.API_URL}/auth/login`, formData).pipe(
      tap((response) => {
        // Stocker le token et les infos user
        localStorage.setItem(this.TOKEN_KEY, response.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(response.user));
        this.currentUserSubject.next(response.user);
      }),
      catchError((error) => {
        const message =
          error.status === 401
            ? 'Email ou mot de passe incorrect.'
            : error.status === 0
              ? 'Impossible de contacter le serveur. Vérifiez votre connexion.'
              : 'Une erreur est survenue. Veuillez réessayer.';
        return throwError(() => new Error(message));
      })
    );
  }

  // ─── LOGOUT ───────────────────────────────────────────────────────────
  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUserSubject.next(null);
    this.router.navigate(['/']);
  }

  // ─── TOKEN ────────────────────────────────────────────────────────────
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  isLoggedIn(): boolean {
    const token = this.getToken();
    if (!token) return false;
    // Vérifier si le token n'est pas expiré
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  // ─── USER ─────────────────────────────────────────────────────────────
  getCurrentUser(): UserInfo | null {
    return this.currentUserSubject.value;
  }

  hasRole(role: string | string[]): boolean {
    const user = this.getCurrentUser();
    if (!user) return false;
    if (Array.isArray(role)) return role.includes(user.role);
    return user.role === role;
  }

  // Rediriger vers la bonne page selon le rôle
  redirectByRole(): void {
    const user = this.getCurrentUser();
    if (!user) {
      this.router.navigate(['/']);
      return;
    }
    const route = ROLE_ROUTES[user.role] ?? '/dashboard';
    this.router.navigate([route]);
  }

  // ─── PRIVATE ──────────────────────────────────────────────────────────
  private getUserFromStorage(): UserInfo | null {
    try {
      const raw = localStorage.getItem(this.USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
