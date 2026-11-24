# OpsPilot — Dashboard (Angular 22)

L'écran des incidents : connexion, liste en direct, détail du diagnostic, boutons **Approuver / Refuser**.

## Lancer (développement)

Prérequis : Node.js 22.22+ ou 24.15+. Le backend doit tourner sur le port 8090 (voir `backend/README.md`).

```bash
npm install
npm start          # http://localhost:4200
```

`proxy.conf.json` redirige `/api/...` vers `http://localhost:8090` : pas de problème de CORS.

## Tests

```bash
npm test -- --watch=false   # Vitest : parseur SSE, libellés, connexion + intercepteur JWT
```

## Organisation

| Fichier | Rôle |
|---|---|
| `core/auth.ts` | Connexion, jeton JWT gardé dans `sessionStorage`, rôles (admin / viewer) |
| `core/auth.interceptor.ts` | Ajoute `Authorization: Bearer …` ; déconnecte si 401 |
| `core/auth.guard.ts` | Bloque les pages sans connexion |
| `core/incidents.ts` | Appels API + flux temps réel (SSE lu avec `fetch`) |
| `core/sse.ts` | Découpe le flux SSE en événements |
| `pages/login` | Écran de connexion |
| `pages/incident-list` | Compteurs, filtres, tableau mis à jour en direct, nouvelle enquête (admin) |
| `pages/incident-detail` | Réparation proposée + décision, diagnostic, preuves, étapes de l'agent |

Pourquoi `fetch` et pas `EventSource` pour le temps réel ? `EventSource` ne peut pas envoyer
l'en-tête `Authorization` : il faudrait mettre le jeton dans l'URL, où il finirait dans les logs.
