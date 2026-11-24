/** Les données renvoyées par le backend Spring Boot (/api/incidents). */

export type IncidentStatus =
  | 'INVESTIGATING'
  | 'DIAGNOSED'
  | 'AWAITING_APPROVAL'
  | 'EXECUTING'
  | 'RESOLVED'
  | 'REJECTED'
  | 'FAILED';

export interface Remediation {
  action: 'git_revert' | 'argocd_sync' | 'manual' | 'none';
  repo_url?: string | null;
  commit_sha?: string | null;
  file_path?: string | null;
  argocd_app?: string | null;
  explanation?: string;
}

export interface Diagnosis {
  category: string;
  root_cause: string;
  confidence: number;
  evidence: string[];
  affected_resources: string[];
  last_known_good?: string | null;
  suggested_fix: string;
  fix_commands: string[];
  remediation?: Remediation | null;
}

export interface AgentStep {
  order: number;
  node: string;
  tool: string | null;
  args: Record<string, unknown> | null;
  at: string;
}

export interface Incident {
  id: number;
  namespace: string;
  alerts: string[];
  severity?: string;
  summary?: string;
  status: IncidentStatus;
  category?: string;
  rootCause?: string;
  confidence?: number;
  remediationAction?: string;
  remediation?: Remediation;
  toolCalls?: number;
  durationSeconds?: number;
  actionResult?: string;
  errorMessage?: string;
  decidedBy?: string;
  decidedAt?: string;
  createdAt: string;
  updatedAt: string;
  /** Seulement dans le détail (GET /api/incidents/{id}) */
  diagnosis?: Diagnosis;
  steps?: AgentStep[];
}

export interface Session {
  token: string;
  username: string;
  roles: string[];
  expiresAt: string;
}
