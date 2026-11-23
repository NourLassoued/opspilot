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
- Résultats : 2/2 causes ; vrais noms (SPRING_DATASOURCE_URL) ; version saine 0.1.1 retrouvée ; corrections GitOps.
  Reste : SHA du commit et chemin du fichier inconnus (pas d'accès Git) ; 53,7 s sur la panne 2 (limite Groq).

## Sprint 3 — Lien GitOps et réparation avec validation humaine

- Serveur MCP gitops_inspector : application ArgoCD (via l'API Kubernetes) + historique et diff Git (API GitHub).
- L'agent distingue un mauvais commit (Synced → git_revert du SHA prouvé par le diff)
  d'une modification manuelle (OutOfSync + synchro désactivée → argocd_sync).
- Validation humaine : pause du graphe LangGraph (interrupt + checkpointer) avant toute action.
- Réparations en liste blanche, hors de portée de l'IA ; testées sur de vrais dépôts Git temporaires.
- Revue de sécurité : `argocd_sync` réactivait la synchro auto avec `prune: true` (risque de suppression,
  ex. base de données si un manifest disparaît de Git). Corrigé : une seule synchro, uniquement des
  ressources OutOfSync, `prune: false`, synchro auto laissée à la décision humaine.
- Résultats : voir evaluation/sprint3-scenarios.md

## Sprint 4 — Backend Spring Boot (incidents)

- Webhook Alertmanager protégé par jeton ; alertes regroupées par namespace (pas de doublon d'incident).
- Incidents et étapes de l'agent enregistrés dans PostgreSQL (Flyway) ; suivi temps réel en SSE.
- Rôles : VIEWER lit, ADMIN approuve/refuse. L'agent n'agit qu'après `/approve`,
  via `/remediate` protégé par un second jeton (AGENT_API_TOKEN).
- Tests d'intégration (MockMvc, agent simulé) : jeton invalide, regroupement, 403 viewer,
  double approbation (409), refus, agent en panne (FAILED).
- Résultats : voir evaluation/sprint4-scenarios.md
- Incident réel au premier test : le modèle gratuit (Groq) oubliait le champ `root_cause` quand tout allait
  bien → erreur 400 → agent en 500 → incident FAILED (le backend a bien géré l'échec).
  Correction : champs du diagnostic tolérants, nouvel essai automatique, diagnostic de secours
  `unknown` sans aucune action. 3 tests ajoutés (18 au total).
- Faux positif au test suivant (système sain, alerte de test) : l'agent a proposé de revert 7117d0b,
  commit DÉJÀ annulé par 860ad2c. L'humain a refusé (rôle de la validation humaine).
  Corrections : règle « pas de panne → none » dans les consignes + garde-fou dans git_revert
  (refus si le commit a déjà été annulé). Test ajouté (19 au total).
- 3e test : le diagnostic de secours a fonctionné (category unknown, aucune action) car gpt-oss a
  appelé un outil « json » inexistant. Correction : sortie structurée en mode `json_schema`
  (le modèle renvoie le JSON directement), puis `function_calling` en secours (3 essais au total).
