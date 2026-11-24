import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, retry, share, tap, timer } from 'rxjs';
import { AuthService } from './auth';
import { Incident } from './models';

export type StreamEvent = { type: 'ready' } | { type: 'incident'; incident: Incident };
import { parseSse } from './sse';

/** Appels au backend pour les incidents. */
@Injectable({ providedIn: 'root' })
export class IncidentsApi {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  /** true quand le flux temps réel est connecté */
  readonly live = signal(false);

  /**
   * UN SEUL flux partagé par toutes les pages de l'onglet.
   * (Le navigateur n'autorise que 6 connexions ouvertes vers le même serveur : un flux par page
   * finissait par tout bloquer.) Reconnexion automatique toutes les 5 s.
   */
  readonly events$: Observable<StreamEvent> = this.stream().pipe(
    tap({ next: () => this.live.set(true), error: () => this.live.set(false) }),
    retry({ delay: () => timer(5000) }),
    share(),
  );

  list(): Observable<Incident[]> {
    return this.http.get<Incident[]>('/api/incidents');
  }

  get(id: number): Observable<Incident> {
    return this.http.get<Incident>(`/api/incidents/${id}`);
  }

  approve(id: number): Observable<Incident> {
    return this.http.post<Incident>(`/api/incidents/${id}/approve`, {});
  }

  reject(id: number): Observable<Incident> {
    return this.http.post<Incident>(`/api/incidents/${id}/reject`, {});
  }

  investigate(namespace: string, alert: string): Observable<Incident> {
    return this.http.post<Incident>('/api/incidents', { namespace, alert });
  }

  /**
   * Flux temps réel : chaque changement d'incident arrive ici.
   * On utilise fetch (et pas EventSource) car EventSource ne peut pas envoyer l'en-tête Authorization.
   */
  stream(): Observable<StreamEvent> {
    return new Observable<StreamEvent>((subscriber) => {
      const controller = new AbortController();
      const token = this.auth.token();
      // Si le serveur n'a pas dit « ready » en 10 s, la connexion est bloquée : on abandonne et on réessaie.
      const readyTimeout = setTimeout(() => {
        controller.abort();
        subscriber.error(new Error('Flux temps réel : pas de réponse'));
      }, 10_000);
      fetch('/api/incidents/stream', {
        headers: { Accept: 'text/event-stream', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok || !response.body) throw new Error(`Flux temps réel indisponible (${response.status})`);
          const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
          let buffer = '';
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            const parsed = parseSse(buffer + value);
            buffer = parsed.rest;
            for (const e of parsed.events) {
              if (e.event === 'ready') {
                clearTimeout(readyTimeout);
                subscriber.next({ type: 'ready' });
              }
              if (e.event === 'incident') subscriber.next({ type: 'incident', incident: JSON.parse(e.data) as Incident });
            }
          }
          subscriber.error(new Error('Flux temps réel interrompu'));
        })
        .catch((error) => {
          if (!controller.signal.aborted) subscriber.error(error);
        });
      return () => {
        clearTimeout(readyTimeout);
        controller.abort();
      };
    });
  }
}
