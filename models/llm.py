"""LiteLLM wrapper with task-type model routing and retry logic."""

import asyncio
from typing import Any, Literal

import litellm

from config import (
    GROQ_API_KEY,
    MODELS,
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAYS,
    REASONING_EFFORT,
)

# Task types map to model keys in config
TaskType = Literal["conversation", "extraction", "classification", "spec"]


async def llm_call(
    task_type: TaskType,
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> str:
    """
    Call LLM with task-type routing. Uses Groq models via LiteLLM.
    Retries with exponential backoff on failure.
    """
    model = MODELS.get(task_type, MODELS["conversation"])
    api_key = GROQ_API_KEY

    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or environment.")

    extra: dict[str, Any] = {}
    if task_type == "conversation" and "gpt-oss" in model:
        # reasoning_effort is Groq-specific; allow it past LiteLLM's OpenAI param validator
        extra["reasoning_effort"] = REASONING_EFFORT
        extra["allowed_openai_params"] = ["reasoning_effort"]

    last_error: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                api_key=api_key,
                **extra,
                **kwargs,
            )
            choice = response.choices[0]
            if choice.message.content is None:
                raise ValueError("LLM returned empty content")
            return choice.message.content.strip()
        except Exception as e:
            last_error = e
            if attempt < LLM_MAX_RETRIES - 1:
                delay = LLM_RETRY_DELAYS[attempt]
                await asyncio.sleep(delay)

    raise last_error or RuntimeError("LLM call failed after retries")
