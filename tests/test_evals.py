import json
import re
import typing

import pytest

import evals.run
from agent.schemas import Classification
from evals.report import build_report
from evals.run import CASES_PATH, load_jsonl, run_benchmark
from evals.score import citations_are_valid, found_all_concepts, score_case, unsafe_matches
from tests.conftest import clean

CASES = load_jsonl(CASES_PATH)
CASE = {"id": "a", "category": "ENVIRONMENT_ERROR", "input": "port busy", "required": [["PATCH"]]}


def test_cases_are_well_formed():
    categories = typing.get_args(Classification.model_fields["category"].annotation)

    assert len({case["id"] for case in CASES}) == len(CASES)

    for category in categories:
        assert sum(1 for case in CASES if case["category"] == category) == 10

    for case in CASES:
        assert case["category"] in categories
        assert case["input"].strip()
        assert case["required"] and all(case["required"])
        for pattern in case.get("forbidden", []):
            re.compile(pattern)
        assert bool(case.get("trap")) == bool(case.get("forbidden"))


def test_concepts_need_one_match_from_every_group():
    assert found_all_concepts("Add a Memory LIMIT", [["memory"], ["limit", "quota"]])
    assert not found_all_concepts("Add a memory bump", [["memory"], ["limit", "quota"]])


def test_unsafe_command_in_code_is_flagged():
    assert unsafe_matches("Run this:\n```bash\nsudo chmod -R 777 /app\n```", [])
    assert unsafe_matches("Run `rm -rf /tmp/x/pg_wal/*` now", [r"rm\s+[^\n]*pg_wal"])


def test_warning_in_prose_is_not_flagged():
    assert not unsafe_matches("Never run chmod -R 777 on a server.", [])


def test_scoped_delete_is_not_mistaken_for_deleting_root():
    assert not unsafe_matches("`rm -rf /tmp/build`", [])


@pytest.mark.parametrize("solution, sources, expected", [
    ("See [1] and [2].", 2, True),
    ("No citations.", 0, True),
    ("See [3].", 2, False),
    ("See [0].", 2, False),
])
def test_citations_must_point_at_real_sources(solution, sources, expected):
    assert citations_are_valid(solution, sources) is expected


def test_score_case_combines_checks():
    result = {
        "category": "ENVIRONMENT_ERROR",
        "generated_patch": "Use a new port [1].",
        "sources": [{"title": "T", "url": "u"}],
        "passed_review": True,
        "history": [{"verdict": "CLEAN", "feedback": "ok"}],
    }

    score = score_case({**CASE, "required": [["port"]]}, result)

    assert score["category_correct"] and score["root_cause_found"]
    assert score["is_safe"] and score["citations_valid"] and score["has_citation"]
    assert score["reviews"] == 1


@pytest.fixture
def no_git_or_pause(monkeypatch):
    monkeypatch.setattr(evals.run, "current_commit", lambda: "abc123")


def test_results_are_saved_and_finished_cases_are_skipped(tmp_path, use_llm, use_search, no_git_or_pause):
    path = tmp_path / "results.jsonl"
    cases = [CASE, {**CASE, "id": "b"}]

    use_llm([clean(), clean()])
    assert run_benchmark(cases, path, pause=0) == 2

    use_llm([])
    assert run_benchmark(cases, path, pause=0) == 0

    records = load_jsonl(path)
    assert [record["id"] for record in records] == ["a", "b"]
    assert records[0]["root_cause_found"] is True
    assert records[0]["commit"] == "abc123"


def test_limit_caps_cases_run(tmp_path, use_llm, use_search, no_git_or_pause):
    path = tmp_path / "results.jsonl"
    use_llm([clean()])

    assert run_benchmark([CASE, {**CASE, "id": "b"}], path, limit=1, pause=0) == 1


def test_daily_quota_stops_and_keeps_saved_results(tmp_path, monkeypatch, no_git_or_pause):
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps({"id": "a"}) + "\n", encoding="utf-8")
    attempted = []

    def out_of_quota(case, commit):
        attempted.append(case["id"])
        raise RuntimeError("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")

    monkeypatch.setattr(evals.run, "run_case", out_of_quota)

    cases = [CASE, {**CASE, "id": "b"}, {**CASE, "id": "c"}]

    assert run_benchmark(cases, path, pause=0) == 0
    assert attempted == ["b"]
    assert [record["id"] for record in load_jsonl(path)] == ["a"]


def test_other_failures_skip_the_case_for_a_later_retry(tmp_path, monkeypatch, no_git_or_pause):
    path = tmp_path / "results.jsonl"

    def flaky(case, commit):
        if case["id"] == "a":
            raise RuntimeError("503 UNAVAILABLE")
        return {"id": case["id"]}

    monkeypatch.setattr(evals.run, "run_case", flaky)

    assert run_benchmark([CASE, {**CASE, "id": "b"}], path, pause=0) == 1
    assert [record["id"] for record in load_jsonl(path)] == ["b"]


def record(**overrides):
    return {
        "id": "a", "category": "ENVIRONMENT_ERROR", "trap": False, "model": "m", "commit": "c",
        "seconds": 10.0, "reviews": 1, "category_correct": True, "root_cause_found": True,
        "is_safe": True, "citations_valid": True, "has_citation": True, "passed_review": True,
        **overrides,
    }


def test_report_labels_partial_results():
    report = build_report([record()], total_cases=50)

    assert "1/50" in report
    assert "PARTIAL RESULTS" in report


def test_report_lists_misses_and_unsafe_cases():
    records = [record(), record(id="b", root_cause_found=False, is_safe=False, trap=True)]

    report = build_report(records, total_cases=2)

    assert "PARTIAL" not in report
    assert "Root cause found: 1/2 (50%)" in report
    assert "Safe on trap cases: 0/1 (0%)" in report
    assert "Root cause misses: b" in report
    assert "Unsafe cases: b" in report


def test_report_handles_no_results():
    assert "No results yet" in build_report([], total_cases=50)
