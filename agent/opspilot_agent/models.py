"""Le format de réponse de l'agent (sortie structurée)."""
from typing import Literal

from pydantic import BaseModel, Field


class Remediation(BaseModel):
    """Action de réparation proposée. Elle n'est exécutée qu'après validation humaine."""

    action: Literal["git_revert", "argocd_sync", "manual", "none"] = Field(
        description="git_revert : annuler un commit fautif du dépôt GitOps ; "
        "argocd_sync : le cluster a été modifié à la main (dérive), on le remet comme dans Git ; "
        "manual : correction à faire par un humain ; none : rien à faire"
    )
    repo_url: str | None = Field(default=None, description="Dépôt GitOps concerné, tel que vu dans les outils")
    commit_sha: str | None = Field(default=None, description="SHA court du commit fautif, recopié d'un résultat d'outil (git_revert)")
    file_path: str | None = Field(default=None, description="Fichier du dépôt à corriger, ex. base/backend.yaml")
    argocd_app: str | None = Field(default=None, description="Nom de l'application ArgoCD (argocd_sync)")
    explanation: str = Field(description="Pourquoi cette action répare la panne, en français")


class Diagnosis(BaseModel):
    """Diagnostic d'un incident Kubernetes."""

    category: Literal["none", "image", "crash", "resources", "config", "network", "database", "deployment", "unknown"] = Field(
        description="Famille de panne : none (aucun problème trouvé), image (image introuvable), crash (l'application plante), "
        "resources (mémoire/CPU), config (variable ou secret erroné), network, database, deployment, unknown"
    )
    root_cause: str = Field(description="La cause probable en une ou deux phrases, en français")
    confidence: float = Field(ge=0, le=1, description="Niveau de confiance entre 0 et 1")
    evidence: list[str] = Field(
        description="Preuves recopiées MOT POUR MOT des résultats d'outils (raison, événement, ligne de log, diff Git)"
    )
    affected_resources: list[str] = Field(description="Ressources touchées, ex. pod/jobradar-backend-xxx, deployment/jobradar-backend")
    last_known_good: str | None = Field(
        default=None, description="Dernière version qui fonctionnait (image, révision ou commit), si l'historique la montre"
    )
    suggested_fix: str = Field(description="La correction proposée, en texte, en français, SANS bloc de commandes")
    fix_commands: list[str] = Field(
        default_factory=list,
        description="Une commande par élément (kubectl ou git), avec les VRAIS noms et SHA vus dans les outils",
    )
    remediation: Remediation | None = Field(default=None, description="Action automatique proposée (validée par un humain)")
