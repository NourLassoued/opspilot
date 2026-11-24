import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./pages/login/login').then((m) => m.Login) },
  {
    path: 'incidents',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/incident-list/incident-list').then((m) => m.IncidentList),
  },
  {
    path: 'incidents/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/incident-detail/incident-detail').then((m) => m.IncidentDetail),
  },
  { path: '', pathMatch: 'full', redirectTo: 'incidents' },
  { path: '**', redirectTo: 'incidents' },
];
