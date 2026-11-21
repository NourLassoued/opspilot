# Journal de bord — OpsPilot

## Sprint 0 — Environnement et application surveillée (terminé le 20/11/2026)

- WSL2 + Ubuntu, Docker Desktop, cluster k3d à 3 nœuds (k3s v1.35).
- JobRadar rendu observable (Actuator + Micrometer Prometheus) et conteneurisé (Dockerfiles multi-stage, nginx).
- Images publiées sur GHCR ; dépôt `jobradar-gitops` déployé par ArgoCD.
- kube-prometheus-stack + 5 règles d'alerte personnalisées.
- Démo : image `9.9.9` inexistante → alerte `PodImagePullFailed` FIRING → `git revert`.

### Incidents rencontrés

| Problème | Cause | Solution |
|---|---|---|
| `npm ci` → `ECONNRESET` | Connexion instable | Retries npm + cache BuildKit dans le Dockerfile |
| ArgoCD : CRD `applicationsets` « too long » | Annotation trop grosse avec `kubectl apply` classique | `kubectl apply --server-side --force-conflicts` |
| Connexion Google → retour à la page de login | Le cookie de session OAuth2 (sub Google) passait avant le JWT ; invisible en local car front/back sur des origines différentes | JWT prioritaire dans `JwtAuthenticationFilter` + session invalidée après le succès OAuth2 (v0.1.1) |
| Pod bloqué en `ContainerCreating` | Téléchargement lent de l'image sur un nouveau nœud | `k3d image import` |

### À retenir pour OpsPilot

Une seule panne (image inexistante) a déclenché 5 alertes (PodImagePullFailed, PodNotReady,
KubePodNotReady, KubeContainerWaiting, TargetDown) → l'agent devra regrouper les alertes
et remonter à une cause unique (le commit fautif).

## Sprint 1 — MVP de l'agent (terminé le 21/11/2026)

- Graphe LangGraph fixe : collecter (client Kubernetes) → diagnostiquer (LLM, sortie structurée Pydantic).
- LLM : `openai/gpt-oss-120b` (open-weight) via Groq, gratuit. `llama-3.3-70b-versatile` retiré par Groq → modèle
  configurable dans `.env`, changé sans toucher au code.
- Résultats : 2/2 causes correctes (image introuvable 3,1 s ; base injoignable 2,7 s, preuve trouvée dans les logs
  d'avant le crash).
- Limites observées : noms inventés (POSTGRES_HOST), tag `latest` proposé, corrections non GitOps
  → l'agent ne voyait ni la config du Deployment ni l'historique des versions.

## Sprint 2 — Outils MCP et enquête autonome

- 2 serveurs MCP (k8s_inspector : 5 outils ; prom_inspector : 2 outils), lecture seule, Secrets masqués.
- Boucle d'enquête : l'IA choisit ses outils ; garde-fou de 12 appels ; erreurs d'outils non bloquantes.
- Consignes renforcées : ne jamais inventer de nom, correction GitOps, jamais `latest`.
- RBAC lecture seule pour l'agent (deploy/rbac).
- Résultats : voir evaluation/sprint2-scenarios.md
