import json
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from shared.a2a_sdk import send_text_task
from shared.llm import async_call_llm, extract_json
from shared.config import AGENT_URLS

DECOMPOSE_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "orchestrator.txt")
SELECTION_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "selection.txt")

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


async def _is_research_query(query: str) -> bool:
    result = await validate_research_query(query)
    return bool(result.get("is_research"))


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


async def orchestrate(query: str, progress_callback=None) -> dict:
    if progress_callback is None:
        progress_callback = lambda step, status, detail: None

    try:
        return await _orchestrate_inner(query, progress_callback)
    except Exception as e:
        progress_callback("orchestrator", "error", f"Orchestration failed: {e}")
        return {
            "error": str(e),
            "literature_review": "",
            "datasets": "",
            "models": "",
            "evaluation_plan": "",
            "prototype_guidance": "",
        }


async def _orchestrate_inner(query: str, progress_callback) -> dict:

    # ── Step 0: Research-relevance gate ────────────────────────────────────────
    progress_callback("validating_query", "running", "Checking if query is research-related...")
    validation = await validate_research_query(query)
    if not validation.get("is_research"):
        reason = str(validation.get("reason") or NOT_RESEARCH_RESPONSE["message"])
        progress_callback("validating_query", "complete", f"Query rejected: {reason}")
        return _build_not_research_response(reason, validation)
    progress_callback("validating_query", "complete", "Query is research-related")

    # ── Step 1: Select agents ──────────────────────────────────────────────────
    progress_callback("selecting_agents", "running", "Selecting relevant agents...")
    valid_agents = {"research", "solution", "experiment"}
    selected_agents = list(valid_agents)  # default fallback

    try:
        selection_prompt = _load_prompt_safe(SELECTION_PROMPT_PATH)
        selection_raw = await async_call_llm(
            system_prompt="You are a research orchestrator that selects relevant agents. You MUST respond with valid JSON only.",
            user_prompt=selection_prompt.format(query=query)
        )
        selection = extract_json(selection_raw)

        if isinstance(selection, dict):
            raw_list = selection.get("selected_agents", [])
            if isinstance(raw_list, list):
                selected_agents = [a for a in raw_list if isinstance(a, str) and a in valid_agents]
        elif isinstance(selection, list):
            selected_agents = [a for a in selection if isinstance(a, str) and a in valid_agents]

        if not selected_agents:
            progress_callback("selecting_agents", "complete", "No relevant agents found for this query")
            return NOT_RESEARCH_RESPONSE
        progress_callback("selecting_agents", "complete", f"Selected: {', '.join(selected_agents)}")
    except Exception as e:
        progress_callback("selecting_agents", "complete", f"Selection parse failed, using all agents")

    # ── Step 2: Decompose query ────────────────────────────────────────────────
    progress_callback("decomposing_task", "running", "Decomposing query into sub-tasks...")
    try:
        decompose_prompt = _load_prompt_safe(DECOMPOSE_PROMPT_PATH)
        decomposed_raw = await async_call_llm(
            system_prompt="You are a research orchestrator.",
            user_prompt=decompose_prompt.format(query=query)
        )
        tasks = extract_json(decomposed_raw)
        progress_callback("decomposing_task", "complete", "Query decomposed into sub-tasks")
    except Exception as e:
        tasks = {}
        progress_callback("decomposing_task", "complete", f"Decomposition failed, using original query: {e}")

    agent_endpoints = {
        "research": ("research_task", AGENT_URLS["research"]),
        "solution": ("solution_task", AGENT_URLS["solution"]),
        "experiment": ("experiment_task", AGENT_URLS["experiment"]),
    }

    # ── Step 3: Dispatch to sub-agents concurrently ────────────────────────────
    async def _call_agent(_client: httpx.AsyncClient, agent_name: str):
        task_key, base_url = agent_endpoints[agent_name]
        sub_query = tasks.get(task_key, query)
        progress_callback(agent_name, "running", f"Calling {agent_name} agent...")
        try:
            result = await send_text_task(base_url, sub_query)
            progress_callback(agent_name, "complete", f"{agent_name} agent completed")
            return agent_name, result
        except Exception as e:
            msg = f"{agent_name} agent A2A request failed: {e}"
            progress_callback(agent_name, "error", msg)
            return agent_name, {"error": msg}

    async with httpx.AsyncClient(timeout=120) as client:
        agent_tasks = [_call_agent(client, name) for name in selected_agents]
        agent_results = await asyncio.gather(*agent_tasks)
        responses = {name: result for name, result in agent_results}

    # ── Step 4: Aggregate results ──────────────────────────────────────────────
    progress_callback("aggregating", "running", "Aggregating results into final report...")
    try:
        agg_prompt = f"""
Combine these agent responses into a single research report.
Agents used: {json.dumps(selected_agents)}
Research: {json.dumps(responses.get('research', {'result': {}}))}
Solution: {json.dumps(responses.get('solution', {'result': {}}))}
Experiment: {json.dumps(responses.get('experiment', {'result': {}}))}
Return ONLY valid JSON with keys: literature_review, datasets, models, evaluation_plan, prototype_guidance
"""
        final_raw = await async_call_llm(
            system_prompt="You are a research report writer that synthesizes multi-agent outputs.",
            user_prompt=agg_prompt
        )
        progress_callback("aggregating", "complete", "Report finalized")
        result = extract_json(final_raw)
        if isinstance(result, dict):
            result["selected_agents"] = selected_agents
        return result
    except Exception as e:
        progress_callback("aggregating", "error", f"Aggregation failed: {e}")
        # Return raw agent responses as fallback
        fallback = {
            "literature_review": str(responses.get("research", {}).get("result", {})),
            "datasets": str(responses.get("research", {}).get("result", {})),
            "models": str(responses.get("solution", {}).get("result", {})),
            "evaluation_plan": str(responses.get("experiment", {}).get("result", {})),
            "prototype_guidance": f"Aggregation failed: {e}",
            "selected_agents": selected_agents,
        }
        return fallback
