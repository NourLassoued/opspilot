"""API HTTP de l'agent (utilisée plus tard par le backend Spring Boot).

Lancer : uvicorn opspilot_agent.api:app --reload --port 8000
"""
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from .graph import investigate
from .models import Diagnosis

load_dotenv()
app = FastAPI(title="OpsPilot Agent", version="0.2.0")


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


@app.get("/health")
def health() -> dict:
    return {"status": "UP"}


@app.post("/investigate", response_model=InvestigateResponse)
async def investigate_endpoint(req: InvestigateRequest) -> InvestigateResponse:
    steps: list[Step] = []

    def record(node: str, data: dict) -> None:
        calls = [c for m in data.get("messages", []) for c in (getattr(m, "tool_calls", None) or [])]
        if calls:
            steps.extend(Step(node=node, tool=c["name"], args=c["args"]) for c in calls)
        elif node == "diagnose":
            steps.append(Step(node=node))

    start = time.time()
    result = await investigate(req.namespace, req.alert, on_step=record)
    return InvestigateResponse(
        namespace=req.namespace,
        duration_seconds=round(time.time() - start, 2),
        tool_calls=result.get("tool_calls", 0),
        steps=steps,
        diagnosis=result.get("diagnosis"),
    )
