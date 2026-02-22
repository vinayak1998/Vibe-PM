"""User intent classification for discovery review and scoping agreement."""

from prompts.extraction import (
    CLASSIFY_DISCOVERY_REVIEW_PROMPT,
    CLASSIFY_SCOPING_INTENT_PROMPT,
)
from models.llm import llm_call


async def classify_discovery_review(user_response: str) -> bool:
    """
    Did the user confirm the discovery summary (ready to hand off to scoping)?
    Returns True if CONFIRM, False if REVISE or unclear.
    """
    try:
        prompt = CLASSIFY_DISCOVERY_REVIEW_PROMPT.format(
            user_response=user_response.strip()
        )
        raw = await llm_call("classification", [{"role": "user", "content": prompt}])
        return "CONFIRM" in raw.strip().upper()
    except Exception:
        return False


async def classify_scoping_intent(user_response: str) -> str:
    """
    Classify user response to scoping proposal.
    Returns "AGREE", "PUSHBACK", or "QUESTION".
    """
    try:
        prompt = CLASSIFY_SCOPING_INTENT_PROMPT.format(user_response=user_response.strip())
        raw = await llm_call("classification", [{"role": "user", "content": prompt}])
        word = raw.strip().upper()
        if "AGREE" in word:
            return "AGREE"
        if "PUSHBACK" in word:
            return "PUSHBACK"
        if "QUESTION" in word:
            return "QUESTION"
        return "PUSHBACK"  # default to treat as pushback if unclear
    except Exception:
        return "PUSHBACK"
