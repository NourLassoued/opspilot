# OpsPilot Agent — Sprint 1 (MVP)

Graphe LangGraph à 2 étapes :

```
collect (Kubernetes, lecture seule)  →  diagnose (LLM Groq, réponse structurée)
```

## Installation (Ubuntu / WSL)

```bash
cd ~/projects/opspilot/agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # puis mets ta clé Groq dans .env
```

## Utilisation

```bash
# Tests (sans cluster ni clé API)
pytest -q

# Enquête sur le namespace jobradar
python -m opspilot_agent.cli --namespace jobradar

# Avec le texte de l'alerte et les données envoyées au LLM
python -m opspilot_agent.cli -n jobradar -a "PodImagePullFailed" --show-context

# API HTTP (docs sur http://localhost:8000/docs)
uvicorn opspilot_agent.api:app --reload --port 8000
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `opspilot_agent/k8s_collector.py` | Lit l'état des pods, événements et logs (lecture seule) |
| `opspilot_agent/models.py` | Format de la réponse : cause, confiance, preuves, correction |
| `opspilot_agent/graph.py` | Le graphe LangGraph : collecter → diagnostiquer |
| `opspilot_agent/cli.py` | Lancer une enquête depuis le terminal |
| `opspilot_agent/api.py` | Endpoint `POST /investigate` (pour le backend Spring Boot) |
| `tests/test_agent.py` | Tests avec un faux Kubernetes et un faux LLM |
