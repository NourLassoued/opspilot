import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, effect, inject, input, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from '../../core/auth';
import { IncidentsApi } from '../../core/incidents';
import { Incident } from '../../core/models';
import { ACTIONS, CATEGORIES } from '../../shared/labels';
import { StatusBadge } from '../../shared/status-badge';

@Component({
  selector: 'app-incident-detail',
  imports: [RouterLink, StatusBadge, DatePipe, DecimalPipe],
  templateUrl: './incident-detail.html',
})
export class IncidentDetail {
  /** Lu automatiquement depuis l'URL /incidents/:id */
  readonly id = input.required<string>();

  private readonly api = inject(IncidentsApi);
  protected readonly auth = inject(AuthService);

  protected readonly incident = signal<Incident | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly deciding = signal(false);

  protected readonly actions = ACTIONS;
  protected readonly categories = CATEGORIES;

  protected readonly canDecide = computed(
    () => this.auth.isAdmin() && this.incident()?.status === 'AWAITING_APPROVAL',
  );
  protected readonly toolSteps = computed(() => (this.incident()?.steps ?? []).filter((s) => s.tool));

  constructor() {
    effect(() => this.load(Number(this.id())));

    // Temps réel : si CET incident change (ex. l'enquête se termine), on recharge le détail.
    this.api.events$
      .pipe(
        filter((e) => e.type === 'incident' && e.incident.id === Number(this.id())),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => this.load(Number(this.id())));
  }

  load(id: number): void {
    this.api.get(id).subscribe({
      next: (incident) => {
        this.incident.set(incident);
        this.error.set(null);
      },
      error: (e: HttpErrorResponse) => this.error.set(e.status === 404 ? `Incident ${id} introuvable.` : `Erreur ${e.status}.`),
    });
  }

  approve(): void {
    const r = this.incident()?.remediation;
    const what = r?.action === 'git_revert' ? `annuler le commit ${r.commit_sha}` : (ACTIONS[r?.action ?? ''] ?? 'réparer');
    // Dernière vérification humaine avant une action réelle sur Git / le cluster
    if (!confirm(`Confirmer la réparation : ${what} ?\n\nCette action modifie réellement le système.`)) return;
    this.decide('approve');
  }

  reject(): void {
    if (!confirm('Refuser cette réparation ? Rien ne sera modifié.')) return;
    this.decide('reject');
  }

  private decide(decision: 'approve' | 'reject'): void {
    const id = Number(this.id());
    this.deciding.set(true);
    const call = decision === 'approve' ? this.api.approve(id) : this.api.reject(id);
    call.subscribe({
      next: () => {
        this.deciding.set(false);
        this.load(id);
      },
      error: (e: HttpErrorResponse) => {
        this.deciding.set(false);
        this.error.set(
          e.status === 403 ? "Seul un administrateur peut décider." :
          e.status === 409 ? 'Cet incident a déjà été traité.' : `Erreur ${e.status}.`,
        );
        this.load(id);
      },
    });
  }

  args(value: Record<string, unknown> | null): string {
    return value ? Object.entries(value).map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`).join('  ') : '';
  }
}
