# OpsPilot Agent — Sprint 2

L'agent **choisit lui-même** ses outils (serveurs MCP) pour enquêter, puis rédige un diagnostic structuré.

```
START → enquêter ──(demande un outil)──► outils (MCP) ──► enquêter ──► …
             └──(cause trouvée, ou 12 appels max)──► diagnostiquer → END
```

## Installation (Ubuntu / WSL)

```bash
cd ~/projects/opspilot/agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # puis mets ta clé Groq
```

## Utilisation

```bash
pytest -q                                              # tests sans cluster ni clé
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090 &   # pour les outils Prometheus
python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping"
uvicorn opspilot_agent.api:app --reload --port 8000    # API : POST /investigate
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `opspilot_agent/graph.py` | Graphe LangGraph : boucle d'enquête + diagnostic, garde-fous, consignes de l'IA |
| `opspilot_agent/tools.py` | Lance les serveurs MCP et charge leurs outils |
| `opspilot_agent/models.py` | Format du diagnostic (cause, preuves, dernière version saine, commandes) |
| `opspilot_agent/cli.py` | Enquête depuis le terminal, raisonnement affiché en direct |
| `opspilot_agent/api.py` | Endpoint `POST /investigate` (avec la liste des étapes) |
| `tests/test_agent.py` | Faux outils + faux LLM : boucle, garde-fou, outil inconnu |

## Garde-fous

- 12 appels d'outils maximum par enquête (`MAX_TOOL_CALLS`).
- Une erreur d'outil n'arrête pas l'enquête : l'IA reçoit le message d'erreur.
- Outils en lecture seule, Secrets jamais lus, réponses tronquées.
