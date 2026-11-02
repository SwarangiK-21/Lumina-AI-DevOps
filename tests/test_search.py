import pytest

from agent.config import MAX_QUERY_CHARS
from tests.conftest import REAL_GET_SEARCH_TOOL
from tools.search import build_search_query, safe_search


def test_results_are_numbered_and_sources_recorded(use_search):
    notes, sources = safe_search("query")

    assert "[1] Example" in notes
    assert sources == [{"title": "Example", "url": "http://example.test"}]


def raise_error(request):
    raise RuntimeError("search is down")


@pytest.mark.parametrize("response", [
    raise_error,
    {"error": "bad request"},
    {"results": []},
    "401 Unauthorized",
])
def test_failed_search_is_labelled_with_no_sources(use_search, response):
    use_search(response)

    notes, sources = safe_search("query")

    assert sources == []
    assert notes.startswith("No web research available")


def test_long_query_is_capped_and_keeps_both_ends():
    query = build_search_query("START " + "x" * 20000 + " END")

    assert len(query) <= MAX_QUERY_CHARS
    assert "START" in query
    assert "END" in query


def test_query_keeps_feedback_within_limit():
    query = build_search_query("x" * 20000, "MARKER")

    assert len(query) <= MAX_QUERY_CHARS
    assert query.endswith("MARKER")


def test_missing_search_key_disables_search(monkeypatch):
    REAL_GET_SEARCH_TOOL.cache_clear()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    assert REAL_GET_SEARCH_TOOL() is None
