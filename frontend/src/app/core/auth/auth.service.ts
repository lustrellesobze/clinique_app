import { Injectable } from '@angular/core';
import {
  HttpBackend,
  HttpClient,
  HttpErrorResponse,
  HttpHeaders,
  HttpParams,
} from '@angular/common/http';
import { Router } from '@angular/router';
import {
  BehaviorSubject,
  Observable,
  tap,
  catchError,
  throwError,
  shareReplay,
  finalize,
} from 'rxjs';
import {
  GoogleAuthConfig,
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
  private readonly REFRESH_KEY = 'clinique_refresh_token';
  private readonly USER_KEY = 'clinique_user';

  /** HttpClient sans intercepteurs — évite boucle 401 sur /auth/refresh */
  private readonly plainHttp: HttpClient;

  private refreshInFlight: Observable<LoginResponse> | null = null;

  // Observable du user courant — tous les composants peuvent s'y abonner
  private currentUserSubject = new BehaviorSubject<UserInfo | null>(
    this.getUserFromStorage()
  );
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private http: HttpClient,
    httpBackend: HttpBackend,
    private router: Router
  ) {
    this.plainHttp = new HttpClient(httpBackend);
  }

  getGoogleAuthConfig(): Observable<GoogleAuthConfig> {
    return this.http.get<GoogleAuthConfig>(`${this.API_URL}/auth/google/config`);
  }

  /** Connexion Google — réservée au rôle infirmière d'accueil. */
  loginWithGoogle(credential: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${this.API_URL}/auth/google`, { credential })
      .pipe(
        tap((response) => {
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          localStorage.setItem(this.REFRESH_KEY, response.refresh_token);
          localStorage.setItem(this.USER_KEY, JSON.stringify(response.user));
          this.currentUserSubject.next(response.user);
        }),
        catchError((err: unknown) => {
          const message =
            err instanceof HttpErrorResponse
              ? this.mapLoginError(err)
              : 'Erreur inattendue. Réessayez.';
          return throwError(() => new Error(message));
        })
      );
  }

  // ─── LOGIN ────────────────────────────────────────────────────────────
  login(credentials: LoginRequest): Observable<LoginResponse> {
    // OAuth2PasswordRequestForm : application/x-www-form-urlencoded, champs username + password
    const body = new HttpParams()
      .set('username', credentials.email.trim())
      .set('password', credentials.password);
    const headers = new HttpHeaders().set(
      'Content-Type',
      'application/x-www-form-urlencoded; charset=UTF-8'
    );

    return this.http
      .post<LoginResponse>(`${this.API_URL}/auth/login`, body, { headers })
      .pipe(
        tap((response) => {
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          localStorage.setItem(this.REFRESH_KEY, response.refresh_token);
          localStorage.setItem(this.USER_KEY, JSON.stringify(response.user));
          this.currentUserSubject.next(response.user);
        }),
        catchError((err: unknown) => {
          const message =
            err instanceof HttpErrorResponse
              ? this.mapLoginError(err)
              : 'Erreur inattendue. Réessayez.';
          return throwError(() => new Error(message));
        })
      );
  }

  private mapLoginError(error: HttpErrorResponse): string {
    const raw = error.error;
    if (error.status === 401) {
      return 'Email ou mot de passe incorrect.';
    }
    if (error.status === 503) {
      const detail = this.fastApiDetailMessage(raw);
      if (detail) {
        return detail;
      }
      return (
        'Service ou base de données indisponible. Ouvrez http://127.0.0.1:8000/health : ' +
        'si « database » n’est pas « connected », démarrez WAMP / MySQL et vérifiez backend/.env.'
      );
    }
    if (error.status === 0) {
      return "Impossible de joindre l'API (port 8000). Démarrez le backend : dans le dossier backend, exécutez « uvicorn app.main:app --reload » puis réessayez.";
    }
    if (error.status === 502 || error.status === 504) {
      return "L'API sur le port 8000 ne répond pas. Vérifiez qu'Uvicorn est bien démarré.";
    }
    const fromDetail = this.fastApiDetailMessage(raw);
    if (fromDetail) {
      return fromDetail;
    }
    if (error.status >= 500) {
      return `Erreur serveur (${error.status}). Vérifiez la console Uvicorn et la connexion MySQL (fichier .env, base clinique_db).`;
    }
    if (typeof raw === 'string' && raw.length > 0 && raw.length < 400) {
      return `Réponse serveur (${error.status}) : ${raw.trim().slice(0, 200)}`;
    }
    return `Erreur ${error.status}${error.statusText ? ' — ' + error.statusText : ''}. Réessayez ou ouvrez /docs sur l’API.`;
  }

  /** Supprime la session locale (token + utilisateur). */
  clearSession(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUserSubject.next(null);
  }

  // ─── LOGOUT ───────────────────────────────────────────────────────────
  logout(): void {
    this.clearSession();
    this.router.navigate(['/']);
  }

  // ─── TOKEN ────────────────────────────────────────────────────────────
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_KEY);
  }

  /**
   * Renouvelle access + refresh (requête hors intercepteur JWT).
   * Multiples appels concurrents partagent la même requête réseau.
   */
  refreshAccessToken(): Observable<LoginResponse> {
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }
    const rt = localStorage.getItem(this.REFRESH_KEY);
    if (!rt) {
      return throwError(() => new Error('Pas de refresh token'));
    }
    this.refreshInFlight = this.plainHttp
      .post<LoginResponse>(`${this.API_URL}/auth/refresh`, { refresh_token: rt })
      .pipe(
        tap((response) => {
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          localStorage.setItem(this.REFRESH_KEY, response.refresh_token);
          localStorage.setItem(this.USER_KEY, JSON.stringify(response.user));
          this.currentUserSubject.next(response.user);
        }),
        shareReplay({ bufferSize: 1, refCount: false }),
        finalize(() => {
          this.refreshInFlight = null;
        })
      );
    return this.refreshInFlight;
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
      this.clearSession();
      this.router.navigate(['/login']);
      return;
    }
    const route = ROLE_ROUTES[user.role] ?? '/dashboard';
    this.router.navigateByUrl(route);
  }

  /** Corps d’erreur FastAPI `{ detail: string | … }`. */
  private fastApiDetailMessage(raw: unknown): string | null {
    if (!raw || typeof raw !== 'object' || !('detail' in raw)) {
      return null;
    }
    const d = (raw as { detail: unknown }).detail;
    if (typeof d === 'string') {
      return d;
    }
    if (Array.isArray(d)) {
      const parts = d
        .map((x: { msg?: string }) => x?.msg)
        .filter(Boolean)
        .join(' ');
      return parts || null;
    }
    return null;
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
