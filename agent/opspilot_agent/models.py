"""Le format de réponse de l'agent (sortie structurée)."""
from typing import Literal

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    """Diagnostic d'un incident Kubernetes."""

    category: Literal["image", "crash", "resources", "config", "network", "database", "deployment", "unknown"] = Field(
        description="Famille de panne : image (image introuvable), crash (l'application plante), "
        "resources (mémoire/CPU), config (variable ou secret manquant), network, database, deployment, unknown"
    )
    root_cause: str = Field(description="La cause probable en une ou deux phrases, en français")
    confidence: float = Field(ge=0, le=1, description="Niveau de confiance entre 0 et 1")
    evidence: list[str] = Field(
        description="Les preuves exactes tirées des données (raison du pod, ligne de log, événement)"
    )
    affected_resources: list[str] = Field(description="Les ressources touchées, ex. pod/jobradar-backend-xxx")
    suggested_fix: str = Field(description="La correction proposée, concrète, en français")
    fix_commands: list[str] = Field(
        default_factory=list,
        description="Commandes kubectl ou git suggérées (elles ne sont JAMAIS exécutées automatiquement)",
    )
