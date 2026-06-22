"""Orchestrator constants: research keywords and display names."""

# Friendly display names for each agent (used in error messages).
AGENT_DISPLAY_NAMES: dict[str, str] = {
    "research": "CV Research Agent",
    "solution": "NLP Solution Agent",
    "experiment": "ML Experiment Agent",
}

# ── Research-relevance gate keywords ────────────────────────────────────────

RESEARCH_DOMAINS: list[str] = [
    "computer vision", "image classification", "object detection", "segmentation",
    "medical imaging", "video analytics", "vision-language", "nlp", "llm",
    "natural language", "rag", "retrieval augmented", "prompt engineering",
    "text classification", "summarization", "conversational ai", "information extraction",
    "machine learning", "deep learning", "neural network", "model selection",
    "feature engineering", "time series", "hyperparameter", "experiment design",
    "evaluation strategy", "research", "dataset", "benchmark", "architecture",
    "transformer", "cnn", "diffusion", "gan", "reinforcement learning",
    "paper", "arxiv", "research proposal", "proof of concept",
    # CV/ML implementation keywords
    "ocr", "optical character recognition", "handwriting", "handwritten",
    "text recognition", "document", "receipt", "invoice",
    "image processing", "feature extraction", "pipeline",
    "build", "develop", "create", "implement", "design",
    "solution", "system", "model", "algorithm",
    "training", "inference", "deployment", "preprocessing",
    "augmentation", "transfer learning", "fine-tuning",
    "detection", "recognition", "extraction", "parsing",
    "classification", "regression", "clustering",
    "embedding", "encoder", "decoder",
    "cnn", "rnn", "lstm", "gru", "attention",
    "resnet", "yolo", "efficientnet", "mobilenet",
    "bert", "gpt", "t5", "whisper",
    "pytorch", "tensorflow", "keras", "opencv",
    # Speech/audio
    "speech recognition", "speech-to-text", "text-to-speech", "asr",
    "audio processing", "voice", "acoustic model", "speaker recognition",
]

RESEARCH_ACTIONS: list[str] = [
    "recommend", "compare", "find", "search", "summarize", "analyze", "evaluate",
    "benchmark", "design", "plan", "prototype", "implement", "improve", "optimize",
    "select", "review", "survey", "study", "explore",
    # Implementation actions
    "build", "develop", "create", "set up", "configure", "deploy",
    "train", "fine-tune", "preprocess", "extract", "detect", "recognize",
    "classify", "parse", "process", "generate", "predict",
]

NON_RESEARCH_PATTERNS: list[str] = [
    "weather", "movie", "song", "lyrics", "joke", "meme", "recipe", "restaurant",
    "sports score", "cricket score", "football score", "stock price", "bitcoin price",
    "translate this", "write birthday", "instagram caption", "what is my ip",
    "who are you", "good morning", "good night",
]

AMBIGUOUS_HINTS: list[str] = [
    "model", "accuracy", "dataset", "classification", "training", "prediction",
    "evaluation", "architecture", "experiment",
]

NOT_RESEARCH_RESPONSE: dict = {
    "error": "not_research_query",
    "message": (
        "This query does not appear to be related to AI/ML research. "
        "This system is a Research Assistant that helps with: Computer Vision, "
        "NLP, Machine Learning research — including literature review, dataset "
        "recommendation, model selection, experiment planning, and prototype "
        "guidance. Ask a research-related question."
    ),
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
