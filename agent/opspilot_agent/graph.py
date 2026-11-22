"""Le graphe LangGraph de l'agent (Sprint 3).

   START → enquêter ⇄ outils (K8s, Prometheus, ArgoCD, Git)
         → diagnostiquer
         → [si réparation automatique possible et actions autorisées]
             → validation humaine (pause) → exécuter → END
"""
from __future__ import annotations

import os
import uuid
from contextlib import AsyncExitStack
from typing import Annotated, Any, Callable, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from .models import Diagnosis

MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "14"))  # garde-fou : jamais de boucle infinie

SYSTEM_PROMPT = """Tu es OpsPilot, un ingénieur SRE expert de Kubernetes et de GitOps (ArgoCD).
Tu enquêtes sur un incident en utilisant les OUTILS fournis (lecture seule).

Méthode :
1. list_pods (et get_firing_alerts si utile) pour repérer les pods en difficulté.
2. get_pod_events, puis get_pod_logs (previous=True si le pod a redémarré).
3. get_deployment_config pour les vrais noms de variables et l'image ; get_rollout_history pour la dernière version saine.
4. get_argocd_application (l'application porte en général le nom du namespace) pour savoir d'où vient le changement.
5. Choisis la réparation :
   - Application OutOfSync avec synchro automatique DÉSACTIVÉE → quelqu'un a modifié le cluster à la main (dérive) :
     remediation.action = "argocd_sync" (Git a raison, on remet le cluster comme dans Git).
   - Application Synced → le changement fautif vient de Git : list_git_commits(repo_url, path) puis
     get_git_commit_diff pour PROUVER le commit fautif → remediation.action = "git_revert" avec son SHA court.
   - Sinon → "manual".
6. Arrête-toi dès que la cause et la réparation sont prouvées : pas d'appels inutiles.

Règles :
- N'invente JAMAIS un nom, un chemin de fichier ou un SHA que tu n'as pas vu dans un résultat d'outil.
- La correction passe par Git (GitOps), jamais par kubectl edit/set ; jamais le tag "latest".
- Réponds en français."""

FINAL_INSTRUCTION = """Rédige maintenant le diagnostic final à partir des seuls résultats d'outils ci-dessus.
- evidence : recopie mot pour mot les lignes qui prouvent la cause (y compris la ligne du diff Git si tu l'as).
- last_known_good : la dernière image/révision/commit sain si l'historique le montre.
- suggested_fix : du texte uniquement ; les commandes vont dans fix_commands (une par élément, vrais SHA et chemins).
- remediation : l'action automatique (git_revert, argocd_sync, manual ou none) avec ses paramètres exacts.
- Si aucun pod n'a de problème, category="none" et remediation.action="none"."""

AUTO_ACTIONS = ("git_revert", "argocd_sync")


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    namespace: str
    alert: str
    tool_calls: int
    diagnosis: Diagnosis | None
    approved: bool | None
    action_result: str | None


def build_llm():
    from langchain_groq import ChatGroq

    return ChatGroq(model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"), temperature=0)


def build_graph(
    tools: list[BaseTool],
    llm: Any | None = None,
    max_tool_calls: int = MAX_TOOL_CALLS,
    allow_actions: bool = False,
    executor: Callable | None = None,
    checkpointer: Any | None = None,
):
    llm = llm or build_llm()
    llm_with_tools = llm.bind_tools(tools)

    async def investigate(state: AgentState) -> AgentState:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response], "tool_calls": state.get("tool_calls", 0) + len(response.tool_calls)}

    def route_investigation(state: AgentState) -> str:
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

    def route_after_diagnosis(state: AgentState) -> str:
        diag = state.get("diagnosis")
        if allow_actions and diag and diag.remediation and diag.remediation.action in AUTO_ACTIONS:
            return "approve"
        return END

    def approve(state: AgentState) -> AgentState:
        # Le graphe se met en PAUSE ici et attend la décision d'un humain.
        decision = interrupt({"remediation": state["diagnosis"].remediation.model_dump()})
        return {"approved": bool(decision)}

    def execute(state: AgentState) -> AgentState:
        if not state.get("approved"):
            return {"action_result": "Réparation refusée par l'humain : rien n'a été modifié."}
        from .actions import execute as run_action

        try:
            return {"action_result": (executor or run_action)(state["diagnosis"].remediation)}
        except Exception as exc:  # l'échec d'une action ne doit pas faire planter l'agent
            return {"action_result": f"Échec de la réparation : {exc}"}

    graph = StateGraph(AgentState)
    graph.add_node("investigate", investigate)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_node("diagnose", diagnose)
    graph.add_node("approve", approve)
    graph.add_node("execute", execute)
    graph.add_edge(START, "investigate")
    graph.add_conditional_edges("investigate", route_investigation, {"tools": "tools", "diagnose": "diagnose"})
    graph.add_edge("tools", "investigate")
    graph.add_conditional_edges("diagnose", route_after_diagnosis, {"approve": "approve", END: END})
    graph.add_edge("approve", "execute")
    graph.add_edge("execute", END)
    return graph.compile(checkpointer=checkpointer)


def initial_state(namespace: str, alert: str) -> AgentState:
    return {
        "namespace": namespace,
        "alert": alert,
        "tool_calls": 0,
        "messages": [
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(f"Namespace : {namespace}\nAlerte reçue : {alert or 'aucune (analyse générale)'}\n"
                         "Enquête avec les outils, puis arrête-toi quand la cause et la réparation sont prouvées."),
        ],
    }


async def run_graph(graph, state_or_command, config, on_step, final: dict) -> dict | None:
    """Fait avancer le graphe ; renvoie la demande de validation s'il se met en pause."""
    async for update in graph.astream(state_or_command, config, stream_mode="updates"):
        for node, data in update.items():
            if node == "__interrupt__":
                return data[0].value
            if on_step:
                on_step(node, data)
            final.update({k: v for k, v in (data or {}).items() if k in ("diagnosis", "action_result", "approved")})
            if data and "tool_calls" in data:
                final["tool_calls"] = data["tool_calls"]
    return None


async def investigate(
    namespace: str,
    alert: str = "",
    on_step: Callable | None = None,
    llm: Any | None = None,
    approver: Callable[[dict], bool] | None = None,
) -> dict:
    """Lance une enquête complète.
    approver(demande) -> bool : si fourni, l'agent peut proposer une réparation et attend cette décision.
    Sans approver, l'agent diagnostique seulement (aucune action possible)."""
    from .tools import open_tools

    async with AsyncExitStack() as stack:
        tools = await open_tools(stack)
        graph = build_graph(tools, llm, allow_actions=approver is not None, checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 70}
        final: dict = {}
        request = await run_graph(graph, initial_state(namespace, alert), config, on_step, final)
        if request is not None and approver is not None:
            await run_graph(graph, Command(resume=approver(request)), config, on_step, final)
        return final
