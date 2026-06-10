import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter
from app.models import SettingsUpdate, SettingsResponse, LLMSettings
from shared.config import get_setting, set_setting, get_all_settings, AGENT_URLS

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
def get_settings():
    return SettingsResponse(
        llm_provider=get_setting("LLM_PROVIDER", "gemini"),
        providers={
            "gemini": LLMSettings(
                provider="gemini",
                model=get_setting("GEMINI_MODEL", "gemini-1.5-flash"),
                api_key_set=bool(get_setting("GEMINI_API_KEY")),
                base_url=get_setting("GEMINI_BASE_URL") or None,
            ),
            "openai": LLMSettings(
                provider="openai",
                model=get_setting("OPENAI_MODEL", "gpt-4o"),
                api_key_set=bool(get_setting("OPENAI_API_KEY")),
                base_url=get_setting("OPENAI_BASE_URL"),
            ),
            "anthropic": LLMSettings(
                provider="anthropic",
                model=get_setting("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                api_key_set=bool(get_setting("ANTHROPIC_API_KEY")),
                base_url=get_setting("ANTHROPIC_BASE_URL") or None,
            ),
        },
        kaggle_username=get_setting("KAGGLE_USERNAME", ""),
        kaggle_key_set=bool(get_setting("KAGGLE_KEY")),
        agent_urls=AGENT_URLS,
    )


@router.put("/settings")
def update_settings(update: SettingsUpdate):
    updates = {}
    if update.llm_provider:
        updates["LLM_PROVIDER"] = update.llm_provider
    if update.gemini_api_key is not None:
        updates["GEMINI_API_KEY"] = update.gemini_api_key
    if update.gemini_base_url is not None:
        updates["GEMINI_BASE_URL"] = update.gemini_base_url
    if update.gemini_model:
        updates["GEMINI_MODEL"] = update.gemini_model
    if update.openai_api_key is not None:
        updates["OPENAI_API_KEY"] = update.openai_api_key
    if update.openai_base_url is not None:
        updates["OPENAI_BASE_URL"] = update.openai_base_url
    if update.openai_model:
        updates["OPENAI_MODEL"] = update.openai_model
    if update.anthropic_api_key is not None:
        updates["ANTHROPIC_API_KEY"] = update.anthropic_api_key
    if update.anthropic_base_url is not None:
        updates["ANTHROPIC_BASE_URL"] = update.anthropic_base_url
    if update.anthropic_model:
        updates["ANTHROPIC_MODEL"] = update.anthropic_model
    if update.kaggle_username is not None:
        updates["KAGGLE_USERNAME"] = update.kaggle_username
    if update.kaggle_key is not None:
        updates["KAGGLE_KEY"] = update.kaggle_key
    if update.research_agent_url:
        updates["RESEARCH_AGENT_URL"] = update.research_agent_url
    if update.solution_agent_url:
        updates["SOLUTION_AGENT_URL"] = update.solution_agent_url
    if update.experiment_agent_url:
        updates["EXPERIMENT_AGENT_URL"] = update.experiment_agent_url

    for k, v in updates.items():
        if v is not None:
            set_setting(k, v)

    # Reload shared.config module so in-memory vars reflect the new values
    import importlib
    import shared.config
    importlib.reload(shared.config)

    return {"message": "Settings updated", "updated": list(updates.keys())}
