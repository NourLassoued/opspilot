"""API HTTP de l'agent, appelée par le backend Spring Boot.

- POST /investigate : enquête + diagnostic (aucune action, jamais).
- POST /remediate   : exécute UNE réparation déjà validée par un humain dans le backend.
                      Protégée par un jeton partagé (AGENT_API_TOKEN) : seul le backend peut l'appeler.

Lancer : uvicorn opspilot_agent.api:app --port 8000
"""
import hmac
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import actions
from .graph import investigate
from .models import Diagnosis, Remediation

load_dotenv()
app = FastAPI(title="OpsPilot Agent", version="0.4.0")


class InvestigateRequest(BaseModel):
    namespace: str = "jobradar"
    alert: str = ""


class Step(BaseModel):
    node: str
    tool: str | None = None
    args: dict | None = None


class InvestigateResponse(BaseModel):
    namespace: str
    duration_seconds: float
    tool_calls: int
    steps: list[Step]
    diagnosis: Diagnosis | None


class RemediateRequest(BaseModel):
    remediation: Remediation


class RemediateResponse(BaseModel):
    success: bool
    message: str


@app.get("/health")
def health() -> dict:
    return {"status": "UP"}


@app.post("/investigate", response_model=InvestigateResponse)
async def investigate_endpoint(req: InvestigateRequest) -> InvestigateResponse:
    steps: list[Step] = []

    def record(node: str, data: dict) -> None:
        calls = [c for m in (data or {}).get("messages", []) for c in (getattr(m, "tool_calls", None) or [])]
        if calls:
            steps.extend(Step(node=node, tool=c["name"], args=c["args"]) for c in calls)
        elif node == "diagnose":
            steps.append(Step(node=node))

    start = time.time()
    result = await investigate(req.namespace, req.alert, on_step=record)  # sans approver : aucune action
    return InvestigateResponse(
        namespace=req.namespace,
        duration_seconds=round(time.time() - start, 2),
        tool_calls=result.get("tool_calls", 0),
        steps=steps,
        diagnosis=result.get("diagnosis"),
    )


@app.post("/remediate", response_model=RemediateResponse)
def remediate_endpoint(req: RemediateRequest, authorization: str | None = Header(default=None)) -> RemediateResponse:
    expected = os.getenv("AGENT_API_TOKEN", "")
    if not expected or not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Jeton invalide : seul le backend OpsPilot peut réparer.")
    try:
        return RemediateResponse(success=True, message=actions.execute(req.remediation))
    except Exception as exc:  # l'échec est renvoyé au backend, qui passe l'incident en FAILED
        return RemediateResponse(success=False, message=str(exc))
