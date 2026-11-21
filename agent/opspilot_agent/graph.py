"""Le graphe LangGraph de l'agent (Sprint 2) : enquête avec outils -> diagnostic.

   START -> enquêter --(l'IA demande un outil)--> outils --> enquêter --> ...
                   +-(l'IA a fini, ou limite atteinte)--> diagnostiquer -> END
"""
from __future__ import annotations

import os
from contextlib import AsyncExitStack
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .models import Diagnosis

MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))  # garde-fou : jamais de boucle infinie

SYSTEM_PROMPT = """Tu es OpsPilot, un ingénieur SRE expert de Kubernetes et de GitOps (ArgoCD).
Tu enquêtes sur un incident en utilisant les OUTILS fournis (lecture seule).

Méthode :
1. Commence par list_pods (et get_firing_alerts si utile) pour repérer les pods en difficulté.
2. Creuse : get_pod_events, puis get_pod_logs (previous=True si le pod a redémarré).
3. Vérifie la configuration réelle avec get_deployment_config (vrais noms de variables, image).
4. Cherche la dernière version qui fonctionnait avec get_rollout_history.
5. Arrête-toi dès que la cause est prouvée : n'appelle pas d'outils inutiles.

Règles :
- N'invente JAMAIS un nom (variable, ConfigMap, image, tag) que tu n'as pas vu dans un résultat d'outil.
- Le cluster est géré en GitOps : la correction recommandée passe par le dépôt Git (ex. git revert
  du commit fautif dans jobradar-gitops, ou correction du manifest), pas par kubectl edit/set.
- Ne propose jamais le tag "latest".
- Réponds en français."""

FINAL_INSTRUCTION = """Rédige maintenant le diagnostic final à partir des seuls résultats d'outils ci-dessus.
- evidence : recopie mot pour mot les lignes qui prouvent la cause.
- last_known_good : la dernière image/révision saine si l'historique la montre.
- suggested_fix : du texte uniquement ; les commandes vont dans fix_commands (une par élément).
- Si aucun pod n'a de problème, category="none"."""


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    namespace: str
    alert: str
    tool_calls: int
    diagnosis: Diagnosis | None


def build_llm():
    from langchain_groq import ChatGroq

    return ChatGroq(model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"), temperature=0)


def build_graph(tools: list[BaseTool], llm: Any | None = None, max_tool_calls: int = MAX_TOOL_CALLS):
    llm = llm or build_llm()
    llm_with_tools = llm.bind_tools(tools)

    async def investigate(state: AgentState) -> AgentState:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response], "tool_calls": state.get("tool_calls", 0) + len(response.tool_calls)}

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls and state.get("tool_calls", 0) <= max_tool_calls:
            return "tools"
        return "diagnose"

    async def diagnose(state: AgentState) -> AgentState:
        messages = list(state["messages"])
        if isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            messages = messages[:-1]  # limite atteinte : on retire la demande d'outil restée sans réponse
        structured = llm.with_structured_output(Diagnosis)
        return {"diagnosis": await structured.ainvoke([*messages, HumanMessage(FINAL_INSTRUCTION)])}

    graph = StateGraph(AgentState)
    graph.add_node("investigate", investigate)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_node("diagnose", diagnose)
    graph.add_edge(START, "investigate")
    graph.add_conditional_edges("investigate", route, {"tools": "tools", "diagnose": "diagnose"})
    graph.add_edge("tools", "investigate")
    graph.add_edge("diagnose", END)
    return graph.compile()


def initial_state(namespace: str, alert: str) -> AgentState:
    return {
        "namespace": namespace,
        "alert": alert,
        "tool_calls": 0,
        "messages": [
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(f"Namespace : {namespace}\nAlerte reçue : {alert or 'aucune (analyse générale)'}\n"
                         "Enquête avec les outils, puis arrête-toi quand la cause est prouvée."),
        ],
    }


async def investigate(namespace: str, alert: str = "", on_step=None, llm: Any | None = None) -> AgentState:
    """Lance une enquête complète. on_step(nom_du_nœud, mise_à_jour) permet d'afficher le raisonnement en direct."""
    from .tools import open_tools

    async with AsyncExitStack() as stack:
        tools = await open_tools(stack)
        graph = build_graph(tools, llm)
        final: AgentState = {}
        async for update in graph.astream(initial_state(namespace, alert), {"recursion_limit": 60}, stream_mode="updates"):
            for node, data in update.items():
                if on_step:
                    on_step(node, data)
                if "diagnosis" in data:
                    final["diagnosis"] = data["diagnosis"]
                final["tool_calls"] = data.get("tool_calls", final.get("tool_calls", 0))
        return final
