# Sprint 1 — Les 2 pannes de test (S1-06)

Pour ces tests rapides, on met d'abord l'application ArgoCD en pause,
sinon ArgoCD annule les changements manuels (selfHeal) :

```bash
kubectl -n argocd patch application jobradar --type merge -p '{"spec":{"syncPolicy":null}}'
```

## Panne 1 — Image introuvable

```bash
kubectl -n jobradar set image deploy/jobradar-backend backend=ghcr.io/nourlassoued/jobradar-backend:9.9.9
# attendre 30 s, puis :
python -m opspilot_agent.cli -n jobradar -a "PodImagePullFailed"
```
Attendu : `category = image`, cause = l'image 9.9.9 n'existe pas, correction = revenir à 0.1.1.

## Panne 2 — Base de données injoignable (mauvaise configuration)

```bash
kubectl -n jobradar set image deploy/jobradar-backend backend=ghcr.io/nourlassoued/jobradar-backend:0.1.1
kubectl -n jobradar set env deploy/jobradar-backend SPRING_DATASOURCE_URL=jdbc:postgresql://postgres-inexistant:5432/jobradar
# attendre 2 à 3 minutes (le temps que Spring Boot échoue et redémarre), puis :
python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping"
```
Attendu : `category = config` ou `database`, preuve = une ligne de log du type `UnknownHostException: postgres-inexistant`.

## Tout réparer

```bash
kubectl -n argocd patch application jobradar --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}'
```
ArgoCD remet alors tout comme décrit dans Git.

## Résultats

| Panne | Catégorie trouvée | Cause correcte ? | Temps | Notes |
|---|---|---|---|---|
| Image introuvable | image | ✅ oui (confiance 0,96) | 3,1 s | Preuves exactes ; correction non GitOps (propose `latest` et `kubectl set image`) → à améliorer aux Sprints 2-3 |
| Base injoignable | | | | |
