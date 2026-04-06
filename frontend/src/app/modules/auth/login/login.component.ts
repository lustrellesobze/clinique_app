import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  /** Affiche l’aide comptes démo uniquement hors production */
  readonly devDemoHint = !environment.production;

  /** Textes avec « @ » : dans le HTML, « @ » déclenche la syntaxe Angular (@if, etc.) */
  readonly demoEmailExamples =
    'accueil@demo.cm · medecin@demo.cm · admin@demo.cm · …';
  readonly demoPassword = 'demo123';

  loginForm!: FormGroup;
  isLoading = false;
  showPassword = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    // Si déjà connecté → rediriger directement
    if (this.authService.isLoggedIn()) {
      this.authService.redirectByRole();
    }
  }

  // ─── GETTERS (raccourcis dans le template) ───────────────────────────
  get email() {
    return this.loginForm.get('email');
  }

  get password() {
    return this.loginForm.get('password');
  }

  // ─── SOUMISSION ───────────────────────────────────────────────────────
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
        // Redirection automatique selon le rôle
        this.authService.redirectByRole();
      },
      error: (err: Error) => {
        this.isLoading = false;
        this.errorMessage = err.message;
      },
    });
  }
}
