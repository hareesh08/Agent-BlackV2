import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException
import httpx
from app.models import AgentCardResponse
from shared.config import AGENT_URLS
from shared.a2a_sdk import A2A_CARD_PATH
from app.database import save_agent_discovery, get_agent_discovery

router = APIRouter(tags=["discovery"])

AGENT_NAMES = {
    "research": "Computer Vision Research Agent",
    "solution": "NLP Solution Agent",
    "experiment": "ML Experiment Agent",
}

AGENT_META = {
    "research": {"name": "Research Agent", "port": 8001, "url": AGENT_URLS.get("research", "http://localhost:8001")},
    "solution": {"name": "Solution Agent", "port": 8002, "url": AGENT_URLS.get("solution", "http://localhost:8002")},
    "experiment": {"name": "Experiment Agent", "port": 8003, "url": AGENT_URLS.get("experiment", "http://localhost:8003")},
}


@router.get("/agents/discover")
async def discover_agents():
    results = {}
    for key, url in AGENT_URLS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{url}{A2A_CARD_PATH}")
                if r.status_code == 200:
                    data = r.json()
                    results[key] = data
                    skills = [skill.get("id", "") for skill in data.get("skills", []) if isinstance(skill, dict)]
                    port = 0
                    for iface in data.get("supportedInterfaces", []):
                        if isinstance(iface, dict):
                            try:
                                port = int(str(iface.get("url", "")).rsplit(":", 1)[-1].split("/")[0])
                                break
                            except (ValueError, IndexError):
                                continue
                    save_agent_discovery(key, url, port, skills, "running")
                else:
                    results[key] = {"error": f"HTTP {r.status_code}"}
        except Exception as e:
            results[key] = {"error": str(e)}
    return {"agents": results}


@router.get("/agents/{agent_name}/card", response_model=AgentCardResponse)
async def get_agent_card(agent_name: str):
    if agent_name not in AGENT_URLS:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")
    url = AGENT_URLS[agent_name]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{url}{A2A_CARD_PATH}")
            r2 = await client.get(f"{url}/health")
            r3 = await client.get(f"{url}/tools")
            r4 = await client.get(f"{url}/capabilities")

            card = r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}"}
            mcp_payload = r3.json() if r3.status_code == 200 else {"tools": {}}
            capabilities_payload = r4.json() if r4.status_code == 200 else {}

            raw_tools = mcp_payload.get("tools", {}) if isinstance(mcp_payload, dict) else {}
            mcp_tools = []
            if isinstance(raw_tools, dict):
                mcp_tools = [tool for tool in raw_tools.values() if isinstance(tool, dict)]
            elif isinstance(raw_tools, list):
                mcp_tools = [tool for tool in raw_tools if isinstance(tool, dict)]

            card_capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}
            communication_methods = {
                "a2a_jsonrpc": bool(isinstance(card, dict) and card.get("supportedInterfaces")),
                "streaming": bool(isinstance(card_capabilities, dict) and card_capabilities.get("streaming")),
                "polling": True,
                "health": r2.status_code == 200,
                "legacy_card": True,
                "mcp": r3.status_code == 200,
                "rest": bool(capabilities_payload.get("port")) if isinstance(capabilities_payload, dict) else True,
            }

            return AgentCardResponse(
                card=card,
                health=r2.json().get("status", "unknown") if r2.status_code == 200 else "stopped",
                mcp_tools=mcp_tools,
                communication_methods=communication_methods,
            )
    except Exception as e:
        return AgentCardResponse(
            card={"error": str(e)},
            health="stopped",
            mcp_tools=[],
            communication_methods={},
        )


@router.get("/agents/discovered")
def get_discovered_agents():
    from app.database import get_agent_discovery
    discovered = get_agent_discovery()
    if discovered:
        return {"agents": discovered}
    return {"agents": [
        {"name": "research-agent", "port": 8001, "url": AGENT_URLS.get("research", "http://localhost:8001")},
        {"name": "solution-agent", "port": 8002, "url": AGENT_URLS.get("solution", "http://localhost:8002")},
        {"name": "experiment-agent", "port": 8003, "url": AGENT_URLS.get("experiment", "http://localhost:8003")},
    ]}
