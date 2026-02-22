"""Configuration for AI PM Agent. Model names, API config, constants."""

import os
from pathlib import Path

# Load .env if present
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Model routing: task_type -> LiteLLM model name (Mixture of Experts)
MODEL_CONVERSATION = "groq/openai/gpt-oss-20b"  # thinking model on Groq for Discovery + Scoping
MODEL_SPEC = "groq/llama-3.3-70b-versatile"
MODEL_EXTRACTION = "groq/llama-3.1-8b-instant"

MODELS = {
    "conversation": MODEL_CONVERSATION,
    "extraction": MODEL_EXTRACTION,
    "classification": MODEL_EXTRACTION,
    "spec": MODEL_SPEC,
}

# Reasoning config for GPT-OSS-20B (conversation task only)
REASONING_EFFORT = "medium"  # "low" | "medium" | "high"
INCLUDE_REASONING = False  # set True to see reasoning in logs

# Retry config
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAYS = (1, 2, 4)  # seconds, exponential backoff

# Discovery completeness
DISCOVERY_COMPLETENESS_THRESHOLD = 0.75
DISCOVERY_MANDATORY_FIELDS = ("target_user", "core_problem")
DISCOVERY_MIN_TURNS = 4  # minimum user messages before completeness check can pass

# Scoping
MAX_NEGOTIATION_ROUNDS = 3

# Web search
WEB_SEARCH_MAX_RESULTS = 5
