import streamlit.delta_generator
from streamlit.testing.v1 import AppTest

import agent.graph
from agent.config import ConfigError

UI_TIMEOUT_SECONDS = 30


def open_ui(monkeypatch, run_agent):
    monkeypatch.setattr(agent.graph, "run_agent", run_agent)

    # Streamlit's one-time usage warning inspects the whole call stack, which
    # can take minutes under pytest on Windows
    monkeypatch.setattr(streamlit.delta_generator, "_use_warning_has_been_displayed", True)

    return AppTest.from_file("ui.py", default_timeout=UI_TIMEOUT_SECONDS).run()


def run_ui(monkeypatch, run_agent):
    page = open_ui(monkeypatch, run_agent)
    page.text_area[0].set_value("boom").run()
    page.button(key="analyze_button").click().run()

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

    page = run_ui(monkeypatch, lambda error, on_step: agent_result(True, sources))

    assert metrics(page)["AI Review"] == "Passed"
    assert metrics(page)["Web Sources"] == "1"
    assert not [w for w in page.warning if "did not pass" in w.value]
    assert any("Review 1: Passed" in text.value for text in page.markdown)


def test_failed_review_and_missing_sources_show_warnings(monkeypatch):
    page = run_ui(monkeypatch, lambda error, on_step: agent_result(False, []))

    warnings = " ".join(w.value for w in page.warning)

    assert metrics(page)["AI Review"] == "Not passed"
    assert "did not pass AI review" in warnings
    assert "No web sources" in warnings


def test_result_stays_after_another_interaction(monkeypatch):
    page = run_ui(monkeypatch, lambda error, on_step: agent_result(True, []))

    page.text_area[0].set_value("something else").run()

    assert metrics(page)["AI Review"] == "Passed"


def test_empty_input_does_not_run_agent(monkeypatch):
    def fail(error, on_step):
        raise AssertionError("The agent should not run.")

    page = open_ui(monkeypatch, fail)
    page.button(key="analyze_button").click().run()

    assert any("Paste an error" in w.value for w in page.warning)


def test_example_fills_input(monkeypatch):
    page = open_ui(monkeypatch, lambda error, on_step: agent_result(True, []))

    page.button(key="example_Missing Python module").click().run()

    assert "ModuleNotFoundError" in page.text_area[0].value


def test_clear_removes_input_and_result(monkeypatch):
    page = run_ui(monkeypatch, lambda error, on_step: agent_result(True, []))

    page.button(key="clear_button").click().run()

    assert page.text_area[0].value == ""
    assert not page.metric


def test_missing_key_shows_setup_message(monkeypatch):
    def fail(error, on_step):
        raise ConfigError("GOOGLE_API_KEY is not set.")

    page = run_ui(monkeypatch, fail)

    assert any("Setup Needed" in e.value for e in page.error)


def test_daily_quota_shows_reset_message(monkeypatch):
    def fail(error, on_step):
        raise RuntimeError("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")

    page = run_ui(monkeypatch, fail)

    assert any("Daily Gemini Quota" in e.value for e in page.error)


def test_busy_provider_shows_friendly_message(monkeypatch):
    def fail(error, on_step):
        raise RuntimeError("503 UNAVAILABLE")

    page = run_ui(monkeypatch, fail)

    assert any("Busy" in e.value for e in page.error)
