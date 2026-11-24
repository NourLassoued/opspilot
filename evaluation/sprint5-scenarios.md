# Sprint 5 — Scénarios du dashboard (résultats du 2026-11-23/24)

| # | Test | Attendu | Obtenu |
|---|---|---|---|
| E1 | Mauvais mot de passe | « Nom ou mot de passe incorrect » | ✅ |
| E2 | Connexion viewer | Lecture seule, pas de « Nouvelle enquête », pas d'Approuver/Refuser | ✅ |
| E3 | Connexion admin | Badge « admin », bouton « Nouvelle enquête » | ✅ |
| E4 | Temps réel | `simulate-alert.sh` → incident #6 apparaît puis passe à Diagnostiqué | ✅ |
| E5 | Détail incident #5 | Commit ab94a79, confiance 90 %, preuves, 6 outils, décidé par admin | ✅ |
| E6 | Navigation liste ↔ détail | Le point reste vert | ✅ après correction (1 flux partagé) |

## Bugs trouvés pendant les tests
1. Webhook Alertmanager en 401 : son jeton « Bearer » était lu comme un JWT → ignoré pour cette URL.
2. Écran bloqué après plusieurs allers-retours : un flux SSE par page, limite de 6 connexions du navigateur
   → un seul flux partagé par onglet, nouvel essai après 10 s sans réponse.
