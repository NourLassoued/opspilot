"""Lancer une enquête depuis le terminal, en affichant le raisonnement de l'agent étape par étape.

Exemples :
  python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping"                    # diagnostic seul
  python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping" --allow-actions    # + réparation après validation
"""
import argparse
import asyncio
import json
import os
import time

from dotenv import load_dotenv

from .graph import investigate


def print_step(node: str, data: dict) -> None:
    for msg in (data or {}).get("messages", []):
        for call in getattr(msg, "tool_calls", []) or []:
            args = ", ".join(f"{k}={v}" for k, v in call["args"].items())
            print(f"  🔧 {call['name']}({args})")
        if node == "tools":
            content = msg.content
            if isinstance(content, list):  # format MCP : [{"type": "text", "text": "..."}]
                content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
            preview = str(content).strip().splitlines()[0][:110] if content else ""
            print(f"     ↳ {preview}")
    if node == "diagnose":
        print("  🧠 Rédaction du diagnostic…")


def ask_human(request: dict) -> bool:
    r = request["remediation"]
    print("\n" + "=" * 70)
    print("🛑 VALIDATION HUMAINE REQUISE — OpsPilot propose une réparation")
    print(f"   Action      : {r['action']}")
    if r.get("commit_sha"):
        print(f"   Commit      : {r['commit_sha']} ({r.get('repo_url')})")
    if r.get("file_path"):
        print(f"   Fichier     : {r['file_path']}")
    if r.get("argocd_app"):
        print(f"   Application : {r['argocd_app']}")
    print(f"   Pourquoi    : {r['explanation']}")
    print("=" * 70)
    return input("Approuver cette réparation ? (oui/non) : ").strip().lower() in ("oui", "o", "yes", "y")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="OpsPilot — diagnostic d'incident Kubernetes")
    parser.add_argument("--namespace", "-n", default=os.getenv("NAMESPACE", "jobradar"))
    parser.add_argument("--alert", "-a", default="", help="Texte de l'alerte reçue (optionnel)")
    parser.add_argument("--allow-actions", action="store_true",
                        help="Autoriser OpsPilot à proposer une réparation (exécutée seulement si tu réponds oui)")
    args = parser.parse_args()

    print(f"🔎 Enquête OpsPilot sur le namespace '{args.namespace}'…")
    start = time.time()

    def approver(request: dict) -> bool:
        nonlocal start
        pause = time.time()
        decision = ask_human(request)
        start += time.time() - pause  # le temps de réflexion humain n'est pas compté
        return decision

    result = asyncio.run(investigate(args.namespace, args.alert, on_step=print_step,
                                     approver=approver if args.allow_actions else None))
    elapsed = time.time() - start

    diagnosis = result.get("diagnosis")
    print(f"\n🩺 Diagnostic ({elapsed:.1f} s, {result.get('tool_calls', 0)} appels d'outils)\n")
    print(json.dumps(diagnosis.model_dump() if diagnosis else None, indent=2, ensure_ascii=False))
    if result.get("action_result"):
        print(f"\n🛠️  {result['action_result']}")


if __name__ == "__main__":
    main()
