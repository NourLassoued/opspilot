# Sprint 4 — Scénarios backend (résultats du 2026-11-23)

## Scénario C — De l'alerte à la réparation approuvée

Panne : commit ab94a79 (image backend 9.9.9 inexistante) → pod en ImagePullBackOff.

| Étape | Attendu | Obtenu |
|---|---|---|
| Incident créé | 202 + id | ✅ 202, incident 5 |
| Diagnostic | AWAITING_APPROVAL, bon commit | ✅ category image, git_revert de ab94a79, confiance 0.9 |
| Enquête | < 2 min | ✅ 6 outils, 74,7 s |
| Viewer approuve | 403 | ✅ 403 |
| Admin approuve | RESOLVED, ArgoCD redéploie | ✅ RESOLVED, revert 2e9105b poussé, backend 1/1 Running |

## Scénario D — Refus humain (faux positif réel)

Système sain + alerte de test : l'IA a proposé de revert 7117d0b, commit DÉJÀ annulé (860ad2c).

| Étape | Attendu | Obtenu |
|---|---|---|
| Refus admin | REJECTED | ✅ REJECTED (incident 2) |
| Git inchangé | aucun nouveau commit | ✅ 860ad2c inchangé |

## Système sain (après corrections)

| Incident | Résultat |
|---|---|
| 1 | FAILED : erreur 400 Groq (root_cause manquant) → backend a bien géré l'échec |
| 3 | Diagnostic de secours `unknown`, aucune action (outil « json » inexistant) |
| 4 | ✅ DIAGNOSED, category none, aucune action (après passage en json_schema) |
