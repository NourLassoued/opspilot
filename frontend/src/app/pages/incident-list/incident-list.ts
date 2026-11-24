import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth';
import { IncidentsApi } from '../../core/incidents';
import { Incident, IncidentStatus } from '../../core/models';
import { CATEGORIES, statusLabel, timeAgo } from '../../shared/labels';
import { StatusBadge } from '../../shared/status-badge';

type Filter = 'ALL' | 'OPEN' | IncidentStatus;

@Component({
  selector: 'app-incident-list',
  imports: [FormsModule, StatusBadge],
  templateUrl: './incident-list.html',
})
export class IncidentList {
  private readonly api = inject(IncidentsApi);
  private readonly router = inject(Router);
  protected readonly auth = inject(AuthService);

  protected readonly incidents = signal<Incident[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly live = this.api.live;
  protected readonly filter = signal<Filter>('ALL');
  protected readonly now = signal(Date.now());

  protected readonly stats = computed(() => {
    const list = this.incidents();
    const count = (...s: IncidentStatus[]) => list.filter((i) => s.includes(i.status)).length;
    return {
      total: list.length,
      waiting: count('AWAITING_APPROVAL'),
      running: count('INVESTIGATING', 'EXECUTING'),
      resolved: count('RESOLVED'),
      failed: count('FAILED'),
    };
  });

  protected readonly visible = computed(() => {
    const f = this.filter();
    const list = this.incidents();
    if (f === 'ALL') return list;
    if (f === 'OPEN') return list.filter((i) => ['INVESTIGATING', 'AWAITING_APPROVAL', 'EXECUTING'].includes(i.status));
    return list.filter((i) => i.status === f);
  });

  // Formulaire « nouvelle enquête » (admin)
  protected showForm = signal(false);
  protected namespace = 'jobradar';
  protected alert = 'Vérification manuelle';
  protected readonly sending = signal(false);

  protected readonly categories = CATEGORIES;
  protected readonly statusLabel = statusLabel;

  constructor() {
    const destroyRef = inject(DestroyRef);
    this.load();

    // Temps réel : « ready » = (re)connecté → on recharge la liste (on a pu rater des changements) ;
    // « incident » = un incident a changé → on le remplace ou on l'ajoute.
    this.api.events$.pipe(takeUntilDestroyed(destroyRef)).subscribe((event) => {
      if (event.type === 'ready') this.load(false);
      else this.upsert(event.incident);
    });
    // Rafraîchit les « il y a 3 min »
    const clock = setInterval(() => this.now.set(Date.now()), 30_000);
    destroyRef.onDestroy(() => clearInterval(clock));
  }

  load(showSpinner = true): void {
    if (showSpinner) this.loading.set(true);
    this.api.list().subscribe({
      next: (list) => {
        this.incidents.set(list);
        this.error.set(null);
        this.loading.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set(e.status === 0 ? 'Backend injoignable.' : `Erreur ${e.status} au chargement.`);
        this.loading.set(false);
      },
    });
  }

  private upsert(incident: Incident): void {
    this.incidents.update((list) => {
      const others = list.filter((i) => i.id !== incident.id);
      return [incident, ...others].sort((a, b) => b.id - a.id);
    });
  }

  open(incident: Incident): void {
    this.router.navigate(['/incidents', incident.id]);
  }

  ago(iso: string): string {
    return timeAgo(iso, this.now());
  }

  investigate(): void {
    this.sending.set(true);
    this.api.investigate(this.namespace.trim(), this.alert.trim()).subscribe({
      next: (incident) => {
        this.sending.set(false);
        this.showForm.set(false);
        this.upsert(incident);
      },
      error: (e: HttpErrorResponse) => {
        this.sending.set(false);
        this.error.set(e.status === 400 ? 'Namespace invalide (lettres minuscules, chiffres, tirets).' : `Erreur ${e.status}.`);
      },
    });
  }
}
