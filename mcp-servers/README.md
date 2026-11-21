# Serveurs MCP d'OpsPilot

Les « outils » que l'agent peut appeler. Chaque serveur est un petit programme Python
que l'agent lance lui-même (transport stdio). Tous sont en **lecture seule**.

## k8s_inspector

| Outil | Rôle |
|---|---|
| `list_pods(namespace)` | État des pods (prêts, redémarrages, raison d'erreur) |
| `get_pod_events(namespace, pod)` | Événements Kubernetes d'un pod |
| `get_pod_logs(namespace, pod, previous)` | Logs ; `previous=True` = avant le dernier crash |
| `get_deployment_config(namespace, deployment)` | Image, variables (Secrets masqués), ressources, sondes |
| `get_rollout_history(namespace, deployment)` | Versions successives → dernière version saine |

## prom_inspector

| Outil | Rôle |
|---|---|
| `get_firing_alerts(namespace)` | Alertes Prometheus actives (hors Watchdog) |
| `query_prometheus(promql)` | Requête PromQL instantanée |

Prometheus doit être joignable (port-forward) :
`kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090`

## Sécurité

- Aucune écriture dans le cluster.
- Les Secrets ne sont jamais lus : seul leur nom apparaît.
- Chaque réponse est tronquée (≈ 3 500 caractères) pour limiter les tokens envoyés au LLM.
