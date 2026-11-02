"""Shared fakes. No test may reach a real LLM or search service."""

import types

import pytest
from langchain_core.messages import AIMessage

import agent.llm
import tools.search
from agent.schemas import Classification, Review

REAL_GET_LLM = agent.llm.get_llm
REAL_GET_SEARCH_TOOL = tools.search.get_search_tool

GOOD_SEARCH = {"results": [{"url": "http://example.test", "title": "Example", "content": "Useful text"}]}


class FakeStructured:
    def __init__(self, llm, schema):
        self.llm = llm
        self.schema = schema

    def invoke(self, prompt):
        self.llm.prompts.append(prompt)
        if self.schema is Classification:
            return Classification(category=self.llm.category)
        return self.llm.reviews.pop(0)


class FakeLLM:
    """Replays scripted reviews and numbers each generated fix."""

    def __init__(self, reviews, category="ENVIRONMENT_ERROR"):
        self.reviews = list(reviews)
        self.category = category
        self.prompts = []
        self.fix_count = 0

    def with_structured_output(self, schema):
        return FakeStructured(self, schema)

    def invoke(self, prompt):
        self.prompts.append(prompt)
        self.fix_count += 1
        return AIMessage(content=[{"type": "text", "text": f"PATCH v{self.fix_count}"}])

    def coder_prompts(self):
        return [p for p in self.prompts if "Senior DevOps Engineer" in p]


def clean():
    return Review(verdict="CLEAN", feedback="Looks good")


def redo(feedback="Use a different port"):
    return Review(verdict="REDO", feedback=feedback)


@pytest.fixture(autouse=True)
def block_real_services(monkeypatch):
    """Fail any test that forgets to fake a service, and skip retry waits."""

    def blocked():
        raise AssertionError("Test tried to create a real service client.")

    monkeypatch.setattr(agent.llm, "get_llm", blocked)
    monkeypatch.setattr(tools.search, "get_search_tool", blocked)
    monkeypatch.setattr(agent.llm.time, "sleep", lambda seconds: None)


@pytest.fixture
def use_llm(monkeypatch):
    def install(reviews, **kwargs):
        llm = FakeLLM(reviews, **kwargs)
        monkeypatch.setattr(agent.llm, "get_llm", lambda: llm)
        return llm

    return install


@pytest.fixture
def use_search(monkeypatch):
    def install(response=GOOD_SEARCH):
        handler = response if callable(response) else (lambda query: response)
        tool = types.SimpleNamespace(invoke=handler)
        monkeypatch.setattr(tools.search, "get_search_tool", lambda: tool)

    install()
    return install
