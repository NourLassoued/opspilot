import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth';

/** Bloque les pages si l'utilisateur n'est pas connecté. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.token() ? true : inject(Router).createUrlTree(['/login']);
};
