"""Discovery completeness checker — pure Python, no LLM."""

from config import DISCOVERY_COMPLETENESS_THRESHOLD, DISCOVERY_MANDATORY_FIELDS

from models.schemas import DiscoverySummary


def _is_filled(value) -> bool:
    """Return True if field has a non-empty value."""
    if value is None:
        return False
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, str):
        return value.strip() != ""
    return True


def is_aspect_filled(summary: DiscoverySummary, aspect_key: str) -> bool:
    """Return True if the given discovery aspect has a non-empty value."""
    value = getattr(summary, aspect_key, None)
    return _is_filled(value)


def check_completeness(summary: DiscoverySummary) -> tuple[float, list[str], bool]:
    """
    Compute completeness score and list of gap fields.
    Returns (score, gaps, is_complete).
    Discovery is complete when score >= 0.75 AND target_user and core_problem are filled.
    """
    fields = [
        "target_user",
        "core_problem",
        "current_alternatives",
        "why_now",
        "feature_wishlist",
        "success_metric",
        "revenue_model",
        "constraints",
    ]
    filled = [f for f in fields if _is_filled(getattr(summary, f, None))]
    gaps = [f for f in fields if f not in filled]
    score = len(filled) / len(fields) if fields else 0.0
    mandatory_met = all(
        _is_filled(getattr(summary, f, None)) for f in DISCOVERY_MANDATORY_FIELDS
    )
    is_complete = score >= DISCOVERY_COMPLETENESS_THRESHOLD and mandatory_met
    return score, gaps, is_complete
