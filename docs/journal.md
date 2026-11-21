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

## Sprint 1 — MVP de l'agent

- …
