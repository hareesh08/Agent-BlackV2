import asyncio
import logging
import os
import sys
from typing import Any

import httpx

if __name__ != "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import AGENT_URLS

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 3.0


async def _fetch_agent(client: httpx.AsyncClient, name: str, url: str) -> dict[str, Any] | None:
    try:
        cap_task = client.get(f"{url.rstrip('/')}/capabilities", timeout=DISCOVERY_TIMEOUT)
        tools_task = client.get(f"{url.rstrip('/')}/tools", timeout=DISCOVERY_TIMEOUT)
        health_task = client.get(f"{url.rstrip('/')}/health", timeout=DISCOVERY_TIMEOUT)
        cap_resp, tools_resp, health_resp = await asyncio.gather(
            cap_task, tools_task, health_task, return_exceptions=True
        )
    except Exception as e:
        logger.warning("Discovery request failed for %s at %s: %s", name, url, e)
        return None

    if isinstance(cap_resp, Exception) or cap_resp.status_code != 200:
        logger.warning("Capabilities unreachable for %s", name)
        return None

    if isinstance(health_resp, Exception) or health_resp.status_code != 200:
        logger.warning("Health check failed for %s", name)
        return None

    try:
        capabilities = cap_resp.json()
    except Exception:
        capabilities = {}

    tools: list[dict[str, str]] = []
    if not isinstance(tools_resp, Exception) and tools_resp.status_code == 200:
        try:
            raw_tools = tools_resp.json().get("tools", [])
        except Exception:
            raw_tools = []

        # Endpoint can return either a list of tool objects or a dict keyed by tool name.
        if isinstance(raw_tools, dict):
            raw_tools = [
                {"name": k, **(v if isinstance(v, dict) else {})}
                for k, v in raw_tools.items()
            ]
        elif not isinstance(raw_tools, list):
            raw_tools = []

        for t in raw_tools:
            if isinstance(t, dict) and t.get("name"):
                tools.append(
                    {
                        "name": str(t["name"]),
                        "description": str(t.get("description", "")).strip(),
                    }
                )

    return {
        "name": name,
        "url": url,
        "description": str(capabilities.get("description", "")).strip(),
        "port": capabilities.get("port"),
        "tools": tools,
    }


async def discover_agents() -> list[dict[str, Any]]:
    """Discover all configured agents and their available tools at runtime.

    Returns a list of:
        {
            "name": "research",
            "url": "http://localhost:8001",
            "description": "Computer Vision ...",
            "port": 8001,
            "tools": [{"name": "search_papers", "description": "..."}, ...]
        }

    Agents that fail discovery (offline, timeout, non-200) are silently skipped.
    """
    async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT) as client:
        tasks = [_fetch_agent(client, name, url) for name, url in AGENT_URLS.items()]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def render_catalog(catalog: list[dict[str, Any]]) -> str:
    """Render the catalog as a human-readable text block for LLM prompts."""
    if not catalog:
        return "(no agents are currently online)"

    blocks: list[str] = []
    for agent in catalog:
        lines = [
            f"[Agent: {agent['name']}]",
            f"  URL: {agent['url']}",
            f"  Description: {agent['description'] or '(none)'}",
            "  Tools:",
        ]
        if agent["tools"]:
            for tool in agent["tools"]:
                desc = tool["description"][:160].replace("\n", " ")
                lines.append(f"    - {tool['name']}: {desc}")
        else:
            lines.append("    (no tools discovered)")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


if __name__ == "__main__":
    import json
    print(json.dumps(asyncio.run(discover_agents()), indent=2))
