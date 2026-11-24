import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth';

/** Ajoute "Authorization: Bearer <jeton>" à chaque appel /api ; déconnecte si le backend répond 401. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const isLogin = req.url.endsWith('/api/auth/login');
  const token = isLogin ? null : auth.token();
  const request = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(request).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !isLogin) {
        auth.logout(); // jeton expiré ou invalide
      }
      return throwError(() => error);
    }),
  );
};
