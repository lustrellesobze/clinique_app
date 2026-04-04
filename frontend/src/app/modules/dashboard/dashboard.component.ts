import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="shell">
      <header>
        <h1>Tableau de bord</h1>
        <nav>
          <a routerLink="/accueil">Accueil</a>
          <a routerLink="/login" (click)="onLogout($event)">Déconnexion</a>
        </nav>
      </header>
      <p class="hint">Module dashboard — contenu à venir.</p>
    </div>
  `,
  styles: `
    .shell {
      padding: 1.5rem;
      max-width: 960px;
      margin: 0 auto;
    }
    header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    h1 {
      margin: 0;
      font-size: 1.35rem;
      color: var(--text-primary);
    }
    nav {
      display: flex;
      gap: 1rem;
    }
    a {
      color: var(--primary);
      font-weight: 600;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .hint {
      color: var(--text-secondary);
      margin: 0;
    }
  `,
})
export class DashboardComponent {
  private readonly auth = inject(AuthService);

  onLogout(event: Event): void {
    event.preventDefault();
    this.auth.logout();
  }
}
