# OpsPilot — Backend (Spring Boot)

Le « chef d'orchestre » d'OpsPilot :

```
Prometheus → Alertmanager → [Backend] → Agent IA (FastAPI) → diagnostic
                                 │
                       PostgreSQL (incidents + étapes)
                                 │
                 Humain (ADMIN) : approuver / refuser → Agent /remediate
```

## Prérequis (Ubuntu / WSL)

```bash
sudo apt update && sudo apt install -y openjdk-21-jdk maven
java -version   # doit afficher 21
```

## Base de données (conteneur Docker)

```bash
docker run -d --name opspilot-db \
  -e POSTGRES_DB=opspilot -e POSTGRES_USER=opspilot -e POSTGRES_PASSWORD=opspilot \
  -p 5433:5432 postgres:16-alpine
```

Les tables sont créées automatiquement au démarrage par Flyway (`db/migration/V1__init.sql`).

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `AGENT_URL` | Adresse de l'API de l'agent | `http://localhost:8000` |
| `AGENT_API_TOKEN` | Jeton pour `/remediate` (le **même** que dans `agent/.env`) | vide |
| `ALERTMANAGER_TOKEN` | Jeton attendu sur le webhook | `change-me` |
| `ADMIN_USER` / `ADMIN_PASSWORD` | Compte qui peut approuver | `admin` / `admin` |
| `VIEWER_USER` / `VIEWER_PASSWORD` | Compte lecture seule | `viewer` / `viewer` |

Ne jamais committer de vrais mots de passe : les définir dans le terminal (`export ...`).

## Lancer

```bash
mvn test              # tests (base H2 en mémoire, agent simulé)
mvn spring-boot:run   # démarre sur http://localhost:8090
```

Documentation interactive : http://localhost:8090/swagger-ui.html

## API

| Méthode | Chemin | Accès |
|---|---|---|
| POST | `/api/alerts/alertmanager` | jeton Alertmanager |
| GET | `/api/incidents` , `/api/incidents/{id}` | VIEWER ou ADMIN |
| GET | `/api/incidents/stream` (temps réel, SSE) | VIEWER ou ADMIN |
| POST | `/api/incidents` (enquête manuelle) | ADMIN |
| POST | `/api/incidents/{id}/approve` , `/reject` | ADMIN |

Cycle de vie : `INVESTIGATING → DIAGNOSED` ou `AWAITING_APPROVAL → EXECUTING → RESOLVED / FAILED`,
ou `REJECTED`. Une réparation n'est **jamais** lancée sans approbation d'un ADMIN.
