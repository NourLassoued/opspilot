import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Session } from './models';

const STORAGE_KEY = 'opspilot.session';

/**
 * Connexion : envoie nom + mot de passe au backend, garde le jeton JWT reçu.
 * Le jeton est gardé dans sessionStorage : il disparaît quand on ferme l'onglet.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly session = signal<Session | null>(AuthService.restore());

  readonly user = computed(() => this.session()?.username ?? null);
  readonly isLoggedIn = computed(() => this.session() !== null);
  readonly isAdmin = computed(() => this.session()?.roles.includes('ADMIN') ?? false);

  token(): string | null {
    const s = this.session();
    if (s && AuthService.isExpired(s)) {
      this.logout();
      return null;
    }
    return s?.token ?? null;
  }

  async login(username: string, password: string): Promise<void> {
    const session = await firstValueFrom(this.http.post<Session>('/api/auth/login', { username, password }));
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    this.session.set(session);
  }

  logout(): void {
    sessionStorage.removeItem(STORAGE_KEY);
    this.session.set(null);
    this.router.navigate(['/login']);
  }

  private static restore(): Session | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      const session = raw ? (JSON.parse(raw) as Session) : null;
      return session && !AuthService.isExpired(session) ? session : null;
    } catch {
      return null;
    }
  }

  private static isExpired(session: Session): boolean {
    return new Date(session.expiresAt).getTime() <= Date.now();
  }
}
