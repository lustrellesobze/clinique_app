import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-splash',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './splash.component.html',
  styleUrl: './splash.component.scss',
})
export class SplashComponent implements OnInit {
  constructor(
    private router: Router,
    private auth: AuthService
  ) {}

  ngOnInit(): void {
    if (this.auth.isLoggedIn() && this.auth.getCurrentUser()) {
      this.auth.redirectByRole();
    }
  }

  goToLogin(): void {
    if (this.auth.isLoggedIn() && this.auth.getCurrentUser()) {
      this.auth.redirectByRole();
      return;
    }
    if (this.auth.getToken()) {
      this.auth.clearSession();
    }
    this.router.navigateByUrl('/login');
  }
}
