import streamlit.delta_generator
from streamlit.testing.v1 import AppTest

import agent.graph
from agent.config import ConfigError

UI_TIMEOUT_SECONDS = 30


def run_ui(monkeypatch, run_agent):
    monkeypatch.setattr(agent.graph, "run_agent", run_agent)

    # Streamlit's one-time usage warning inspects the whole call stack, which
    # can take minutes under pytest on Windows
    monkeypatch.setattr(streamlit.delta_generator, "_use_warning_has_been_displayed", True)

    page = AppTest.from_file("ui.py", default_timeout=UI_TIMEOUT_SECONDS).run()
    page.text_area[0].set_value("boom").run()
    page.button[0].click().run()

    assert not page.exception
    return page


def agent_result(passed, sources):
    verdict = "CLEAN" if passed else "REDO"
    return {
        "category": "ENVIRONMENT_ERROR",
        "generated_patch": "THE FIX",
        "sources": sources,
        "research_notes": "notes",
        "passed_review": passed,
        "history": [{"verdict": verdict, "feedback": "risky step"}],
    }


def metrics(page):
    return {metric.label: metric.value for metric in page.metric}


def test_passed_review_with_sources(monkeypatch):
    sources = [{"title": "Example", "url": "http://example.test"}]

    page = run_ui(monkeypatch, lambda error: agent_result(True, sources))

    assert metrics(page)["AI Review"] == "Passed"
    assert metrics(page)["Web Sources"] == "1"
    assert not [w for w in page.warning if "did not pass" in w.value]


def test_failed_review_and_missing_sources_show_warnings(monkeypatch):
    page = run_ui(monkeypatch, lambda error: agent_result(False, []))

    warnings = " ".join(w.value for w in page.warning)

    assert metrics(page)["AI Review"] == "Not passed"
    assert "did not pass AI review" in warnings
    assert "No web sources" in warnings


def test_missing_key_shows_setup_message(monkeypatch):
    def fail(error):
        raise ConfigError("GOOGLE_API_KEY is not set.")

    page = run_ui(monkeypatch, fail)

    assert any("Setup Needed" in e.value for e in page.error)


def test_daily_quota_shows_reset_message(monkeypatch):
    def fail(error):
        raise RuntimeError("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")

    page = run_ui(monkeypatch, fail)

    assert any("Daily Gemini Quota" in e.value for e in page.error)


def test_busy_provider_shows_friendly_message(monkeypatch):
    def fail(error):
        raise RuntimeError("503 UNAVAILABLE")

    page = run_ui(monkeypatch, fail)

    assert any("Busy" in e.value for e in page.error)
