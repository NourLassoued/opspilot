"""Serveur MCP « gitops-inspector » : ArgoCD + historique Git, en LECTURE SEULE.

- ArgoCD est lu via l'API Kubernetes (ressource Application) : pas besoin de mot de passe ArgoCD.
- Git est lu via l'API GitHub (dépôt public). Si GITHUB_TOKEN est défini, il est utilisé
  (limite plus haute) ; sinon, accès anonyme (60 requêtes / heure).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from kubernetes import client, config
from mcp.server.fastmcp import FastMCP

MAX_CHARS = 3500
mcp = FastMCP("gitops-inspector", log_level="WARNING")
_custom: client.CustomObjectsApi | None = None


def _k8s() -> client.CustomObjectsApi:
    global _custom
    if _custom is None:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        _custom = client.CustomObjectsApi()
    return _custom


def _cut(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n…(tronqué)…"


def _github(path: str) -> dict | list:
    req = urllib.request.Request(f"https://api.github.com{path}", headers={"Accept": "application/vnd.github+json"})
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _owner_repo(repo_url: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", repo_url)
    if not match:
        raise ValueError(f"Dépôt GitHub non reconnu : {repo_url}")
    return f"{match.group(1)}/{match.group(2)}"


@mcp.tool()
def get_argocd_application(name: str, argocd_namespace: str = "argocd") -> str:
    """État d'une application ArgoCD : dépôt Git et dossier suivis, synchronisation (Synced/OutOfSync),
    santé, synchro automatique active ou non, ressources désynchronisées, historique des déploiements (SHA Git).
    OutOfSync + synchro automatique désactivée = le cluster a été modifié à la main (dérive)."""
    app = _k8s().get_namespaced_custom_object("argoproj.io", "v1alpha1", argocd_namespace, "applications", name)
    spec, status = app.get("spec", {}), app.get("status", {})
    source = spec.get("source", {})
    auto = (spec.get("syncPolicy") or {}).get("automated")
    lines = [
        f"Application {name}",
        f"Dépôt : {source.get('repoURL')} | dossier : {source.get('path')} | branche : {source.get('targetRevision')}",
        f"Synchro : {status.get('sync', {}).get('status')} (révision Git {str(status.get('sync', {}).get('revision', ''))[:7]})",
        f"Santé : {status.get('health', {}).get('status')}",
        f"Synchro automatique : {'ACTIVE' if auto else 'DÉSACTIVÉE'}"
        + (f" (selfHeal={auto.get('selfHeal', False)})" if auto else ""),
    ]
    drift = [r for r in status.get("resources", []) if r.get("status") == "OutOfSync"]
    if drift:
        lines.append("Ressources différentes de Git : " + ", ".join(f"{r.get('kind')}/{r.get('name')}" for r in drift))
    history = status.get("history", [])[-5:]
    if history:
        lines.append("Historique des déploiements (du plus récent) :")
        for h in reversed(history):
            lines.append(f"- {str(h.get('revision', ''))[:7]} déployé le {h.get('deployedAt')}")
    return _cut("\n".join(lines))


@mcp.tool()
def list_git_commits(repo_url: str, path: str = "", limit: int = 8) -> str:
    """Derniers commits d'un dépôt GitHub (filtrés sur un dossier si path est fourni) :
    SHA court, date, auteur, message. Sert à trouver le commit qui a introduit la panne."""
    query = f"?per_page={min(limit, 20)}" + (f"&path={path}" if path else "")
    try:
        commits = _github(f"/repos/{_owner_repo(repo_url)}/commits{query}")
    except Exception as exc:
        return f"GitHub injoignable ou dépôt introuvable ({exc})."
    lines = [
        f"- {c['sha'][:7]} | {c['commit']['author']['date']} | {c['commit']['author']['name']} | "
        f"{c['commit']['message'].splitlines()[0]}"
        for c in commits
    ]
    return _cut("\n".join(lines) or "Aucun commit.")


@mcp.tool()
def get_git_commit_diff(repo_url: str, sha: str) -> str:
    """Modifications exactes d'un commit (fichiers et lignes changés). Sert à prouver qu'un commit est fautif."""
    try:
        data = _github(f"/repos/{_owner_repo(repo_url)}/commits/{sha}")
    except Exception as exc:
        return f"Commit introuvable ({exc})."
    lines = [f"Commit {data['sha'][:7]} : {data['commit']['message'].splitlines()[0]}"]
    for f in data.get("files", [])[:10]:
        lines.append(f"--- {f['filename']} (+{f['additions']} -{f['deletions']})")
        lines.append(f.get("patch", "(pas de diff texte)"))
    return _cut("\n".join(lines))


if __name__ == "__main__":
    mcp.run()
