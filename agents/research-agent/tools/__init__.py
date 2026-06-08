from .paper_search import search_papers
from .summarizer import summarize_paper
from .gap_analysis import analyze_gaps
from .cv_datasets import find_cv_datasets
from .cv_models import recommend_cv_models
from .citation_generator import citation_generator
from .benchmark_search import benchmark_search_cv
from .eval_advisor import eval_metric_advisor_cv
from .architecture_comparison import architecture_comparison
from .synthetic_data import synthetic_data_strategy
from .solution_recommendation import solution_recommendation
from .prototype_guidance import prototype_guidance
from .experiment_planner import experiment_planner

TOOLS = {
    "search_papers": search_papers,
    "summarize_paper": summarize_paper,
    "analyze_gaps": analyze_gaps,
    "find_cv_datasets": find_cv_datasets,
    "recommend_cv_models": recommend_cv_models,
    "citation_generator": citation_generator,
    "benchmark_search": benchmark_search_cv,
    "evaluation_metric_tool": eval_metric_advisor_cv,
    "eval_metric_advisor": eval_metric_advisor_cv,
    "architecture_comparison": architecture_comparison,
    "synthetic_data_strategy": synthetic_data_strategy,
    "solution_recommendation": solution_recommendation,
    "prototype_guidance": prototype_guidance,
    "experiment_planner": experiment_planner,
}

def execute_tool(name: str, query: str = "", **kwargs) -> dict:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name](query=query, **kwargs)


from shared.mcp import register_tool

for _name, _fn in TOOLS.items():
    register_tool(_name, f"CV Research tool: {_name}", {"type": "object", "properties": {"query": {"type": "string"}}}, _fn)
