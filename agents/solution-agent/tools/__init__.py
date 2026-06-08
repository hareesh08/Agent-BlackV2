from .paper_search import search_papers
from .summarizer import summarize_paper
from .nlp_datasets import find_nlp_datasets
from .rag_design import rag_design
from .llm_benchmark import llm_benchmark
from .citation_generator import citation_generator
from .prompt_optimizer import prompt_optimizer
from .information_extraction import information_extraction
from .eval_metrics import eval_metric_advisor_nlp
from .gap_analysis import analyze_gaps
from .solution_recommendation import solution_recommendation
from .prototype_guidance import prototype_guidance
from .experiment_planner import experiment_planner

TOOLS = {
    "search_papers": search_papers,
    "summarize_paper": summarize_paper,
    "find_nlp_datasets": find_nlp_datasets,
    "rag_design": rag_design,
    "llm_benchmark": llm_benchmark,
    "citation_generator": citation_generator,
    "prompt_optimizer": prompt_optimizer,
    "information_extraction": information_extraction,
    "evaluation_metric_tool": eval_metric_advisor_nlp,
    "eval_metric_advisor": eval_metric_advisor_nlp,
    "analyze_gaps": analyze_gaps,
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
    register_tool(_name, f"NLP tool: {_name}", {"type": "object", "properties": {"query": {"type": "string"}}}, _fn)
