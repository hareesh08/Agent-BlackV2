from .paper_search import search_papers
from .experiment_planner import plan_experiment
from .citation_generator import citation_generator
from .metrics import eval_metric_advisor
from .hyperparams import hyperparameter_advice
from .models import recommend_models
from .benchmark_search import benchmark_search_ml
from .feature_engineering import feature_engineering_advisor
from .explainability import model_explainability_advisor
from .time_series import time_series_strategy
from .gap_analysis import analyze_gaps
from .solution_recommendation import solution_recommendation
from .prototype_guidance import prototype_guidance
from .summarizer import summarize_paper

TOOLS = {
    "search_papers": search_papers,
    "experiment_planner": plan_experiment,
    "plan_experiment": plan_experiment,
    "citation_generator": citation_generator,
    "evaluation_metric_tool": eval_metric_advisor,
    "eval_metric_advisor": eval_metric_advisor,
    "hyperparameter_advice": hyperparameter_advice,
    "model_recommendation_tool": recommend_models,
    "recommend_models": recommend_models,
    "benchmark_search": benchmark_search_ml,
    "feature_engineering_advisor": feature_engineering_advisor,
    "model_explainability_advisor": model_explainability_advisor,
    "time_series_strategy": time_series_strategy,
    "analyze_gaps": analyze_gaps,
    "solution_recommendation": solution_recommendation,
    "prototype_guidance": prototype_guidance,
    "summarize_paper": summarize_paper,
}

def execute_tool(name: str, query: str = "", **kwargs) -> dict:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name](query=query, **kwargs)


from shared.mcp import register_tool

for _name, _fn in TOOLS.items():
    register_tool(_name, f"ML tool: {_name}", {"type": "object", "properties": {"query": {"type": "string"}}}, _fn)
