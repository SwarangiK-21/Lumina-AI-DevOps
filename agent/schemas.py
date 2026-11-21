"""Structured outputs and graph state."""

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


class Classification(BaseModel):
    """The single category that best fits the error"""
    category: Literal[
        "SYNTAX_ERROR",
        "LOGIC_ERROR",
        "ENVIRONMENT_ERROR",
        "DEPENDENCY_ERROR",
        "PERMISSION_ERROR",
    ]


class Review(BaseModel):
    """The reviewer's decision on a proposed fix"""
    verdict: Literal["CLEAN", "REDO"] = Field(
        description="CLEAN if the fix is safe and correct, otherwise REDO"
    )
    feedback: str = Field(
        description="Why the fix passed, or exactly what must change"
    )


class AgentState(TypedDict):
    """State schema for the LUMINA agent"""
    input: str                                          # The error message from user
    category: str                                       # Categorized error type
    research_notes: str                                 # Research findings from web
    sources: list[dict]                                 # Title and URL of each web source
    generated_patch: str                                # Generated solution
    history: Annotated[list[dict], operator.add]        # One verdict/feedback per review
    passed_review: bool                                 # Reviewer approved the final solution
    safety_issues: list[str]                            # Risky commands in the final solution
    redactions: list[str]                               # Kind of each secret masked in the input


def initial_state(error: str, redactions: list[str] | None = None) -> AgentState:
    """Build the starting state for one run. error must already be redacted."""
    return {
        "input": error,
        "redactions": list(redactions or []),
        "category": "",
        "research_notes": "",
        "sources": [],
        "generated_patch": "",
        "history": [],
        "passed_review": False,
        "safety_issues": [],
    }
