import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from shared.models import AgentRequest
from shared.a2a_sdk import add_sdk_a2a_routes, agent_card_to_legacy_dict, build_agent_card
from shared.config import HOST_AGENT_URL
from orchestrator import orchestrate

app = FastAPI(title="Host Agent / Orchestrator")

AGENT_NAME = "Host Orchestrator"
TASKS = [
    "research_orchestration", "agent_selection",
    "task_decomposition", "result_aggregation",
]

AGENT_CARD = build_agent_card(
    name=AGENT_NAME,
    description="Orchestrates CV, NLP, and ML agents for research queries",
    base_url=HOST_AGENT_URL,
    tasks=TASKS,
)

add_sdk_a2a_routes(app, card=AGENT_CARD, run_fn=orchestrate)

@app.get("/.well-known/agent-card")
def agent_card():
    return agent_card_to_legacy_dict(AGENT_CARD)

@app.post("/research")
async def research(req: AgentRequest):
    result = await orchestrate(req.query)
    return {"query": req.query, "report": result}

@app.get("/health")
def health():
    return {"status": "ok", "agent": "Host Orchestrator"}

@app.get("/")
def root():
    return {
        "name": "Agent Black",
        "agents": ["Computer Vision Research Agent", "NLP Solution Agent", "ML Experiment Agent"],
        "endpoints": {
            "POST /research": "Submit a research query to all agents",
            "POST /a2a": "A2A protocol endpoint",
            "GET /.well-known/agent-card": "Legacy agent card endpoint",
            "GET /.well-known/agent-card.json": "Standard A2A agent card endpoint",
            "GET /health": "Health check",
        }
    }
