"""Serveur MCP « k8s-inspector » : outils Kubernetes en LECTURE SEULE pour l'agent OpsPilot.

Règles de sécurité :
- aucune écriture dans le cluster ;
- les Secrets ne sont JAMAIS lus : on affiche seulement leur nom ;
- chaque réponse est tronquée pour limiter les tokens envoyés au LLM.

Lancement manuel (test) : python mcp-servers/k8s_inspector/server.py
"""
from __future__ import annotations

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from mcp.server.fastmcp import FastMCP

MAX_CHARS = 3500
mcp = FastMCP("k8s-inspector", log_level="WARNING")
_core: client.CoreV1Api | None = None
_apps: client.AppsV1Api | None = None


def _apis() -> tuple[client.CoreV1Api, client.AppsV1Api]:
    global _core, _apps
    if _core is None:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        _core, _apps = client.CoreV1Api(), client.AppsV1Api()
    return _core, _apps


def _cut(text: str) -> str:
    return text if len(text) <= MAX_CHARS else "…(début tronqué)…\n" + text[-MAX_CHARS:]


def _container_line(cs) -> str:
    parts = [f"conteneur={cs.name}", f"image={cs.image}", f"ready={cs.ready}", f"restarts={cs.restart_count}"]
    if cs.state and cs.state.waiting:
        parts.append(f"état=waiting raison={cs.state.waiting.reason} message={cs.state.waiting.message}")
    elif cs.state and cs.state.terminated:
        parts.append(f"état=terminated raison={cs.state.terminated.reason} code={cs.state.terminated.exit_code}")
    else:
        parts.append("état=running")
    if cs.last_state and cs.last_state.terminated:
        t = cs.last_state.terminated
        parts.append(f"dernier_arrêt={t.reason} code={t.exit_code}")
    return " | ".join(parts)


@mcp.tool()
def list_pods(namespace: str) -> str:
    """Liste les pods d'un namespace avec leur état (prêt, redémarrages, raison d'erreur).
    À appeler EN PREMIER pour repérer les pods en difficulté."""
    core, _ = _apis()
    lines = []
    for pod in core.list_namespaced_pod(namespace).items:
        statuses = pod.status.container_statuses or []
        ready = sum(1 for cs in statuses if cs.ready)
        lines.append(f"- {pod.metadata.name} {ready}/{len(statuses)} phase={pod.status.phase} nœud={pod.spec.node_name}")
        for cs in statuses:
            if not cs.ready or cs.restart_count:
                lines.append("    " + _container_line(cs))
    return _cut("\n".join(lines) or "Aucun pod dans ce namespace.")


@mcp.tool()
def get_pod_events(namespace: str, pod: str) -> str:
    """Événements Kubernetes d'un pod (image introuvable, sonde en échec, OOMKilled, planification…)."""
    core, _ = _apis()
    events = core.list_namespaced_event(namespace, field_selector=f"involvedObject.name={pod}").items
    events.sort(key=lambda e: e.last_timestamp or e.event_time or e.metadata.creation_timestamp)
    return _cut("\n".join(f"- {e.type} {e.reason} (x{e.count or 1}): {e.message}" for e in events[-12:]) or "Aucun événement.")


@mcp.tool()
def get_pod_logs(namespace: str, pod: str, previous: bool = False, tail_lines: int = 60) -> str:
    """Dernières lignes de logs d'un pod. previous=True donne les logs AVANT le dernier redémarrage :
    indispensable quand un pod est en CrashLoopBackOff (la cause du crash y est souvent)."""
    core, _ = _apis()
    try:
        logs = core.read_namespaced_pod_log(pod, namespace, tail_lines=min(tail_lines, 200), previous=previous)
    except ApiException as exc:
        return f"Logs indisponibles ({exc.status} {exc.reason}) : le conteneur n'a peut-être jamais démarré."
    return _cut(logs or "(aucun log)")


@mcp.tool()
def get_deployment_config(namespace: str, deployment: str) -> str:
    """Configuration d'un Deployment : image, variables d'environnement (valeurs des Secrets masquées),
    limites de ressources, sondes. Permet de connaître les VRAIS noms de variables."""
    _, apps = _apis()
    dep = apps.read_namespaced_deployment(deployment, namespace)
    lines = [f"Deployment {deployment} — révision {dep.metadata.annotations.get('deployment.kubernetes.io/revision', '?')}"]
    for c in dep.spec.template.spec.containers:
        lines.append(f"Conteneur {c.name} : image={c.image}")
        for e in c.env or []:
            if e.value is not None:
                lines.append(f"  env {e.name}={e.value}")
            elif e.value_from and e.value_from.secret_key_ref:
                ref = e.value_from.secret_key_ref
                lines.append(f"  env {e.name}=<valeur secrète : secret {ref.name}, clé {ref.key}>")
            else:
                lines.append(f"  env {e.name}=<valeur dynamique>")
        for src in c.env_from or []:
            if src.secret_ref:
                lines.append(f"  envFrom secret {src.secret_ref.name}")
            if src.config_map_ref:
                lines.append(f"  envFrom configmap {src.config_map_ref.name}")
        if c.resources:
            lines.append(f"  ressources : requests={c.resources.requests} limits={c.resources.limits}")
        for name, probe in (("startup", c.startup_probe), ("liveness", c.liveness_probe), ("readiness", c.readiness_probe)):
            if probe and probe.http_get:
                lines.append(f"  sonde {name} : GET {probe.http_get.path}")
    for v in dep.spec.template.spec.volumes or []:
        if v.secret:
            lines.append(f"Volume {v.name} : secret {v.secret.secret_name} (contenu non lu)")
    return _cut("\n".join(lines))


@mcp.tool()
def get_rollout_history(namespace: str, deployment: str) -> str:
    """Historique des versions d'un Deployment (ReplicaSets) : révision, image, pods prêts.
    Sert à trouver la DERNIÈRE VERSION QUI FONCTIONNAIT avant la panne."""
    _, apps = _apis()
    dep = apps.read_namespaced_deployment(deployment, namespace)
    selector = ",".join(f"{k}={v}" for k, v in dep.spec.selector.match_labels.items())
    rs_list = apps.list_namespaced_replica_set(namespace, label_selector=selector).items
    rows = []
    for rs in rs_list:
        rev = int(rs.metadata.annotations.get("deployment.kubernetes.io/revision", 0))
        images = ", ".join(c.image for c in rs.spec.template.spec.containers)
        rows.append((rev, f"- révision {rev} : {images} | souhaités={rs.spec.replicas} prêts={rs.status.ready_replicas or 0} | créé {rs.metadata.creation_timestamp:%Y-%m-%d %H:%M}"))
    rows.sort(reverse=True)
    return _cut("\n".join(r for _, r in rows) or "Aucun historique.")


if __name__ == "__main__":
    mcp.run()
