# OpsPilot — Agent IA de diagnostic d'incidents Kubernetes

OpsPilot enquête automatiquement quand une application tombe en panne sur Kubernetes :
il lit l'état des pods, les événements et les logs, trouve la cause probable
et propose une correction. **Aucune action n'est exécutée sans validation humaine.**

## Structure

| Dossier | Contenu | Sprint |
|---|---|---|
| `agent/` | Agent IA (Python, LangGraph, Groq) | 1–4 |
| `mcp-servers/` | Outils MCP de l'agent (Kubernetes, Prometheus…) | 2 |
| `backend/` | Plateforme Spring Boot (incidents, validations) | 4 |
| `frontend/` | Dashboard Angular | 5 |
| `evaluation/` | Banc de test : 10 scénarios de panne | 6 |
| `deploy/` | Manifests Kubernetes / Helm d'OpsPilot | 7 |
| `docs/` | Journal, décisions d'architecture | — |

## Application surveillée

[JobRadar](https://github.com/NourLassoued/JobRadar), déployée en GitOps avec ArgoCD
depuis [jobradar-gitops](https://github.com/NourLassoued/jobradar-gitops).

## Démarrage rapide de l'agent

Voir [`agent/README.md`](agent/README.md).
