"""Lancer une enquête depuis le terminal.

Exemple : python -m opspilot_agent.cli --namespace jobradar
"""
import argparse
import json
import os
import time

from dotenv import load_dotenv

from .graph import investigate


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="OpsPilot — diagnostic d'incident Kubernetes")
    parser.add_argument("--namespace", "-n", default=os.getenv("NAMESPACE", "jobradar"))
    parser.add_argument("--alert", "-a", default="", help="Texte de l'alerte reçue (optionnel)")
    parser.add_argument("--show-context", action="store_true", help="Afficher les données envoyées au LLM")
    args = parser.parse_args()

    print(f"🔎 Enquête OpsPilot sur le namespace '{args.namespace}'...")
    start = time.time()
    result = investigate(args.namespace, args.alert)
    elapsed = time.time() - start

    if args.show_context:
        print("\n--- Données collectées ---\n" + result["context"] + "\n--------------------------")

    diagnosis = result.get("diagnosis")
    if diagnosis is None:
        print(f"✅ Aucun pod en difficulté dans '{args.namespace}'. ({elapsed:.1f} s)")
        return

    print(f"\n🩺 Diagnostic ({elapsed:.1f} s)\n")
    print(json.dumps(diagnosis.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
