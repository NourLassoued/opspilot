import { IncidentStatus } from '../core/models';

/** Textes en français et couleur de chaque statut. */
export const STATUS: Record<IncidentStatus, { label: string; tone: string }> = {
  INVESTIGATING: { label: 'Enquête en cours', tone: 'info' },
  DIAGNOSED: { label: 'Diagnostiqué', tone: 'neutral' },
  AWAITING_APPROVAL: { label: 'Attend votre décision', tone: 'warn' },
  EXECUTING: { label: 'Réparation en cours', tone: 'info' },
  RESOLVED: { label: 'Résolu', tone: 'ok' },
  REJECTED: { label: 'Refusé', tone: 'neutral' },
  FAILED: { label: 'Échec', tone: 'bad' },
};

export const ACTIONS: Record<string, string> = {
  git_revert: 'Annuler un commit Git',
  argocd_sync: 'Resynchroniser ArgoCD',
  manual: 'Correction manuelle',
  none: 'Aucune action',
};

export const CATEGORIES: Record<string, string> = {
  none: 'Aucun problème',
  image: 'Image',
  crash: 'Plantage',
  resources: 'Ressources',
  config: 'Configuration',
  network: 'Réseau',
  database: 'Base de données',
  deployment: 'Déploiement',
  unknown: 'Inconnue',
};

export function statusLabel(status: IncidentStatus): string {
  return STATUS[status]?.label ?? status;
}

/** "il y a 3 min" */
export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "à l'instant";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return `il y a ${Math.round(hours / 24)} j`;
}
