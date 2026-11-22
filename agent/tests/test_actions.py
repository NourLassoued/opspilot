"""Teste git_revert sur de vrais dépôts Git temporaires (aucun accès réseau)."""
import subprocess

import pytest

from opspilot_agent import actions
from opspilot_agent.models import Remediation


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def gitops_clone(tmp_path, monkeypatch):
    remote, clone = tmp_path / "remote.git", tmp_path / "clone"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(clone)], check=True, capture_output=True)
    git(clone, "config", "user.email", "t@t"); git(clone, "config", "user.name", "t")
    (clone / "backend.yaml").write_text("image: jobradar-backend:0.1.1\n")
    git(clone, "add", "-A"); git(clone, "commit", "-m", "deploy 0.1.1"); git(clone, "push", "-u", "origin", "main")
    (clone / "backend.yaml").write_text("image: jobradar-backend:9.9.9\n")
    git(clone, "commit", "-am", "deploy 9.9.9"); git(clone, "push")
    monkeypatch.setenv("GITOPS_REPO_PATH", str(clone))
    return clone, remote, git(clone, "rev-parse", "--short", "HEAD")


def test_git_revert_restores_previous_version(gitops_clone):
    clone, remote, bad_sha = gitops_clone
    message = actions.execute(Remediation(action="git_revert", commit_sha=bad_sha, explanation="test"))
    assert bad_sha in message
    assert (clone / "backend.yaml").read_text() == "image: jobradar-backend:0.1.1\n"
    assert git(remote, "log", "-1", "--format=%s").startswith('Revert "deploy 9.9.9"')  # bien poussé


def test_invalid_sha_is_rejected(gitops_clone):
    with pytest.raises(ValueError):
        actions.execute(Remediation(action="git_revert", commit_sha="HEAD; rm -rf /", explanation="x"))


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError):
        actions.execute(Remediation(action="manual", explanation="x"))

class FakeArgo:
    def __init__(self, resources, operation=None):
        self.app = {"spec": {"source": {"targetRevision": "main"}, "syncPolicy": None},
                    "status": {"resources": resources}, "operation": operation}
        self.patches = []

    def get_namespaced_custom_object(self, *args):
        return self.app

    def patch_namespaced_custom_object(self, *args):
        self.patches.append(args[-1])


def test_argocd_sync_only_drifted_resources_and_never_prunes():
    argo = FakeArgo([
        {"group": "apps", "kind": "Deployment", "name": "jobradar-backend", "namespace": "jobradar", "status": "OutOfSync"},
        {"group": "", "kind": "Service", "name": "postgres", "namespace": "jobradar", "status": "Synced"},
    ])
    message = actions.argocd_sync(Remediation(action="argocd_sync", argocd_app="jobradar", explanation="x"), api=argo)
    sync = argo.patches[0]["operation"]["sync"]
    assert sync["prune"] is False                                         # jamais de suppression
    assert [r["name"] for r in sync["resources"]] == ["jobradar-backend"]  # seulement la ressource modifiée
    assert "syncPolicy" not in argo.patches[0].get("spec", {})             # synchro auto NON réactivée
    assert "aucune suppression" in message


def test_argocd_sync_does_nothing_without_drift():
    argo = FakeArgo([{"kind": "Deployment", "name": "jobradar-backend", "status": "Synced"}])
    actions.argocd_sync(Remediation(action="argocd_sync", argocd_app="jobradar", explanation="x"), api=argo)
    assert argo.patches == []
