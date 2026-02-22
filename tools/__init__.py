"""Tools: completeness checker, extraction, intent, web search, templates."""

from tools.completeness import check_completeness
from tools.extraction import extract_discovery_summary, extract_scoping_output
from tools.intent import classify_discovery_review, classify_scoping_intent
from tools.web_search import search_comparable_products
from tools.templates import SPEC_TEMPLATE  # noqa: F401 - re-export

__all__ = [
    "check_completeness",
    "extract_discovery_summary",
    "extract_scoping_output",
    "classify_discovery_review",
    "classify_scoping_intent",
    "search_comparable_products",
    "SPEC_TEMPLATE",
]
