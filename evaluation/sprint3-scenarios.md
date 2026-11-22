# Sprint 3 — Trouver la vraie origine de la panne et réparer (avec validation humaine)

Deux origines possibles d'une panne en GitOps, deux réparations différentes :

| Origine | Ce que voit l'agent dans ArgoCD | Réparation proposée |
|---|---|---|
| **Mauvais commit Git** | Synced (le cluster = Git, mais Git est faux) | `git_revert` du commit fautif |
| **Modification manuelle** (dérive) | OutOfSync + synchro auto désactivée | `argocd_sync` (remettre le cluster comme Git) |

Préparation (onglet 1) :
```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090
```
Onglet 2 :
```bash
cd ~/projects/opspilot/agent && source .venv/bin/activate
export GITHUB_TOKEN=$(gh auth token)
```

## Scénario A — Mauvais commit Git (le vrai cas GitOps)
```bash
cd ~/projects/jobradar-gitops
sed -i 's#jobradar-backend:0.1.1#jobradar-backend:9.9.9#' base/backend.yaml
git commit -am "deploy: backend 9.9.9" && git push
kubectl -n argocd annotate application jobradar argocd.argoproj.io/refresh=hard --overwrite
sleep 90
cd ~/projects/opspilot/agent
python -m opspilot_agent.cli -n jobradar -a "PodImagePullFailed" --allow-actions
```
Attendu : l'agent trouve le commit `deploy: backend 9.9.9` (vrai SHA), le prouve par le diff,
propose `git_revert`, attend « oui », puis annule le commit. ArgoCD redéploie 0.1.1.

## Scénario B — Modification manuelle (dérive)
```bash
kubectl -n argocd patch application jobradar --type merge -p '{"spec":{"syncPolicy":null}}'
kubectl -n jobradar set env deploy/jobradar-backend SPRING_DATASOURCE_URL=jdbc:postgresql://postgres-inexistant:5432/jobradar
sleep 180
python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping" --allow-actions
```
Attendu : OutOfSync + synchro désactivée → `argocd_sync` ; après « oui », ArgoCD remet la bonne URL.

## Résultats

| Scénario | Cause | Origine trouvée | SHA/réparation correcte | Réparation exécutée | Outils | Temps |
|---|---|---|---|---|---|---|
| A — mauvais commit | | | | | | |
| B — dérive manuelle | | | | | | |
