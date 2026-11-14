"""Web search through Tavily."""

import logging
import os
from functools import lru_cache

from langchain_tavily import TavilySearch

from agent.config import MAX_QUERY_CHARS, MAX_SOURCES

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_search_tool() -> TavilySearch | None:
    """Create the search tool the first time it is needed."""
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        logger.warning("TAVILY_API_KEY is not set. Continuing without web search.")
        return None

    return TavilySearch(max_results=MAX_SOURCES, tavily_api_key=api_key)


def build_search_query(error: str, feedback: str = "") -> str:
    """
    Build a search query within Tavily's length limit.

    Keeps both ends of long input, because stack traces can put the
    useful line at either end.
    """
    error = " ".join(error.split())
    room = MAX_QUERY_CHARS - len(feedback) - 1

    if len(error) > room:
        half = room // 2
        error = f"{error[:half]} {error[-half:]}"

    return f"{error} {feedback}".strip()[:MAX_QUERY_CHARS]


def safe_search(query: str) -> tuple[str, list[dict]]:
    """
    Safely perform web search with fallback.

    Args:
        query: Search query string

    Returns:
        Research findings as formatted text, and the sources behind them
    """
    search_tool = get_search_tool()

    if not search_tool:
        return "No web research available: search is not configured.", []

    try:
        response = search_tool.invoke({"query": query})
        results = response.get("results", []) if isinstance(response, dict) else []

        if not results:
            return "No web research available: search returned no results.", []

        research_text = "RESEARCH FINDINGS:\n\n"
        sources = []

        for i, result in enumerate(results, 1):
            url = result.get('url', 'Unknown URL')
            title = result.get('title') or url
            content = result.get('content', 'No content')
            research_text += f"[{i}] {title}\nURL: {url}\nContent: {content}\n\n"
            sources.append({"title": title, "url": url})

        return research_text, sources

    except Exception as e:  # noqa: BLE001 - search is optional, so any failure falls back
        logger.warning("Search failed: %s", str(e)[:100])
        return "No web research available: search failed.", []
