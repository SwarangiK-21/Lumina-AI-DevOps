"""The four agent steps and the routing decision."""

import logging

from agent.config import MAX_FEEDBACK_QUERY_CHARS, MAX_REVIEWS
from agent.llm import call_llm, call_llm_structured
from agent.schemas import AgentState, Classification, Review
from tools.search import build_search_query, safe_search

logger = logging.getLogger(__name__)


def classifier_node(state: AgentState) -> dict:
    """
    Classify the error into a category.

    Categories:
    - SYNTAX_ERROR: Invalid code syntax
    - LOGIC_ERROR: Code works but produces wrong behavior
    - ENVIRONMENT_ERROR: Docker, K8s, network, config issues
    - DEPENDENCY_ERROR: Missing packages, version conflicts
    - PERMISSION_ERROR: Access/auth issues
    """
    logger.info("Step 1/4: classifying error")

    prompt = f"""You are an expert DevOps error classifier.

Categorize this error into ONE of these types:
- SYNTAX_ERROR (Invalid code syntax, typos)
- LOGIC_ERROR (Wrong behavior, incorrect logic)
- ENVIRONMENT_ERROR (Docker, Kubernetes, Network, Config)
- DEPENDENCY_ERROR (Missing packages, version conflicts)
- PERMISSION_ERROR (Access denied, authentication issues)

ERROR MESSAGE:
{state['input']}"""

    category = call_llm_structured(Classification, prompt).category
    logger.info("Error category: %s", category)

    return {"category": category}


def researcher_node(state: AgentState) -> dict:
    """
    Research the error using web search, guided by any reviewer feedback.
    """
    logger.info("Step 2/4: researching solutions")

    feedback = ""
    if state["history"]:
        feedback = state["history"][-1]["feedback"][:MAX_FEEDBACK_QUERY_CHARS]

    search_query = build_search_query(state["input"], feedback)

    research_notes, sources = safe_search(search_query)
    logger.info("Research complete: %d sources", len(sources))

    return {"research_notes": research_notes, "sources": sources}


def coder_node(state: AgentState) -> dict:
    """
    Generate a solution based on research, error analysis and past reviews.
    """
    logger.info("Step 3/4: generating solution")

    revision = ""
    if state["history"]:
        revision = f"""
PREVIOUS ATTEMPT:
{state['generated_patch']}

REVIEWER FEEDBACK (you must address this):
{state['history'][-1]['feedback']}
"""

    prompt = f"""You are a Senior DevOps Engineer with 10+ years experience.

ERROR CATEGORY: {state['category']}
ERROR MESSAGE: {state['input']}

RESEARCH DATA:
{state['research_notes']}
{revision}
Generate a comprehensive fix with the following sections:

1. ROOT CAUSE
   Explain why this error occurred in simple terms.

2. SOLUTION (Step-by-step)
   Provide clear, actionable steps to fix the problem.
   Include code if applicable.

3. VERIFICATION
   How to test that the fix works.

4. PREVENTION
   Best practice to avoid this error in the future.

Cite research with its number, like [1], where it supports a claim.
Only cite numbers listed in RESEARCH DATA, and never invent sources.

Format clearly with headers. Be concise but complete."""

    solution = call_llm(prompt)
    logger.info("Solution generated")

    return {"generated_patch": solution}


def reviewer_node(state: AgentState) -> dict:
    """
    Review the generated solution for safety and correctness.
    """
    logger.info("Step 4/4: reviewing solution")

    prompt = f"""You are a Senior QA & Security Engineer.

Review this fix for safety and correctness.

ORIGINAL ERROR:
{state['input']}

RESEARCH DATA:
{state['research_notes']}

PROPOSED FIX:
{state['generated_patch']}

Evaluate on these criteria:
1. SAFETY: Does it introduce security vulnerabilities?
2. CORRECTNESS: Does it actually fix the root cause?
3. COMPLETENESS: Does it handle edge cases?
4. BEST_PRACTICES: Does it follow industry standards?

Use verdict CLEAN only if the fix meets all four criteria. Otherwise use
verdict REDO and say exactly what must change."""

    review = call_llm_structured(Review, prompt)
    passed = review.verdict == "CLEAN"

    logger.info("Review verdict: %s", review.verdict)

    return {
        "history": [{"verdict": review.verdict, "feedback": review.feedback}],
        "passed_review": passed
    }


def should_refine(state: AgentState) -> str:
    """
    Determine whether to refine the solution or finish.
    """
    if state["passed_review"]:
        return "finish"

    # Prevent infinite loops
    if len(state["history"]) >= MAX_REVIEWS:
        logger.warning("Review limit reached. Finishing without passing review.")
        return "finish"

    logger.info("Refining solution based on feedback")
    return "research"
