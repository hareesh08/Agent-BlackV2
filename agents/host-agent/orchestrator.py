import json
import asyncio
import logging
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from shared.a2a_sdk import send_text_task
from shared.discovery import discover_agents, render_catalog
from shared.llm import async_call_llm, extract_json
from shared.logging_setup import LogTimer

logger = logging.getLogger("orchestrator")

DECOMPOSE_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "orchestrator.txt")
SELECTION_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "selection.txt")
AGGREGATOR_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "aggregator.txt")

RESEARCH_DOMAINS = [
    "computer vision", "image classification", "object detection", "segmentation",
    "medical imaging", "video analytics", "vision-language", "nlp", "llm",
    "natural language", "rag", "retrieval augmented", "prompt engineering",
    "text classification", "summarization", "conversational ai", "information extraction",
    "machine learning", "deep learning", "neural network", "model selection",
    "feature engineering", "time series", "hyperparameter", "experiment design",
    "evaluation strategy", "research", "dataset", "benchmark", "architecture",
    "transformer", "cnn", "diffusion", "gan", "reinforcement learning",
    "paper", "arxiv", "论文", "research proposal", "proof of concept",
]

RESEARCH_ACTIONS = [
    "recommend", "compare", "find", "search", "summarize", "analyze", "evaluate",
    "benchmark", "design", "plan", "prototype", "implement", "improve", "optimize",
    "select", "review", "survey", "study", "explore",
]

NON_RESEARCH_PATTERNS = [
    "weather", "movie", "song", "lyrics", "joke", "meme", "recipe", "restaurant",
    "sports score", "cricket score", "football score", "stock price", "bitcoin price",
    "translate this", "write birthday", "instagram caption", "what is my ip",
    "who are you", "hello", "hi", "good morning", "good night",
]

AMBIGUOUS_HINTS = [
    "model", "accuracy", "dataset", "classification", "training", "prediction",
    "evaluation", "architecture", "experiment",
]

# Deterministic domain → agent mapping for pre-routing checks.
# Each agent owns a set of keyword hints; if the query strongly matches one
# agent's domain AND that agent is offline, the system should refuse rather
# than silently route to a wrong agent.
AGENT_DOMAIN_HINTS: dict[str, list[str]] = {
    "research": [
        "computer vision", "image classification", "object detection", "segmentation",
        "medical imaging", "video analytics", "vision-language", "vision", "cv ",
        "cnn", "resnet", "yolo", "vit", "vision transformer", "diffusion",
        "gan", "image generation", "image segmentation", "pose estimation",
        "depth estimation", "optical flow", "3d reconstruction", "point cloud",
        "face recognition", "face detection", "ocr", "scene understanding",
    ],
    "solution": [
        "nlp", "natural language", "llm", "rag", "retrieval augmented",
        "prompt engineering", "text classification", "summarization",
        "conversational ai", "information extraction", "chatbot",
        "named entity", "ner", "sentiment", "question answering", "qa ",
        "language model", "gpt", "bert", "transformer nlp",
        "text generation", "machine translation", "tokenization",
        "embedding", "fine-tune", "fine tuning", "instruction tuning",
    ],
    "experiment": [
        "experiment design", "experiment agent", "ml experiment",
        "hyperparameter", "hyper-param", "hpo", "optuna",
        "feature engineering", "feature selection", "time series",
        "cross-validation", "k-fold", "ablation", "evaluation strategy",
        "metric selection", "model selection", "model comparison",
        "neural architecture search", "nas", "reinforcement learning",
        "rl agent", "reward function", "policy gradient",
    ],
}

# Friendly display names for each agent (used in error messages).
AGENT_DISPLAY_NAMES: dict[str, str] = {
    "research": "CV Research Agent",
    "solution": "NLP Solution Agent",
    "experiment": "ML Experiment Agent",
}

# ── Per-agent domain keywords for routing validation ────────────────────────
# Used to filter out agents that don't match the query's domain.
# If the LLM incorrectly selects an agent from the wrong domain, this filter
# drops it. If the correct agent is offline, the query fails with
# "no_suitable_agent" instead of silently routing to the wrong agent.

AGENT_DOMAINS = {
    "research": {
        "description": "Computer Vision",
        "keywords": [
            "vision", "image", "video", "cv", "object detection", "segmentation",
            "classification", "ocr", "face", "pose", "depth", "3d", "point cloud",
            "medical imaging", "radiology", "ct", "mri", "x-ray", "histopathology",
            "satellite", "aerial", "remote sensing", "document analysis",
            "vision-language", "vlm", "clip", "sam", "diffusion", "gan",
            "yolo", "resnet", "vit", "transformer", "cnn", "backbone",
            "paper", "arxiv", "survey", "benchmark", "dataset",
            "find papers", "search papers", "literature review",
            "find datasets", "cv datasets", "image datasets",
            "recommend models", "model recommendation", "architecture comparison",
            "research", "proposal", "proof of concept",
        ],
    },
    "solution": {
        "description": "NLP Solutions",
        "keywords": [
            "nlp", "text", "language", "llm", "gpt", "bert", "transformer",
            "rag", "retrieval", "embedding", "vector", "semantic search",
            "prompt", "prompt engineering", "fine-tuning", "fine tuning",
            "chatbot", "dialogue", "conversational", "qa", "question answering",
            "summarization", "translation", "sentiment", "ner", "named entity",
            "information extraction", "text classification", "spam detection",
            "named entity recognition", "relation extraction",
            "document", "corpus", "tokenization", "word embedding",
            "openai", "anthropic", "gemini", "claude", "llama", "mistral",
            "inference", "deployment", "serving", "pipeline",
            "design rag", "rag pipeline", "knowledge base",
            "llm benchmark", "llm evaluation", "prompt optimization",
            "information extraction", "text processing",
        ],
    },
    "experiment": {
        "description": "ML Experiment Design",
        "keywords": [
            "experiment", "training", "hyperparameter", "tuning", "optimization",
            "metric", "evaluation", "accuracy", "precision", "recall", "f1",
            "auc", "roc", "confusion matrix", "cross validation",
            "feature engineering", "feature selection", "data preprocessing",
            "model selection", "model comparison", "ablation",
            "benchmark", "leaderboard", "baseline",
            "time series", "forecasting", "regression",
            "pipeline", "workflow", "mlops", "tracking", "mlflow",
            "explainability", "interpretability", "shap", "lime",
            "hyperparameter tuning", "grid search", "random search",
            "evaluation plan", "experiment design", "experiment planning",
            "model explainability", "feature importance",
        ],
    },
}

NOT_RESEARCH_RESPONSE = {
    "error": "not_research_query",
    "message": "This query does not appear to be related to AI/ML research. This system is a Research Assistant that helps with: Computer Vision, NLP, Machine Learning research — including literature review, dataset recommendation, model selection, experiment planning, and prototype guidance. Please ask a research-related question.",
    "reason": "The query does not look like a research, dataset, model, experiment, or prototype request.",
    "suggestion": "Try asking about papers, datasets, models, evaluation metrics, experiment design, or prototype guidance.",
    "supported_topics": [
        "Research paper discovery and summarization",
        "Dataset recommendation (CV, NLP, ML)",
        "Model/architecture recommendation",
        "Experiment design and planning",
        "Benchmark search and comparison",
        "Research gap analysis",
        "Prototype development guidance",
    ],
}


def _build_not_research_response(reason: str, validation: dict | None = None) -> dict:
    response = dict(NOT_RESEARCH_RESPONSE)
    response["reason"] = reason
    if validation:
        response["validation"] = validation
    return response


def load_prompt(path: str) -> str:
    with open(path) as f:
        return f.read()


def _load_prompt_safe(path: str) -> str:
    try:
        content = load_prompt(path)
        if not content.strip():
            raise ValueError(f"Prompt file is empty: {path}")
        return content
    except (FileNotFoundError, ValueError) as e:
        raise RuntimeError(f"Failed to load prompt from {path}: {e}")


def _rule_based_validation(query: str) -> dict:
    query_lower = query.lower().strip()
    tokens = [token for token in query_lower.replace("/", " ").replace("-", " ").split() if token]

    matched_domains = [domain for domain in RESEARCH_DOMAINS if domain in query_lower]
    matched_actions = [action for action in RESEARCH_ACTIONS if action in query_lower]
    matched_negative = [pattern for pattern in NON_RESEARCH_PATTERNS if pattern in query_lower]
    matched_ambiguous = [hint for hint in AMBIGUOUS_HINTS if hint in query_lower]

    score = 0
    if len(query_lower) >= 12:
        score += 1
    if "?" in query or len(tokens) >= 4:
        score += 1
    score += min(len(matched_domains), 3) * 2
    score += min(len(matched_actions), 2)
    score += min(len(matched_ambiguous), 2)
    score -= min(len(matched_negative), 3) * 3

    decision = "ambiguous"
    if len(query_lower) < 5 or matched_negative:
        decision = "reject"
    elif matched_domains and (matched_actions or len(tokens) >= 4):
        decision = "accept"
    elif score >= 4:
        decision = "accept"
    elif score <= 0:
        decision = "reject"

    return {
        "decision": decision,
        "score": score,
        "matched_domains": matched_domains,
        "matched_actions": matched_actions,
        "matched_negative": matched_negative,
        "matched_ambiguous": matched_ambiguous,
    }


async def validate_research_query(query: str) -> dict:
    query_lower = query.lower().strip()
    if len(query_lower) < 5:
        return {
            "is_research": False,
            "method": "rule_based",
            "reason": "The query is too short to classify as a research request.",
            "rule_based": _rule_based_validation(query),
        }

    rule_result = _rule_based_validation(query)
    if rule_result["decision"] == "accept":
        return {
            "is_research": True,
            "method": "rule_based",
            "reason": "The query contains clear research-related keywords and intent.",
            "rule_based": rule_result,
        }
    if rule_result["decision"] == "reject":
        return {
            "is_research": False,
            "method": "rule_based",
            "reason": "The query matches non-research patterns or lacks research intent.",
            "rule_based": rule_result,
        }

    gate_prompt = f"""You are a research query classifier. Determine if the following query is related to AI, Machine Learning, Computer Vision, NLP, academic/scientific research, datasets, model selection, evaluation, experiments, or prototype guidance.

Respond ONLY with valid JSON in this shape:
{{
  "is_research": true,
  "reason": "brief reason",
  "category": "research|implementation|general|other"
}}

Query: {query}"""
    try:
        raw = await async_call_llm(
            system_prompt="You are a strict classifier. Accept only queries that clearly ask for AI/ML/CV/NLP research help, evaluation, experiments, models, datasets, or prototype guidance.",
            user_prompt=gate_prompt,
        )
        ai_result = extract_json(raw)
        return {
            "is_research": bool(ai_result.get("is_research", False)),
            "method": "hybrid_ai",
            "reason": str(ai_result.get("reason", "Classification completed.")),
            "category": ai_result.get("category", "other"),
            "rule_based": rule_result,
        }
    except Exception:
        return {
            "is_research": False,
            "method": "rule_based_fallback",
            "reason": "The query is ambiguous and the AI validator was unavailable.",
            "rule_based": rule_result,
        }


def _detect_target_agent_domain(query: str) -> str | None:
    """Deterministically detect which agent domain a query belongs to.

    Returns the agent key ("research", "solution", "experiment") if the query
    has a strong domain signal, or None if it's ambiguous / cross-domain.
    """
    query_lower = query.lower()
    scores: dict[str, int] = {}
    for agent_name, hints in AGENT_DOMAIN_HINTS.items():
        score = sum(1 for hint in hints if hint in query_lower)
        if score > 0:
            scores[agent_name] = score

    if not scores:
        return None

    # Only return a clear winner — if two domains tie, it's ambiguous.
    best_agent = max(scores, key=scores.get)
    best_score = scores[best_agent]
    second_best = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    if best_score >= 2 and best_score > second_best:
        return best_agent
    return None


def _check_offline_target(query: str, catalog: list[dict]) -> dict | None:
    """Return an error response if the query targets an offline agent.

    This runs *before* the LLM routing step so that we never silently
    re-route a domain-specific query to the wrong agent.
    """
    target = _detect_target_agent_domain(query)
    if target is None:
        return None  # ambiguous — let the LLM decide

    catalog_by_name = {a["name"]: a for a in catalog}
    agent_info = catalog_by_name.get(target)
    if agent_info is None:
        return None  # agent not in catalog at all
    if agent_info.get("online", True):
        return None  # agent is online — proceed normally

    display = AGENT_DISPLAY_NAMES.get(target, target)
    logger.warning(
        "[Step 1.5] Query targets OFFLINE agent '%s' (%s) — refusing to reroute",
        target,
        display,
    )
    return {
        "error": "no_suitable_agent",
        "message": (
            f"No suitable agent is available for this query. "
            f"The {display} is the best fit but is currently offline. "
            f"Please start the agent service and try again."
        ),
        "offline_agent": target,
    }


def _build_routing_prompt(catalog_text: str, query: str) -> str:
    template = _load_prompt_safe(SELECTION_PROMPT_PATH)
    return template.replace("{{CATALOG}}", catalog_text).replace("{{QUERY}}", query)


def _classify_query_domains(query: str) -> set[str]:
    """Classify which agent domains match the query using keyword matching.

    Returns a set of matching domain names: 'research', 'solution', 'experiment'.
    Empty set means the query is too ambiguous to assign a domain.
    """
    query_lower = query.lower().strip()
    matches: dict[str, int] = {}
    for domain, info in AGENT_DOMAINS.items():
        score = sum(1 for kw in info["keywords"] if kw in query_lower)
        if score > 0:
            matches[domain] = score
    if not matches:
        return set()
    max_score = max(matches.values())
    threshold = max(1, max_score // 3)
    return {d for d, s in matches.items() if s >= threshold}


def _filter_by_domain(
    selected: list[dict], query: str
) -> tuple[list[dict], list[str]]:
    """Filter LLM-selected agents against the query's domain.

    Drops agents that don't match the query's domain. If all agents are
    dropped, returns an empty list with the drop reasons.
    """
    domains = _classify_query_domains(query)
    if not domains:
        return selected, []

    valid: list[dict] = []
    drops: list[str] = []
    for entry in selected:
        name = entry["name"]
        if name in domains:
            valid.append(entry)
        else:
            agent_desc = AGENT_DOMAINS.get(name, {}).get("description", name)
            query_domains = ", ".join(AGENT_DOMAINS[d]["description"] for d in domains)
            drops.append(
                f"agent '{name}' ({agent_desc}) does not match query domain ({query_domains})"
            )
    return valid, drops


def _parse_routing_decision(raw: str) -> dict:
    try:
        parsed = extract_json(raw)
    except Exception as e:
        logger.warning("Routing JSON parse failed: %s", e)
        return {"selected_agents": [], "reasoning": f"Parse failed: {e}"}

    if not isinstance(parsed, dict):
        return {"selected_agents": [], "reasoning": "Routing response was not a JSON object."}

    raw_list = parsed.get("selected_agents")
    if not isinstance(raw_list, list):
        return {"selected_agents": [], "reasoning": "No selected_agents list in response."}

    normalized: list[dict] = []
    for entry in raw_list:
        if isinstance(entry, str):
            normalized.append({"name": entry, "tools": [], "sub_query": ""})
        elif isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                tools = entry.get("tools") or []
                tools = [t for t in tools if isinstance(t, str) and t.strip()]
                sub_query = entry.get("sub_query") or entry.get("query") or ""
                if not isinstance(sub_query, str):
                    sub_query = ""
                normalized.append(
                    {"name": name.strip(), "tools": tools, "sub_query": sub_query.strip()}
                )

    return {
        "selected_agents": normalized,
        "reasoning": str(parsed.get("reasoning", "")),
    }


def _filter_routing_against_catalog(
    routing: dict, catalog: list[dict]
) -> tuple[list[dict], list[str], list[str]]:
    catalog_by_name = {a["name"]: a for a in catalog}
    valid: list[dict] = []
    drops: list[str] = []
    offline_agents: list[str] = []
    for entry in routing.get("selected_agents", []):
        name = entry["name"]
        if name not in catalog_by_name:
            drops.append(f"unknown agent '{name}'")
            continue
        agent = catalog_by_name[name]
        if not agent.get("online", True):
            drops.append(f"agent '{name}' is offline")
            offline_agents.append(name)
            continue
        available_tools = {t["name"] for t in agent.get("tools", [])}
        requested_tools = entry.get("tools", []) or []
        kept_tools = [t for t in requested_tools if t in available_tools]
        dropped_tools = [t for t in requested_tools if t not in available_tools]
        for t in dropped_tools:
            drops.append(f"tool '{t}' not on agent '{name}'")
        valid.append({**entry, "name": name, "tools": kept_tools})
    return valid, drops, offline_agents


async def orchestrate(query: str, progress_callback=None) -> dict:
    if progress_callback is None:
        progress_callback = lambda step, status, detail: None

    try:
        return await _orchestrate_inner(query, progress_callback)
    except Exception as e:
        progress_callback("orchestrator", "error", f"Orchestration failed: {e}")
        logger.exception("Orchestration failed: %s", e)
        return {
            "error": str(e),
            "tech_stack": [],
            "literature_review": "",
            "datasets": "",
            "models": "",
            "evaluation_plan": "",
            "prototype_guidance": "",
        }


async def _orchestrate_inner(query: str, progress_callback) -> dict:
    logger.info("=" * 60)
    logger.info("ORCHESTRATION START  query=%s", query[:200])

    # ── Step 0: Research-relevance gate ────────────────────────────────────────
    logger.info("[Step 0] Validating research relevance...")
    with LogTimer(logger, "validation"):
        progress_callback("validating_query", "running", "Checking if query is research-related...")
        validation = await validate_research_query(query)

    if not validation.get("is_research"):
        reason = str(validation.get("reason") or NOT_RESEARCH_RESPONSE["message"])
        logger.info(
            "[Step 0] Query REJECTED  method=%s  reason=%s",
            validation.get("method"),
            reason[:200],
        )
        progress_callback("validating_query", "complete", f"Query rejected: {reason}")
        return _build_not_research_response(reason, validation)

    logger.info(
        "[Step 0] Query ACCEPTED  method=%s  reason=%s",
        validation.get("method"),
        validation.get("reason", "")[:200],
    )
    progress_callback("validating_query", "complete", "Query is research-related")

    # ── Step 1: Live agent + tool discovery ───────────────────────────────────
    logger.info("[Step 1] Discovering live agents and their tools...")
    progress_callback("discovering_agents", "running", "Discovering live agents and their tools...")
    with LogTimer(logger, "agent_discovery"):
        catalog = await discover_agents()

    if not catalog:
        logger.warning("[Step 1] No agents are reachable")
        progress_callback("discovering_agents", "error", "No agents are reachable")
        return {
            "error": "no_agents_available",
            "message": "No specialist agents responded to discovery. Check that the 3 agent services are running on :8001/:8002/:8003.",
        }

    # Log each discovered agent with IP/port/tools
    online_count = sum(1 for a in catalog if a.get("online", True))
    for agent in catalog:
        status = "ONLINE" if agent.get("online", True) else "OFFLINE"
        tool_names = [t["name"] for t in agent.get("tools", [])]
        logger.info(
            "[Step 1] Agent discovered  name=%s  status=%s  url=%s  port=%s  tools=%d  tool_list=%s",
            agent["name"],
            status,
            agent.get("url", "N/A"),
            agent.get("port", "N/A"),
            len(tool_names),
            tool_names,
        )

    logger.info(
        "[Step 1] Discovery complete  total=%d  online=%d  agents=%s",
        len(catalog),
        online_count,
        [a["name"] for a in catalog],
    )
    progress_callback(
        "discovering_agents",
        "complete",
        f"Found {len(catalog)} agents: {', '.join(a['name'] for a in catalog)}",
    )

    # ── Step 1.5: Deterministic offline-agent guard ────────────────────────
    # If the query clearly targets one agent domain and that agent is offline,
    # refuse immediately instead of letting the LLM silently reroute.
    offline_error = _check_offline_target(query, catalog)
    if offline_error:
        progress_callback(
            "routing", "complete",
            f"The {offline_error['offline_agent']} agent is offline — refusing to reroute.",
        )
        return offline_error

    # ── Step 2: LLM picks agents + tools from the live catalog ────────────────
    logger.info("[Step 2] LLM routing — selecting agents and tools...")
    progress_callback("routing", "running", "LLM is selecting agents and tools...")
    with LogTimer(logger, "llm_routing"):
        try:
            catalog_text = render_catalog(catalog)
            routing_prompt = _build_routing_prompt(catalog_text, query)
            routing_raw = await async_call_llm(
                system_prompt="You are a research routing orchestrator. Output ONLY valid JSON. No prose, no markdown.",
                user_prompt=routing_prompt,
                json_mode=True,
            )
            routing = _parse_routing_decision(routing_raw)
        except Exception as e:
            logger.error("[Step 2] Routing LLM call failed: %s", e)
            progress_callback("routing", "error", f"Routing LLM call failed: {e}")
            return {
                "error": "routing_failed",
                "message": "The orchestrator's routing LLM call failed.",
                "reason": str(e),
            }

    # Log raw routing decision
    logger.info(
        "[Step 2] LLM raw decision  agents_requested=%s  reasoning=%s",
        [a["name"] for a in routing.get("selected_agents", [])],
        routing.get("reasoning", "")[:300],
    )

    # Filter against live catalog and log drops
    selected, drop_reasons, offline_agents = _filter_routing_against_catalog(routing, catalog)
    if drop_reasons:
        for drop in drop_reasons:
            logger.warning("[Step 2] Routing drop: %s", drop)

    # Filter against query domain — drop agents that don't match
    if selected:
        selected, domain_drops = _filter_by_domain(selected, query)
        if domain_drops:
            for drop in domain_drops:
                logger.warning("[Step 2] Domain filter drop: %s", drop)

    if not selected:
        if offline_agents:
            names = ", ".join(offline_agents)
            logger.warning("[Step 2] Required agents OFFLINE: %s", names)
            msg = f"The correct agent(s) for this query ({names}) are currently offline."
            progress_callback("routing", "complete", msg)
            return {
                "error": "no_suitable_agent",
                "message": f"No suitable agent available. The required agent(s) ({names}) are offline. Please start the agent service(s) and try again.",
                "routing": routing,
            }
        query_domains = _classify_query_domains(query)
        if query_domains:
            domain_names = ", ".join(AGENT_DOMAINS[d]["description"] for d in query_domains)
            msg = f"No suitable agent available for this query. Required domain: {domain_names}."
        else:
            msg = "No suitable agent available for this query."
        logger.info("[Step 2] No matching agent for query domains=%s", query_domains)
        progress_callback("routing", "complete", msg)
        return {
            "error": "no_suitable_agent",
            "message": msg,
            "routing": routing,
        }

    # Log final selected agents with IP, port, and MCP tools
    selected_names = [s["name"] for s in selected]
    reasoning = routing.get("reasoning", "")
    for s in selected:
        agent_info = next((a for a in catalog if a["name"] == s["name"]), {})
        logger.info(
            "[Step 2] Agent SELECTED  name=%s  url=%s  port=%s  mcp_tools=%s  sub_query=%s",
            s["name"],
            agent_info.get("url", "N/A"),
            agent_info.get("port", "N/A"),
            s.get("tools", []),
            (s.get("sub_query") or "N/A")[:150],
        )

    logger.info(
        "[Step 2] Routing complete  selected=%s  reasoning=%s",
        selected_names,
        reasoning[:300],
    )
    progress_callback(
        "routing",
        "complete",
        json.dumps({"agents": selected_names, "reasoning": reasoning}),
    )

    # ── Step 3: Dispatch to sub-agents concurrently with pre-selected tools ───
    logger.info(
        "[Step 3] Dispatching to %d agent(s): %s",
        len(selected),
        selected_names,
    )
    progress_callback("dispatching", "running", f"Dispatching to {len(selected)} agent(s)...")
    catalog_by_name = {a["name"]: a for a in catalog}
    dispatch_start = time.perf_counter()

    async def _call_agent(_client: httpx.AsyncClient, entry: dict):
        name = entry["name"]
        agent_info = catalog_by_name[name]
        base_url = agent_info["url"]
        agent_port = agent_info.get("port", "N/A")
        sub_query = entry.get("sub_query") or query
        tools = entry.get("tools") or []
        envelope = json.dumps(
            {
                "query": query,
                "sub_query": sub_query,
                "tools": tools,
            }
        )
        logger.info(
            "[Step 3] Dispatching  agent=%s  url=%s  port=%s  mcp_tools=%s",
            name,
            base_url,
            agent_port,
            tools,
        )
        progress_callback(
            name,
            "running",
            json.dumps({"tools": tools, "message": f"Calling {name} with {len(tools)} pre-selected tool(s)..."}),
        )
        agent_start = time.perf_counter()
        try:
            result = await send_text_task(base_url, envelope)
            elapsed_ms = round((time.perf_counter() - agent_start) * 1000, 1)
            snippet = ""
            if isinstance(result, dict):
                snippet = json.dumps(result, indent=2)[:500]
            elif isinstance(result, str):
                snippet = result[:500]
            logger.info(
                "[Step 3] Agent response  agent=%s  url=%s  elapsed=%sms  tools=%s",
                name,
                base_url,
                elapsed_ms,
                tools,
            )
            progress_callback(name, "complete", json.dumps({"tools": tools, "snippet": snippet}))
            return name, result
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - agent_start) * 1000, 1)
            msg = f"{name} A2A request failed: {e}"
            logger.error(
                "[Step 3] Agent FAILED  agent=%s  url=%s  elapsed=%sms  error=%s",
                name,
                base_url,
                elapsed_ms,
                e,
            )
            progress_callback(name, "error", msg)
            return name, {"error": msg}

    async with httpx.AsyncClient(timeout=300) as client:
        agent_tasks = [_call_agent(client, entry) for entry in selected]
        agent_results = await asyncio.gather(*agent_tasks)
        responses = {name: result for name, result in agent_results}

    dispatch_elapsed_ms = round((time.perf_counter() - dispatch_start) * 1000, 1)
    logger.info(
        "[Step 3] Dispatch complete  agents=%s  total_elapsed=%sms",
        selected_names,
        dispatch_elapsed_ms,
    )
    progress_callback("dispatching", "complete", "All agent responses received")

    # ── Step 4: Aggregate results ──────────────────────────────────────────────
    logger.info("[Step 4] Aggregating results from %d agent(s)...", len(selected))
    progress_callback("aggregating", "running", "Aggregating results into final report...")
    agg_start = time.perf_counter()
    try:
        agg_template = _load_prompt_safe(AGGREGATOR_PROMPT_PATH)
        agg_user = agg_template.format(
            agents=json.dumps(selected_names),
            research=json.dumps(responses.get("research", {"result": {}}))[:6000],
            solution=json.dumps(responses.get("solution", {"result": {}}))[:6000],
            experiment=json.dumps(responses.get("experiment", {"result": {}}))[:6000],
        )
        final_raw = None
        try:
            final_raw = await async_call_llm(
                system_prompt="You are a senior research synthesiser. Output ONLY valid JSON.",
                user_prompt=agg_user,
                json_mode=True,
            )
        except Exception as e:
            logger.warning("[Step 4] Aggregator json_mode failed, retrying without it: %s", e)
            final_raw = await async_call_llm(
                system_prompt="You are a senior research synthesiser. Output ONLY valid JSON.",
                user_prompt=agg_user,
            )
        result = _parse_aggregator_output(final_raw)
        agg_elapsed_ms = round((time.perf_counter() - agg_start) * 1000, 1)
        logger.info(
            "[Step 4] Aggregation complete  elapsed=%sms  sections=%s",
            agg_elapsed_ms,
            [k for k in result if k not in ("selected_agents", "routing_reasoning", "parse_warning")],
        )
        progress_callback("aggregating", "complete", "Report finalized")
        if isinstance(result, dict):
            result["selected_agents"] = selected_names
            result["routing_reasoning"] = routing.get("reasoning", "")
        total_elapsed = round((time.perf_counter() - dispatch_start) * 1000, 1)
        logger.info(
            "ORCHESTRATION COMPLETE  agents=%s  total_pipeline_ms=%sms",
            selected_names,
            total_elapsed,
        )
        logger.info("=" * 60)
        return result
    except Exception as e:
        agg_elapsed_ms = round((time.perf_counter() - agg_start) * 1000, 1)
        logger.error(
            "[Step 4] Aggregation FAILED  elapsed=%sms  error=%s",
            agg_elapsed_ms,
            e,
        )
        progress_callback("aggregating", "error", f"Aggregation failed: {e}")
        def _extract_section(agent_key: str, section_keys: list[str] | None = None) -> str:
            agent_resp = responses.get(agent_key)
            if isinstance(agent_resp, dict):
                if section_keys:
                    for sk in section_keys:
                        if sk in agent_resp:
                            val = agent_resp[sk]
                            return val if isinstance(val, str) else json.dumps(val, indent=2)
                return json.dumps(agent_resp, indent=2)
            if agent_resp is not None:
                return json.dumps(agent_resp, indent=2) if not isinstance(agent_resp, str) else agent_resp
            return ""

        fallback = {
            "tech_stack": [],
            "literature_review": _extract_section("research", ["literature_review", "papers", "text"]),
            "datasets": _extract_section("research", ["datasets", "datasets_found", "data"]),
            "models": _extract_section("research", ["models", "model_recommendations", "architecture"]),
            "evaluation_plan": _extract_section("experiment", ["evaluation_plan", "experiments", "metrics"]),
            "prototype_guidance": _extract_section("solution", ["prototype_guidance", "guidance", "recommendations"]),
            "selected_agents": selected_names,
            "routing_reasoning": routing.get("reasoning", ""),
            "parse_warning": "aggregator_failed",
        }
        if not any(v for k, v in fallback.items() if k not in ("selected_agents", "routing_reasoning", "parse_warning", "tech_stack")):
            fallback["prototype_guidance"] = f"Aggregation failed: {e}. Agent responses: {json.dumps({k: str(v)[:200] for k, v in responses.items()})}"
        return fallback


def _parse_aggregator_output(raw: str) -> dict:
    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("aggregator did not return a JSON object")

    tech_stack = parsed.get("tech_stack") or []
    if not isinstance(tech_stack, list):
        tech_stack = []
    tech_stack = [
        str(t).strip() for t in tech_stack
        if t is not None and str(t).strip()
    ]
    seen = set()
    deduped = []
    for t in tech_stack:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    tech_stack = deduped

    section_keys = (
        "literature_review", "datasets", "models",
        "evaluation_plan", "prototype_guidance",
    )

    result: dict = {"tech_stack": tech_stack}
    for key in section_keys:
        value = parsed.get(key)
        if isinstance(value, str):
            result[key] = value
        elif isinstance(value, dict):
            obj = dict(value)
            obj.setdefault("text", "")
            result[key] = obj
        elif value is None:
            result[key] = ""
        else:
            result[key] = str(value)

    return result
