import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="page">
      <div class="card">
        <h1>Mot de passe oublié</h1>
        <p>Page à brancher sur l’API (réinitialisation par email).</p>
        <a routerLink="/login">← Retour à la connexion</a>
      </div>
    </div>
  `,
  styles: `
    .page {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 1.5rem;
      background: var(--bg-app);
    }
    .card {
      max-width: 400px;
      padding: 2rem;
      background: var(--bg-card);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-md);
      border: 1px solid var(--border);
    }
    h1 {
      margin: 0 0 0.75rem;
      font-size: 1.35rem;
      color: var(--text-primary);
    }
    p {
      margin: 0 0 1.25rem;
      color: var(--text-secondary);
      font-size: 0.95rem;
      line-height: 1.5;
    }
    a {
      color: var(--primary);
      font-weight: 600;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
  `,
})
export class ForgotPasswordComponent {}
