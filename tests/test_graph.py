import pytest
from pydantic import ValidationError

from agent.graph import run_agent
from agent.schemas import Classification
from tests.conftest import clean, redo


def test_clean_review_finishes_first_time(use_llm, use_search):
    llm = use_llm([clean()])

    result = run_agent("port busy")

    assert result["passed_review"] is True
    assert result["category"] == "ENVIRONMENT_ERROR"
    assert result["generated_patch"] == "PATCH v1"
    assert len(result["history"]) == 1
    assert len(llm.coder_prompts()) == 1


def test_each_finished_step_is_reported_in_order(use_llm, use_search):
    use_llm([redo(), clean()])
    steps = []

    run_agent("port busy", lambda node, update: steps.append(node))

    assert steps == ["classifier", "researcher", "coder", "reviewer"] + ["researcher", "coder", "reviewer"]


def test_feedback_and_previous_fix_reach_next_attempt(use_llm, use_search):
    llm = use_llm([redo("MARKER"), clean()])

    result = run_agent("port busy")

    first, second = llm.coder_prompts()
    assert "MARKER" not in first
    assert "MARKER" in second
    assert "PATCH v1" in second
    assert result["generated_patch"] == "PATCH v2"
    assert result["passed_review"] is True


def test_feedback_guides_next_search(use_llm, use_search):
    queries = []

    def record(request):
        queries.append(request["query"])
        return {"results": []}

    use_search(record)
    use_llm([redo("MARKER"), clean()])

    run_agent("port busy")

    assert "MARKER" not in queries[0]
    assert "MARKER" in queries[1]


def test_redo_mentioning_clean_does_not_pass(use_llm, use_search):
    use_llm([redo("this is not a CLEAN fix")] * 3)

    result = run_agent("port busy")

    assert result["passed_review"] is False


def test_stops_after_three_reviews(use_llm, use_search):
    llm = use_llm([redo()] * 9)

    result = run_agent("port busy")

    assert len(result["history"]) == 3
    assert result["passed_review"] is False
    assert len(llm.coder_prompts()) == 3


def test_last_verdict_decides_after_failed_review(use_llm, use_search):
    result_llm = use_llm([redo(), redo(), clean()])

    result = run_agent("port busy")

    assert result["passed_review"] is True
    assert result_llm.reviews == []


RISKY_PATCH = "Run:\n```bash\nkubectl --insecure-skip-tls-verify get pods\n```"


def test_risky_fix_is_sent_back_without_an_ai_review(use_llm, use_search):
    llm = use_llm([clean()], patches=[RISKY_PATCH, "Renew the certificate."])

    result = run_agent("x509: certificate has expired")

    first, second = result["history"]
    assert first["checked_by"] == "rules" and first["verdict"] == "REDO"
    assert "insecure-skip-tls-verify" in llm.coder_prompts()[1]
    assert second["checked_by"] == "ai"
    assert result["passed_review"] is True
    assert result["safety_issues"] == []


def test_fix_that_stays_risky_never_passes(use_llm, use_search):
    llm = use_llm([], patches=[RISKY_PATCH] * 3)

    result = run_agent("x509: certificate has expired")

    assert result["passed_review"] is False
    assert len(result["history"]) == 3
    assert "turns off TLS certificate checks" in result["safety_issues"][0]
    assert not [p for p in llm.prompts if "Security Engineer" in p]


def test_invalid_category_is_rejected():
    with pytest.raises(ValidationError):
        Classification(category="Sure! It might be ENVIRONMENT_ERROR")
