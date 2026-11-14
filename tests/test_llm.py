import types

import pytest
from langchain_core.messages import AIMessage

import agent.llm
from agent.config import ConfigError
from agent.llm import call_llm, call_llm_structured, invoke_with_retry
from agent.schemas import Review
from tests.conftest import REAL_GET_LLM


class Flaky:
    def __init__(self, message, failures):
        self.message = message
        self.failures = failures
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.message)
        return "ok"


@pytest.mark.parametrize("message", [
    "429 RESOURCE_EXHAUSTED",
    "503 UNAVAILABLE",
    "504 DEADLINE_EXCEEDED",
    "500 INTERNAL",
])
def test_temporary_errors_are_retried(message):
    model = Flaky(message, failures=2)

    assert invoke_with_retry(model, "prompt") == "ok"
    assert model.calls == 3


def test_gives_up_after_three_attempts_and_keeps_real_error():
    model = Flaky("503 UNAVAILABLE", failures=9)

    with pytest.raises(RuntimeError, match="503"):
        invoke_with_retry(model, "prompt")

    assert model.calls == 3


@pytest.mark.parametrize("message", [
    "400 INVALID_ARGUMENT",
    "429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier",
])
def test_permanent_errors_are_not_retried(message):
    model = Flaky(message, failures=9)

    with pytest.raises(RuntimeError):
        invoke_with_retry(model, "prompt")

    assert model.calls == 1


@pytest.mark.parametrize("content", ["text", [{"type": "text", "text": "text"}]])
def test_call_llm_handles_both_reply_formats(monkeypatch, content):
    model = types.SimpleNamespace(invoke=lambda prompt: AIMessage(content=content))
    monkeypatch.setattr(agent.llm, "get_llm", lambda: model)

    assert call_llm("prompt") == "text"


def test_unreadable_structured_reply_fails_closed(monkeypatch):
    structured = types.SimpleNamespace(invoke=lambda prompt: None)
    model = types.SimpleNamespace(with_structured_output=lambda schema: structured)
    monkeypatch.setattr(agent.llm, "get_llm", lambda: model)

    with pytest.raises(ValueError):
        call_llm_structured(Review, "prompt")


def test_missing_api_key_raises_config_error(monkeypatch):
    REAL_GET_LLM.cache_clear()
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ConfigError):
        REAL_GET_LLM()
