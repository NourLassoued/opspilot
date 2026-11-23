package com.opspilot.backend.incident;

/**
 * Cycle de vie d'un incident.
 *
 * INVESTIGATING → (DIAGNOSED | AWAITING_APPROVAL | FAILED)
 * AWAITING_APPROVAL → (EXECUTING → RESOLVED | FAILED) ou REJECTED
 */
public enum IncidentStatus {
    /** L'agent enquête. */
    INVESTIGATING,
    /** Diagnostic posé, aucune réparation automatique possible (action manual ou none). */
    DIAGNOSED,
    /** Réparation proposée : en attente de la décision d'un humain. */
    AWAITING_APPROVAL,
    /** Réparation approuvée, en cours d'exécution. */
    EXECUTING,
    /** Réparation exécutée avec succès. */
    RESOLVED,
    /** Réparation refusée par un humain. */
    REJECTED,
    /** L'agent ou la réparation a échoué. */
    FAILED
}
