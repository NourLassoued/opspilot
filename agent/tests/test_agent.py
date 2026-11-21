"""Tests sans cluster ni clé API : on simule Kubernetes et le LLM."""
from opspilot_agent.graph import build_graph
from opspilot_agent.k8s_collector import format_for_llm
from opspilot_agent.models import Diagnosis

BROKEN_STATE = {
    "namespace": "jobradar",
    "overview": ["jobradar-backend-abc 0/1 Pending", "postgres-0 1/1 Running"],
    "unhealthy_pods": [
        {
            "pod": "jobradar-backend-abc",
            "phase": "Pending",
            "node": "k3d-opspilot-agent-1",
            "containers": [
                {
                    "container": "backend",
                    "image": "ghcr.io/nourlassoued/jobradar-backend:9.9.9",
                    "ready": False,
                    "restarts": 0,
                    "state": "waiting",
                    "reason": "ImagePullBackOff",
                    "message": "Back-off pulling image",
                    "logs": "(logs indisponibles : Bad Request)",
                }
            ],
            "events": ["Warning Failed: Failed to pull image ...:9.9.9: not found"],
        }
    ],
}
HEALTHY_STATE = {"namespace": "jobradar", "overview": ["postgres-0 1/1 Running"], "unhealthy_pods": []}


class FakeLLM:
    """Faux LLM : vérifie ce qu'on lui envoie et renvoie un diagnostic fixe."""

    def __init__(self):
        self.received = None

    def with_structured_output(self, schema):
        assert schema is Diagnosis
        return self

    def invoke(self, messages):
        self.received = messages
        return Diagnosis(
            category="image",
            root_cause="L'image 9.9.9 n'existe pas.",
            confidence=0.95,
            evidence=["ImagePullBackOff"],
            affected_resources=["pod/jobradar-backend-abc"],
            suggested_fix="Revenir à la version 0.1.1.",
            fix_commands=["git revert HEAD"],
        )


def test_format_contains_key_evidence():
    text = format_for_llm(BROKEN_STATE)
    assert "ImagePullBackOff" in text
    assert "9.9.9" in text
    assert "Failed to pull image" in text


def test_graph_diagnoses_broken_namespace():
    llm = FakeLLM()
    result = build_graph(collector=lambda ns: BROKEN_STATE, llm=llm).invoke({"namespace": "jobradar", "alert": "PodImagePullFailed"})
    assert result["diagnosis"].category == "image"
    assert "PodImagePullFailed" in llm.received[1][1]


def test_graph_skips_llm_when_healthy():
    llm = FakeLLM()
    result = build_graph(collector=lambda ns: HEALTHY_STATE, llm=llm).invoke({"namespace": "jobradar"})
    assert result["diagnosis"] is None
    assert llm.received is None  # aucun appel au LLM -> aucun quota consommé
