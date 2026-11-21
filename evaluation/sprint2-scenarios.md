# Sprint 2 — Mêmes pannes, agent avec outils

Objectif : comparer avec le Sprint 1. L'agent doit maintenant :
- utiliser les VRAIS noms (SPRING_DATASOURCE_URL) au lieu d'inventer (POSTGRES_HOST) ;
- retrouver la dernière version saine (0.1.1) au lieu de proposer `latest` ;
- proposer une correction GitOps (git revert dans jobradar-gitops).

Préparation (2 onglets du terminal) :

```bash
# Onglet 1 : Prometheus
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090
# Onglet 2 : pause d'ArgoCD pour garder la panne
kubectl -n argocd patch application jobradar --type merge -p '{"spec":{"syncPolicy":null}}'
```

## Panne 1 — Image introuvable
```bash
kubectl -n jobradar set image deploy/jobradar-backend backend=ghcr.io/nourlassoued/jobradar-backend:9.9.9
sleep 60
python -m opspilot_agent.cli -n jobradar -a "PodImagePullFailed"
```

## Panne 2 — Base injoignable
```bash
kubectl -n jobradar set image deploy/jobradar-backend backend=ghcr.io/nourlassoued/jobradar-backend:0.1.1
kubectl -n jobradar set env deploy/jobradar-backend SPRING_DATASOURCE_URL=jdbc:postgresql://postgres-inexistant:5432/jobradar
sleep 180
python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping"
```

## Réparer
```bash
kubectl -n argocd patch application jobradar --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}'
```

## Résultats (Sprint 1 → Sprint 2)

| Panne | Cause correcte | Vrais noms ? | Dernière version saine ? | Correction GitOps ? | Appels d'outils | Temps |
|---|---|---|---|---|---|---|
| Image introuvable (S1) | ✅ | — | ❌ (`latest`) | ❌ | 0 (fixe) | 3,1 s |
| Image introuvable (S2) | ✅ | ✅ | ✅ 0.1.1 (rév. 8) | ✅ (commit Git, SHA inconnu) | 3 | 8,1 s |
| Base injoignable (S1) | ✅ | ❌ (POSTGRES_HOST) | — | ❌ | 0 (fixe) | 2,7 s |
| Base injoignable (S2) | ✅ | ✅ SPRING_DATASOURCE_URL | ✅ 0.1.1 | ✅ (chemin du fichier générique) | 5 | 53,7 s (limite Groq) |
