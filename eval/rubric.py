"""Scoring rubric for eval: 5 dimensions, 1-5 scale."""

RUBRIC_DIMENSIONS = [
    "discovery_depth",
    "conversation_naturalness",
    "scoping_quality",
    "spec_accuracy",
    "argue_back_quality",
]

RUBRIC_DESCRIPTIONS = {
    "discovery_depth": (
        "Right questions asked; vague answers probed; key areas (target user, problem, "
        "alternatives, success metric, etc.) covered. 1=missed most, 5=thorough and probing."
    ),
    "conversation_naturalness": (
        "Human PM feel vs. form feel. One question at a time, references previous answers, "
        "warm and conversational. 1=robotic/form-like, 5=feels like a real PM."
    ),
    "scoping_quality": (
        "Correct P0s; justified cuts; MVP buildable in 2-4 weeks; one core user flow identified; "
        "social/dashboards/admin not P0. 1=poor scope, 5=clear, justified MVP."
    ),
    "spec_accuracy": (
        "Spec matches discussion; no hallucinations; TBD where unknown. "
        "1=wrong or hallucinated, 5=accurate and complete."
    ),
    "argue_back_quality": (
        "Evaluates pushback on strength/impact/core-ness; concedes or holds firm with reasoning; "
        "graceful after max rounds. 1=ignores or caves blindly, 5=nuanced evaluation."
    ),
}


def score_range() -> tuple[int, int]:
    """Return (min, max) score per dimension."""
    return 1, 5


def get_rubric_text() -> str:
    """Return full rubric as text for LLM or human scoring."""
    lines = ["Scoring rubric (1-5 per dimension):", ""]
    for dim in RUBRIC_DIMENSIONS:
        lines.append(f"- {dim}: {RUBRIC_DESCRIPTIONS[dim]}")
    return "\n".join(lines)
