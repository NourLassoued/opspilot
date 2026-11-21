"""Collecte en LECTURE SEULE de l'état d'un namespace Kubernetes.

On récupère pour chaque pod en difficulté : son état, les raisons d'attente/d'arrêt,
les événements Kubernetes et les dernières lignes de logs.
"""
from __future__ import annotations

from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

MAX_LOG_LINES = 60
MAX_LOG_CHARS = 4000


def load_kube_config() -> None:
    """Dans le cluster : ServiceAccount. Sur le PC : ~/.kube/config (créé par k3d)."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _container_problem(cs: Any) -> dict[str, Any] | None:
    """Retourne un résumé si le conteneur a un problème, sinon None."""
    info: dict[str, Any] = {
        "container": cs.name,
        "image": cs.image,
        "ready": bool(cs.ready),
        "restarts": cs.restart_count or 0,
    }
    state = cs.state
    if state and state.waiting:
        info["state"] = "waiting"
        info["reason"] = state.waiting.reason
        info["message"] = state.waiting.message
    elif state and state.terminated:
        info["state"] = "terminated"
        info["reason"] = state.terminated.reason
        info["exit_code"] = state.terminated.exit_code
    else:
        info["state"] = "running"

    last = cs.last_state.terminated if cs.last_state else None
    if last:
        info["last_terminated_reason"] = last.reason
        info["last_exit_code"] = last.exit_code

    has_problem = (not cs.ready) or info["restarts"] > 0 or info["state"] != "running"
    return info if has_problem else None


def _pod_events(v1: client.CoreV1Api, namespace: str, pod_name: str) -> list[str]:
    events = v1.list_namespaced_event(namespace, field_selector=f"involvedObject.name={pod_name}").items
    events.sort(key=lambda e: e.last_timestamp or e.event_time or e.metadata.creation_timestamp)
    return [f"{e.type} {e.reason}: {e.message}" for e in events[-10:]]


def _pod_logs(v1: client.CoreV1Api, namespace: str, pod_name: str, container: str, previous: bool) -> str:
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name, namespace, container=container, tail_lines=MAX_LOG_LINES, previous=previous
        )
    except ApiException as exc:  # pas de logs (conteneur jamais démarré, image introuvable...)
        return f"(logs indisponibles : {exc.reason})"
    return logs[-MAX_LOG_CHARS:] if logs else "(aucun log)"


def collect_namespace_state(namespace: str, v1: client.CoreV1Api | None = None) -> dict[str, Any]:
    """Photographie l'état du namespace et détaille les pods en difficulté."""
    if v1 is None:
        load_kube_config()
        v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(namespace).items
    overview: list[str] = []
    unhealthy: list[dict[str, Any]] = []

    for pod in pods:
        statuses = pod.status.container_statuses or []
        ready = sum(1 for cs in statuses if cs.ready)
        overview.append(f"{pod.metadata.name} {ready}/{len(statuses)} {pod.status.phase}")

        problems = [p for cs in statuses if (p := _container_problem(cs))]
        if not problems and pod.status.phase in ("Running", "Succeeded"):
            continue

        for p in problems:
            p["logs"] = _pod_logs(v1, namespace, pod.metadata.name, p["container"], previous=False)
            if p["restarts"] > 0:
                p["previous_logs"] = _pod_logs(v1, namespace, pod.metadata.name, p["container"], previous=True)

        unhealthy.append(
            {
                "pod": pod.metadata.name,
                "phase": pod.status.phase,
                "node": pod.spec.node_name,
                "containers": problems,
                "events": _pod_events(v1, namespace, pod.metadata.name),
            }
        )

    return {"namespace": namespace, "overview": overview, "unhealthy_pods": unhealthy}


def format_for_llm(state: dict[str, Any]) -> str:
    """Transforme l'état collecté en texte lisible pour le LLM."""
    lines = [f"Namespace : {state['namespace']}", "", "Vue d'ensemble des pods :"]
    lines += [f"- {o}" for o in state["overview"]] or ["- (aucun pod)"]

    if not state["unhealthy_pods"]:
        lines += ["", "Aucun pod en difficulté."]
        return "\n".join(lines)

    for pod in state["unhealthy_pods"]:
        lines += ["", f"=== Pod en difficulté : {pod['pod']} (phase {pod['phase']}, nœud {pod['node']}) ==="]
        for c in pod["containers"]:
            details = ", ".join(f"{k}={v}" for k, v in c.items() if k not in ("logs", "previous_logs") and v is not None)
            lines.append(f"Conteneur : {details}")
            lines += ["Logs actuels :", c.get("logs", "")]
            if "previous_logs" in c:
                lines += ["Logs avant le dernier redémarrage :", c["previous_logs"]]
        lines.append("Événements Kubernetes :")
        lines += [f"- {e}" for e in pod["events"]] or ["- (aucun)"]
    return "\n".join(lines)
