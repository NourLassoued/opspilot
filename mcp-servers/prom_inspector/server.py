"""Serveur MCP « prom-inspector » : lecture des alertes et métriques Prometheus pour l'agent OpsPilot.

Prometheus doit être joignable à PROMETHEUS_URL (par défaut http://localhost:9090).
Depuis WSL : kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
MAX_CHARS = 3000
mcp = FastMCP("prom-inspector", log_level="WARNING")


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{PROMETHEUS_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def _cut(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n…(tronqué)…"


@mcp.tool()
def get_firing_alerts(namespace: str = "") -> str:
    """Alertes Prometheus actives (firing ou pending), filtrées par namespace si fourni.
    Plusieurs alertes peuvent venir d'UNE SEULE cause : regroupe-les."""
    try:
        alerts = _get("/api/v1/alerts")["data"]["alerts"]
    except Exception as exc:  # Prometheus injoignable : on le dit, sans planter l'agent
        return f"Prometheus injoignable à {PROMETHEUS_URL} ({exc}). Lance le port-forward."
    lines = []
    for a in alerts:
        labels = a.get("labels", {})
        if labels.get("alertname") in ("Watchdog", "InfoInhibitor"):
            continue
        if namespace and labels.get("namespace") != namespace:
            continue
        target = labels.get("pod") or labels.get("deployment") or labels.get("job", "")
        summary = a.get("annotations", {}).get("summary") or a.get("annotations", {}).get("description", "")
        lines.append(f"- [{a.get('state')}] {labels.get('alertname')} sur {target} : {summary}")
    return _cut("\n".join(lines) or "Aucune alerte active.")


@mcp.tool()
def query_prometheus(promql: str) -> str:
    """Exécute une requête PromQL instantanée. Exemples utiles :
    - mémoire d'un conteneur : container_memory_working_set_bytes{namespace="jobradar",container="backend"}
    - redémarrages : kube_pod_container_status_restarts_total{namespace="jobradar"}
    - taux d'erreurs 5xx : sum(rate(http_server_requests_seconds_count{namespace="jobradar",status=~"5.."}[5m]))"""
    try:
        data = _get("/api/v1/query", {"query": promql})
    except Exception as exc:
        return f"Requête impossible ({exc})."
    if data.get("status") != "success":
        return f"Erreur PromQL : {data.get('error')}"
    results = data["data"]["result"]
    if not results:
        return "Aucun résultat."
    lines = []
    for r in results[:20]:
        labels = {k: v for k, v in r["metric"].items() if k in ("pod", "container", "namespace", "status", "uri", "reason")}
        lines.append(f"- {labels} = {r['value'][1]}")
    return _cut("\n".join(lines))


if __name__ == "__main__":
    mcp.run()
