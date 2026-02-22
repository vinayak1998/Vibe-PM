"""DuckDuckGo search for comparable products."""

import asyncio
from typing import Any

from duckduckgo_search import DDGS

from config import WEB_SEARCH_MAX_RESULTS
from models.schemas import DiscoverySummary


def _run_sync_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Run DDGS search in a thread (DDGS is sync)."""
    try:
        results = list(DDGS().text(query, max_results=max_results))
        return results
    except Exception:
        return []


async def search_comparable_products(discovery_summary: DiscoverySummary) -> list[dict[str, Any]]:
    """
    Search for comparable products using target_user and core_problem.
    Returns list of dicts with title, href, body (DuckDuckGo text result format).
    """
    user = discovery_summary.target_user or "users"
    problem = discovery_summary.core_problem or "product"
    query = f"{problem} app for {user}"
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: _run_sync_search(query, WEB_SEARCH_MAX_RESULTS),
    )
    return results
