import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  @ViewChild('googleBtnHost') googleBtnHost?: ElementRef<HTMLDivElement>;

  loginForm!: FormGroup;
  isLoading = false;
  showPassword = false;
  errorMessage = '';

  googleEnabled = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    if (this.authService.isLoggedIn() && this.authService.getCurrentUser()) {
      this.authService.redirectByRole();
      return;
    }
    if (this.authService.getToken()) {
      this.authService.clearSession();
    }

    this.authService.getGoogleAuthConfig().subscribe({
      next: (cfg) => {
        if (cfg.enabled && cfg.client_id) {
          this.googleEnabled = true;
          this.cdr.detectChanges();
          setTimeout(() => this.initGoogleButton(cfg.client_id), 0);
        }
      },
    });
  }

  get email() {
    return this.loginForm.get('email');
  }

  get password() {
    return this.loginForm.get('password');
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        this.isLoading = false;
        this.authService.redirectByRole();
      },
      error: (err: Error) => {
        this.isLoading = false;
        this.errorMessage = err.message;
      },
    });
  }

  onGoogleCredential(credential: string): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.authService.loginWithGoogle(credential).subscribe({
      next: () => {
        this.isLoading = false;
        this.authService.redirectByRole();
      },
      error: (err: Error) => {
        this.isLoading = false;
        this.errorMessage = err.message;
      },
    });
  }

  private loadGoogleScript(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (window.google?.accounts?.id) {
        resolve();
        return;
      }
      const existing = document.querySelector('script[data-google-gsi]');
      if (existing) {
        existing.addEventListener('load', () => resolve());
        existing.addEventListener('error', () => reject());
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.dataset['googleGsi'] = '1';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Script Google indisponible'));
      document.head.appendChild(script);
    });
  }

  private async initGoogleButton(clientId: string): Promise<void> {
    try {
      await this.loadGoogleScript();
      const host = this.googleBtnHost?.nativeElement;
      if (!host || !window.google?.accounts?.id) {
        return;
      }
      host.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response: { credential: string }) => {
          this.onGoogleCredential(response.credential);
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      const width = Math.min(360, host.offsetWidth || 328);
      window.google.accounts.id.renderButton(host, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        width,
        locale: 'fr',
      });
    } catch {
      this.googleEnabled = false;
      this.cdr.detectChanges();
    }
  }
}
