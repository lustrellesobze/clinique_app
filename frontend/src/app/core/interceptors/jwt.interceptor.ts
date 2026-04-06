import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError, catchError, switchMap } from 'rxjs';
import { AuthService } from '../auth/auth.service';

@Injectable()
export class JwtInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(
    req: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    const token = this.authService.getToken();
    const skipAuthHeader =
      req.url.includes('/auth/login') || req.url.includes('/auth/refresh');

    if (token && !skipAuthHeader) {
      req = req.clone({
        setHeaders: { Authorization: `Bearer ${token}` },
      });
    }

    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401 && req.headers.has('X-Skip-Auth-Refresh')) {
          this.authService.logout();
          return throwError(() => error);
        }

        if (
          error.status === 401 &&
          !req.url.includes('/auth/login') &&
          !req.url.includes('/auth/refresh')
        ) {
          const refreshTok = this.authService.getRefreshToken();
          if (!refreshTok) {
            this.authService.logout();
            return throwError(() => error);
          }
          return this.authService.refreshAccessToken().pipe(
            switchMap(() => {
              const newToken = this.authService.getToken();
              const retry = req.clone({
                setHeaders: {
                  ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
                  'X-Skip-Auth-Refresh': '1',
                },
              });
              return next.handle(retry);
            }),
            catchError(() => {
              this.authService.logout();
              return throwError(() => error);
            })
          );
        }

        return throwError(() => error);
      })
    );
  }
}
