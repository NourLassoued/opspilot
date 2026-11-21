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
app = FastAPI(title="OpsPilot Agent", version="0.1.0")


class InvestigateRequest(BaseModel):
    namespace: str = "jobradar"
    alert: str = ""


class InvestigateResponse(BaseModel):
    namespace: str
    healthy: bool
    duration_seconds: float
    diagnosis: Diagnosis | None


@app.get("/health")
def health() -> dict:
    return {"status": "UP"}


@app.post("/investigate", response_model=InvestigateResponse)
def investigate_endpoint(req: InvestigateRequest) -> InvestigateResponse:
    start = time.time()
    result = investigate(req.namespace, req.alert)
    diagnosis = result.get("diagnosis")
    return InvestigateResponse(
        namespace=req.namespace,
        healthy=diagnosis is None,
        duration_seconds=round(time.time() - start, 2),
        diagnosis=diagnosis,
    )
