"""
LUMINA - AI DevOps Troubleshooter Agent
Built with LangGraph + Google Gemini + Tavily Search
"""

import os
import sys
import time
import random
from typing import TypedDict, List, Annotated, Literal
import operator

# ============================================================================
# DEPENDENCY IMPORTS WITH CLEAR ERROR HANDLING
# ============================================================================

try:
    from dotenv import load_dotenv
    print("✅ dotenv loaded")
except ImportError:
    print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    exit(1)

try:
    from pydantic import BaseModel, Field
    print("✅ Pydantic loaded")
except ImportError:
    print("❌ pydantic not installed. Run: pip install -r requirements.txt")
    exit(1)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("✅ Google Gemini API loaded")
except ImportError:
    print("❌ langchain-google-genai not installed. Run: pip install langchain-google-genai")
    exit(1)

try:
    from langchain_tavily import TavilySearch
    print("✅ Tavily Search loaded")
except ImportError:
    print("❌ langchain-tavily not installed. Run: pip install langchain-tavily")
    exit(1)

try:
    from langgraph.graph import StateGraph, END, START
    print("✅ LangGraph loaded")
except ImportError:
    print("❌ langgraph not installed. Run: pip install langgraph")
    exit(1)

print("\n✅ All dependencies loaded successfully!\n")

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================

load_dotenv()

gemini_key = os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

if not gemini_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
    print("Create a .env file with: GOOGLE_API_KEY=your_key_here")
    exit(1)

if not tavily_key:
    print("⚠️ WARNING: TAVILY_API_KEY not found. Search may not work optimally.")
    print("Add to .env: TAVILY_API_KEY=your_key_here")

print("✅ API keys loaded successfully!\n")

# ============================================================================
# SETTINGS
# ============================================================================

MAX_REVIEWS = 3          # Total review rounds before the run stops
MAX_SOURCES = 3          # Web sources used per search
MAX_QUERY_CHARS = 400    # Tavily rejects or degrades longer queries

# Provider errors that are usually temporary and worth retrying
RETRYABLE_ERRORS = (
    "429", "RESOURCE_EXHAUSTED",
    "503", "UNAVAILABLE",
    "504", "DEADLINE_EXCEEDED",
    "INTERNAL",
)

# ============================================================================
# INITIALIZE LLM & SEARCH TOOLS
# ============================================================================

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=gemini_key,
        temperature=0.7,
        timeout=30
    )
    print("✅ Google Gemini initialized")
except Exception as e:
    print(f"❌ Failed to initialize Gemini: {e}")
    exit(1)

try:
    search_tool = TavilySearch(max_results=MAX_SOURCES, tavily_api_key=tavily_key)
    print("✅ Tavily Search initialized\n")
except Exception as e:
    print(f"⚠️ Tavily Search initialization warning: {e}")
    search_tool = None
    print("⚠️ Continuing without search capability\n")

# ============================================================================
# STRUCTURED OUTPUTS
# ============================================================================

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

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State schema for the LUMINA agent"""
    input: str                                          # The error message from user
    category: str                                       # Categorized error type
    research_notes: str                                 # Research findings from web
    sources: List[dict]                                 # Title and URL of each web source
    generated_patch: str                                # Generated solution
    history: Annotated[List[dict], operator.add]        # One verdict/feedback per review
    passed_review: bool                                 # Reviewer approved the final solution


def initial_state(error: str) -> AgentState:
    """Build the starting state for one run."""
    return {
        "input": error,
        "category": "",
        "research_notes": "",
        "sources": [],
        "generated_patch": "",
        "history": [],
        "passed_review": False
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def invoke_with_retry(runnable, prompt: str, max_retries: int = 3):
    """
    Invoke a model with exponential backoff on temporary provider errors.

    Args:
        runnable: The model or structured-output model to call
        prompt: The prompt to send
        max_retries: Maximum number of attempts

    Returns:
        The model's response
    """
    for attempt in range(max_retries):
        try:
            return runnable.invoke(prompt)

        except Exception as e:
            error_msg = str(e)
            is_temporary = any(code in error_msg for code in RETRYABLE_ERRORS)

            if is_temporary and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1) + random.uniform(0, 1)
                print(f"⚠️ Temporary provider error. Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                continue

            raise


def call_llm(prompt: str) -> str:
    """Call Gemini and return plain text."""
    return invoke_with_retry(llm, prompt).text


def call_llm_structured(schema, prompt: str):
    """Call Gemini and return a validated instance of schema."""
    result = invoke_with_retry(llm.with_structured_output(schema), prompt)

    if result is None:
        raise ValueError(f"Model returned no valid {schema.__name__}.")

    return result


def build_search_query(error: str, feedback: str = "") -> str:
    """
    Build a search query within Tavily's length limit.

    Keeps both ends of long input, because stack traces can put the
    useful line at either end.
    """
    error = " ".join(error.split())
    room = MAX_QUERY_CHARS - len(feedback) - 1

    if len(error) > room:
        half = room // 2
        error = f"{error[:half]} {error[-half:]}"

    return f"{error} {feedback}".strip()[:MAX_QUERY_CHARS]


def safe_search(query: str) -> tuple[str, List[dict]]:
    """
    Safely perform web search with fallback.

    Args:
        query: Search query string

    Returns:
        Research findings as formatted text, and the sources behind them
    """
    if not search_tool:
        return "No web research available: search is not configured.", []

    try:
        response = search_tool.invoke({"query": query})
        results = response.get("results", []) if isinstance(response, dict) else []

        if not results:
            return "No web research available: search returned no results.", []

        research_text = "RESEARCH FINDINGS:\n\n"
        sources = []

        for i, result in enumerate(results, 1):
            url = result.get('url', 'Unknown URL')
            title = result.get('title') or url
            content = result.get('content', 'No content')
            research_text += f"[{i}] {title}\nURL: {url}\nContent: {content}\n\n"
            sources.append({"title": title, "url": url})

        return research_text, sources

    except Exception as e:
        print(f"⚠️ Search failed: {str(e)[:100]}")
        return "No web research available: search failed.", []

# ============================================================================
# AGENT NODES
# ============================================================================

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
    print("\n" + "="*60)
    print("📋 [STEP 1/4] ANALYZING ERROR")
    print("="*60)

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
    print(f"✓ Error Category: {category}")

    return {"category": category}

def researcher_node(state: AgentState) -> dict:
    """
    Research the error using web search, guided by any reviewer feedback.
    """
    print("\n" + "="*60)
    print("🔍 [STEP 2/4] RESEARCHING SOLUTIONS")
    print("="*60)

    feedback = state["history"][-1]["feedback"][:120] if state["history"] else ""
    search_query = build_search_query(state["input"], feedback)

    research_notes, sources = safe_search(search_query)
    print(f"✓ Research complete ({len(sources)} sources)")

    return {"research_notes": research_notes, "sources": sources}

def coder_node(state: AgentState) -> dict:
    """
    Generate a solution based on research, error analysis and past reviews.
    """
    print("\n" + "="*60)
    print("💻 [STEP 3/4] GENERATING SOLUTION")
    print("="*60)

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
    print("✓ Solution generated")

    return {"generated_patch": solution}

def reviewer_node(state: AgentState) -> dict:
    """
    Review the generated solution for safety and correctness.
    """
    print("\n" + "="*60)
    print("🔐 [STEP 4/4] REVIEWING SOLUTION")
    print("="*60)

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

    if passed:
        print("✓ Solution passed review")
    else:
        print("⚠️ Solution needs refinement")

    return {
        "history": [{"verdict": review.verdict, "feedback": review.feedback}],
        "passed_review": passed
    }

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_refine(state: AgentState) -> str:
    """
    Determine whether to refine the solution or finish.
    """
    if state["passed_review"]:
        return "finish"

    # Prevent infinite loops
    if len(state["history"]) >= MAX_REVIEWS:
        print("\n⚠️ Review limit reached. Finishing without passing review.")
        return "finish"

    # Otherwise, refine
    print("\n🔄 Refining solution based on feedback...\n")
    return "research"

# ============================================================================
# BUILD WORKFLOW
# ============================================================================

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classifier", classifier_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("reviewer", reviewer_node)

# Define edges
workflow.add_edge(START, "classifier")
workflow.add_edge("classifier", "researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "reviewer")

# Conditional edge for refinement
workflow.add_conditional_edges(
    "reviewer",
    should_refine,
    {
        "research": "researcher",
        "finish": END
    }
)

# Compile workflow
app = workflow.compile()

print("✅ Workflow compiled successfully!\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 LUMINA - AI DevOps Troubleshooter")
    print("="*60 + "\n")

    # Test error
    test_error = "docker: Error response from daemon: Bind for 0.0.0.0:8000 failed: port 8000 is already allocated"

    print(f"Testing with error:\n{test_error}\n")

    try:
        start_time = time.time()

        # Invoke the agent
        final_state = app.invoke(initial_state(test_error))

        elapsed_time = time.time() - start_time

        # Display results
        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE")
        print("="*60)

        print(f"\n📊 RESULTS:")
        print(f"  Category: {final_state['category']}")
        print(f"  Reviews: {len(final_state['history'])}")
        print(f"  Refinements: {len(final_state['history']) - 1}")
        print(f"  Passed review: {final_state['passed_review']}")
        print(f"  Sources: {len(final_state['sources'])}")
        print(f"  Time: {elapsed_time:.1f}s")

        print(f"\n🛠️ FINAL SOLUTION:")
        print("-" * 60)
        print(final_state["generated_patch"])
        print("-" * 60)

        print(f"\n✅ Agent run completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
