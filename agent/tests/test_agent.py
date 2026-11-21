"""Tests sans cluster ni clé API : faux outils Kubernetes + faux LLM qui « joue » une enquête."""
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from opspilot_agent.graph import build_graph, initial_state
from opspilot_agent.models import Diagnosis

CALLS: list[str] = []


@tool
def list_pods(namespace: str) -> str:
    """Liste les pods."""
    CALLS.append("list_pods")
    return "- jobradar-backend-abc 0/1 phase=Running | état=waiting raison=CrashLoopBackOff"


@tool
def get_pod_logs(namespace: str, pod: str, previous: bool = False) -> str:
    """Logs d'un pod."""
    CALLS.append(f"get_pod_logs(previous={previous})")
    return "Caused by: java.net.UnknownHostException: postgres-inexistant"


DIAG = Diagnosis(
    category="config",
    root_cause="Mauvais hôte de base de données.",
    confidence=0.9,
    evidence=["UnknownHostException: postgres-inexistant"],
    affected_resources=["pod/jobradar-backend-abc"],
    suggested_fix="Corriger SPRING_DATASOURCE_URL dans jobradar-gitops.",
    fix_commands=["git revert HEAD"],
)


class ScriptedLLM:
    """Faux LLM : renvoie une suite de réponses prévues (demandes d'outils puis fin)."""

    def __init__(self, script):
        self.script = list(script)
        self.final_messages = None

    def bind_tools(self, tools):
        return self

    def with_structured_output(self, schema):
        assert schema is Diagnosis
        outer = self

        class _Structured:
            async def ainvoke(self, messages):
                outer.final_messages = messages
                return DIAG

        return _Structured()

    async def ainvoke(self, messages):
        return self.script.pop(0) if self.script else AIMessage(content="Fini.")


def ai_call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


async def test_agent_uses_tools_then_diagnoses():
    CALLS.clear()
    llm = ScriptedLLM([
        ai_call("list_pods", {"namespace": "jobradar"}, "1"),
        ai_call("get_pod_logs", {"namespace": "jobradar", "pod": "jobradar-backend-abc", "previous": True}, "2"),
        AIMessage(content="La cause est trouvée."),
    ])
    result = await build_graph([list_pods, get_pod_logs], llm).ainvoke(initial_state("jobradar", "PodCrashLooping"))
    assert CALLS == ["list_pods", "get_pod_logs(previous=True)"]
    assert result["tool_calls"] == 2
    assert result["diagnosis"].category == "config"
    # le diagnostic final voit bien les résultats des outils
    assert any("UnknownHostException" in str(m.content) for m in llm.final_messages)


async def test_tool_limit_stops_infinite_loop():
    CALLS.clear()
    llm = ScriptedLLM([ai_call("list_pods", {"namespace": "jobradar"}, str(i)) for i in range(50)])
    result = await build_graph([list_pods], llm, max_tool_calls=3).ainvoke(initial_state("jobradar", ""))
    assert len(CALLS) <= 4  # le garde-fou coupe la boucle
    assert result["diagnosis"] is not None
    # la demande d'outil restée sans réponse n'est pas envoyée au diagnostic final
    assert not getattr(llm.final_messages[-2], "tool_calls", None)


async def test_unknown_tool_error_does_not_crash():
    CALLS.clear()
    llm = ScriptedLLM([ai_call("outil_inexistant", {}, "1"), AIMessage(content="ok")])
    result = await build_graph([list_pods], llm).ainvoke(initial_state("jobradar", ""))
    assert result["diagnosis"] is not None
