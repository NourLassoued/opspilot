"""Lancer une enquête depuis le terminal, en affichant le raisonnement de l'agent étape par étape.

Exemple : python -m opspilot_agent.cli -n jobradar -a "PodCrashLooping"
"""
import argparse
import asyncio
import json
import os
import time

from dotenv import load_dotenv

from .graph import investigate


def print_step(node: str, data: dict) -> None:
    for msg in data.get("messages", []):
        for call in getattr(msg, "tool_calls", []) or []:
            args = ", ".join(f"{k}={v}" for k, v in call["args"].items())
            print(f"  🔧 {call['name']}({args})")
        if node == "tools":
            preview = str(msg.content).strip().splitlines()[0][:110] if msg.content else ""
            print(f"     ↳ {preview}")
    if node == "diagnose":
        print("  🧠 Rédaction du diagnostic…")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="OpsPilot — diagnostic d'incident Kubernetes")
    parser.add_argument("--namespace", "-n", default=os.getenv("NAMESPACE", "jobradar"))
    parser.add_argument("--alert", "-a", default="", help="Texte de l'alerte reçue (optionnel)")
    args = parser.parse_args()

    print(f"🔎 Enquête OpsPilot sur le namespace '{args.namespace}'…")
    start = time.time()
    result = asyncio.run(investigate(args.namespace, args.alert, on_step=print_step))
    elapsed = time.time() - start

    diagnosis = result.get("diagnosis")
    print(f"\n🩺 Diagnostic ({elapsed:.1f} s, {result.get('tool_calls', 0)} appels d'outils)\n")
    print(json.dumps(diagnosis.model_dump() if diagnosis else None, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
