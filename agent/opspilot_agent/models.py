"""Le format de réponse de l'agent (sortie structurée)."""
from typing import Literal

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    """Diagnostic d'un incident Kubernetes."""

    category: Literal["none", "image", "crash", "resources", "config", "network", "database", "deployment", "unknown"] = Field(
        description="Famille de panne : none (aucun problème trouvé), image (image introuvable), crash (l'application plante), "
        "resources (mémoire/CPU), config (variable ou secret erroné), network, database, deployment, unknown"
    )
    root_cause: str = Field(description="La cause probable en une ou deux phrases, en français")
    confidence: float = Field(ge=0, le=1, description="Niveau de confiance entre 0 et 1")
    evidence: list[str] = Field(
        description="Preuves recopiées MOT POUR MOT des résultats d'outils (raison, événement, ligne de log, valeur de config)"
    )
    affected_resources: list[str] = Field(description="Ressources touchées, ex. pod/jobradar-backend-xxx, deployment/jobradar-backend")
    last_known_good: str | None = Field(
        default=None, description="Dernière version qui fonctionnait (image ou révision), si l'historique la montre"
    )
    suggested_fix: str = Field(description="La correction proposée, en texte, en français, SANS bloc de commandes")
    fix_commands: list[str] = Field(
        default_factory=list,
        description="Une commande par élément (kubectl ou git). Suggestions seulement : jamais exécutées automatiquement",
    )
