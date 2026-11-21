"""Le graphe LangGraph de l'agent (Sprint 1) : collecter -> diagnostiquer.

Au Sprint 2, on ajoutera une boucle d'enquête où l'agent choisit lui-même ses outils (MCP).
"""
from __future__ import annotations

import os
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from .k8s_collector import collect_namespace_state, format_for_llm
from .models import Diagnosis

SYSTEM_PROMPT = """Tu es OpsPilot, un ingénieur SRE expert de Kubernetes.
On te donne l'état réel d'un namespace : pods, raisons d'erreur, événements et logs.

Règles :
- Base-toi UNIQUEMENT sur les données fournies. N'invente rien.
- Chaque élément de "evidence" doit être recopié des données (raison, événement ou ligne de log).
- Si les données ne suffisent pas, mets category="unknown" et une confiance faible.
- Propose une correction concrète. Les commandes sont des suggestions : un humain les validera.
- Réponds en français."""


class AgentState(TypedDict, total=False):
    namespace: str
    alert: str
    raw_state: dict[str, Any]
    context: str
    diagnosis: Diagnosis | None


def build_llm():
    from langchain_groq import ChatGroq

    return ChatGroq(model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"), temperature=0)


def build_graph(
    collector: Callable[[str], dict[str, Any]] = collect_namespace_state,
    llm: Any | None = None,
):
    """Construit le graphe. collector et llm sont injectables (utile pour les tests)."""

    def collect(state: AgentState) -> AgentState:
        raw = collector(state["namespace"])
        return {"raw_state": raw, "context": format_for_llm(raw)}

    def diagnose(state: AgentState) -> AgentState:
        if not state["raw_state"]["unhealthy_pods"]:
            return {"diagnosis": None}  # rien à diagnostiquer : pas d'appel au LLM
        model = (llm or build_llm()).with_structured_output(Diagnosis)
        alert = state.get("alert") or "Aucune alerte précise : analyse générale du namespace."
        messages = [
            ("system", SYSTEM_PROMPT),
            ("human", f"Alerte reçue : {alert}\n\nDonnées collectées :\n{state['context']}"),
        ]
        return {"diagnosis": model.invoke(messages)}

    graph = StateGraph(AgentState)
    graph.add_node("collect", collect)
    graph.add_node("diagnose", diagnose)
    graph.add_edge(START, "collect")
    graph.add_edge("collect", "diagnose")
    graph.add_edge("diagnose", END)
    return graph.compile()


def investigate(namespace: str, alert: str = "", **kwargs: Any) -> AgentState:
    """Lance une enquête complète sur un namespace."""
    return build_graph(**kwargs).invoke({"namespace": namespace, "alert": alert})
