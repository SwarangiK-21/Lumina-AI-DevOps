import pytest

from agent.graph import run_agent
from agent.redact import describe, redact_secrets
from evals.redaction import FAKE_SECRETS, REDACTION_CASES_PATH, build_report, check_case
from evals.run import CASES_PATH, load_jsonl
from tests.conftest import clean

CASES = load_jsonl(REDACTION_CASES_PATH)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_labelled_log_is_redacted_correctly(case):
    assert check_case(case)


def test_benchmark_errors_are_left_unchanged():
    benchmark_inputs = [case["input"] for case in load_jsonl(CASES_PATH)]

    _, passed = build_report(CASES, benchmark_inputs)

    assert passed


def test_only_the_secret_is_masked():
    text = f"DATABASE_URL=postgresql://app:{FAKE_SECRETS['DB_PASS']}@db:5432/app refused"

    redacted, found = redact_secrets(text)

    assert redacted == "DATABASE_URL=postgresql://app:[REDACTED URL PASSWORD]@db:5432/app refused"
    assert found == ["URL password"]


def test_a_secret_is_counted_once():
    _, found = redact_secrets(f"Authorization: Bearer {FAKE_SECRETS['JWT']}")

    assert found == ["JWT"]


def test_describe_counts_each_kind():
    assert describe(["secret value", "JWT", "secret value"]) == "2 secret values, 1 JWT"


def test_secrets_never_reach_the_llm_or_search(use_llm, use_search):
    queries = []
    use_search(lambda request: queries.append(request["query"]) or {"results": []})
    llm = use_llm([clean()])
    secret = FAKE_SECRETS["PLAIN_PASS"]

    result = run_agent(f"POSTGRES_PASSWORD={secret}\nFATAL: password authentication failed")

    assert all(secret not in prompt for prompt in llm.prompts)
    assert all(secret not in query for query in queries)
    assert secret not in result["input"]
    assert result["redactions"] == ["secret value"]
