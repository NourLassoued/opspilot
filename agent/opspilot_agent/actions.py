"""Exécution des réparations, APRÈS validation humaine uniquement.

Sécurité :
- l'IA ne peut PAS appeler ce module : ce n'est pas un outil MCP ; seul le graphe l'appelle après « oui » ;
- seules 2 actions existent (liste blanche) : git_revert et argocd_sync ;
- chaque paramètre est vérifié (format du SHA, dépôt attendu, commit existant).
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .models import Remediation

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} a échoué : {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def _repo_slug(url: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+/[^/.]+)", url or "")
    return match.group(1).lower() if match else ""


def git_revert(remediation: Remediation) -> str:
    """Annule un commit dans le clone local du dépôt GitOps, puis pousse. ArgoCD redéploie ensuite tout seul."""
    sha = (remediation.commit_sha or "").lower()
    if not SHA_RE.match(sha):
        raise ValueError(f"SHA invalide : {remediation.commit_sha!r}")
    repo = Path(os.path.expanduser(os.getenv("GITOPS_REPO_PATH", "~/projects/jobradar-gitops")))
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"Clone GitOps introuvable : {repo} (variable GITOPS_REPO_PATH)")
    expected, actual = _repo_slug(remediation.repo_url or ""), _repo_slug(_git(repo, "remote", "get-url", "origin"))
    if expected and expected != actual:
        raise ValueError(f"Le clone local ({actual}) n'est pas le dépôt visé ({expected})")

    _git(repo, "pull", "--ff-only")
    _git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    full_sha = _git(repo, "rev-parse", f"{sha}^{{commit}}")
    if _git(repo, "log", "--format=%h", f"--grep=This reverts commit {full_sha}"):
        # Garde-fou : ne jamais annuler deux fois le même commit (l'IA peut se tromper).
        raise ValueError(f"Le commit {sha} a déjà été annulé : rien à faire, réparation refusée.")
    try:
        _git(repo, "revert", "--no-edit", sha)
    except RuntimeError:
        subprocess.run(["git", "-C", str(repo), "revert", "--abort"], capture_output=True)
        raise
    new_commit = _git(repo, "log", "-1", "--format=%h %s")
    _git(repo, "push")
    return f"Commit {sha} annulé et poussé : {new_commit}. ArgoCD va redéployer."


def argocd_sync(remediation: Remediation, api=None) -> str:
    """Remet comme dans Git UNIQUEMENT les ressources modifiées à la main (dérive), en une seule synchro.

    Prudence :
    - prune=False : aucune ressource n'est jamais supprimée ;
    - seules les ressources OutOfSync sont synchronisées (pas toute l'application) ;
    - la synchro automatique n'est PAS réactivée : c'est une décision humaine séparée.
    """
    name = remediation.argocd_app or "jobradar"
    if not re.fullmatch(r"[a-z0-9-]{1,63}", name):
        raise ValueError(f"Nom d'application invalide : {name!r}")
    if api is None:
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        api = client.CustomObjectsApi()

    app = api.get_namespaced_custom_object("argoproj.io", "v1alpha1", "argocd", "applications", name)
    drifted = [
        {"group": r.get("group", ""), "kind": r["kind"], "name": r["name"], "namespace": r.get("namespace", "")}
        for r in app.get("status", {}).get("resources", [])
        if r.get("status") == "OutOfSync"
    ]
    if not drifted:
        return f"Aucune ressource désynchronisée dans « {name} » : rien à faire."
    if app.get("operation"):
        raise RuntimeError("Une synchronisation ArgoCD est déjà en cours : réessaie dans un instant.")

    revision = app.get("spec", {}).get("source", {}).get("targetRevision", "HEAD")
    api.patch_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "argocd", "applications", name,
        {"operation": {
            "initiatedBy": {"username": "opspilot"},
            "sync": {"revision": revision, "prune": False, "resources": drifted},
        }},
    )
    targets = ", ".join(f"{r['kind']}/{r['name']}" for r in drifted)
    return (f"Synchronisation unique lancée sur « {name} » pour : {targets} (aucune suppression). "
            "La synchro automatique reste désactivée : à réactiver par un humain si souhaité.")


ACTIONS = {"git_revert": git_revert, "argocd_sync": argocd_sync}


def execute(remediation: Remediation) -> str:
    if remediation.action not in ACTIONS:
        raise ValueError(f"Action non autorisée : {remediation.action}")
    return ACTIONS[remediation.action](remediation)
