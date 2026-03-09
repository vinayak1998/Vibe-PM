"""DuckDuckGo search for comparable products."""

import asyncio
import time
import warnings
from typing import Any

# Suppress the package-rename deprecation warning emitted by duckduckgo_search
# (it was renamed to 'ddgs', but ddgs requires Python 3.10+ and this project
# targets Python 3.9, so we stay on duckduckgo_search for now).
warnings.filterwarnings(
    "ignore",
    message=r".*has been renamed.*ddgs.*",
    category=RuntimeWarning,
)

from duckduckgo_search import DDGS

from config import WEB_SEARCH_MAX_RESULTS
from models.schemas import DiscoverySummary

# Retry config: DuckDuckGo rate-limits after a few calls in quick succession.
# Later scenarios in a run (arguer, pivoter) frequently hit empty results without this.
_SEARCH_MAX_ATTEMPTS = 3
_SEARCH_RETRY_DELAY_S = 5


def _run_sync_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Run DDGS search in a thread (DDGS is sync), with retry on empty/error."""
    for attempt in range(_SEARCH_MAX_ATTEMPTS):
        try:
            results = list(DDGS().text(query, max_results=max_results))
            if results:
                return results
        except Exception:
            pass
        if attempt < _SEARCH_MAX_ATTEMPTS - 1:
            time.sleep(_SEARCH_RETRY_DELAY_S)
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
