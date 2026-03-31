"""
LUMINA - AI DevOps Troubleshooter Agent
Built with LangGraph + Google Gemini 2.5 Flash + Tavily Search
"""

import os
import time
from typing import TypedDict, List, Annotated
import operator
from dotenv import load_dotenv

# Import LangChain & LangGraph
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_community.tools.tavily_search import TavilySearchResults
    from langgraph.graph import StateGraph, END
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install langchain langchain-google-genai langchain-community langgraph tavily-python")
    exit(1)

# Load environment variables
load_dotenv()
gemini_key = os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

# Validate API keys
if not gemini_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env")
    print("Create a .env file with: GOOGLE_API_KEY=your_key_here")
    exit(1)

if not tavily_key:
    print("⚠️ WARNING: TAVILY_API_KEY not found in .env")
    print("Search functionality may not work. Add it to .env for full features.")

print("✅ API keys loaded successfully!")

# Initialize LLM and search tool
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_key)
search_tool = TavilySearchResults(k=3)

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    input: str                                           # The error message
    category: str                                        # Error classification
    research_notes: str                                  # Research findings
    generated_patch: str                                 # The solution
    history: Annotated[List[str], operator.add]         # Refinement history
    is_fixed: bool                                       # Final status

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def call_llm_with_retry(prompt: str, max_retries: int = 2) -> str:
    """
    Call Gemini with graceful quota error handling.
    
    Args:
        prompt: The prompt to send to Gemini
        max_retries: Number of retry attempts
        
    Returns:
        The LLM response content
    """
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            error_msg = str(e)
            
            # Check for quota exhaustion
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⚠️ API quota hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(
                        "❌ API Quota Exhausted. "
                        "Upgrade your Google Cloud plan or wait 24 hours."
                    )
            else:
                # Other errors - re-raise immediately
                raise e

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
    print("\n📋 [STEP 1/4] ANALYZING ERROR...")
    
    prompt = f"""You are an expert DevOps error classifier. Analyze this error and categorize it.

ERROR MESSAGE:
{state['input']}

Respond with ONLY the category (no explanation):
- SYNTAX_ERROR
- LOGIC_ERROR
- ENVIRONMENT_ERROR
- DEPENDENCY_ERROR
- PERMISSION_ERROR"""
    
    category = call_llm_with_retry(prompt).strip()
    
    print(f"✓ Classified as: {category}")
    
    return {
        "category": category,
        "research_notes": "",
        "generated_patch": "",
        "is_fixed": False,
        "history": []
    }

def researcher_node(state: AgentState) -> dict:
    """
    Research the error using Tavily search + web browsing.
    """
    print("\n🔍 [STEP 2/4] RESEARCHING SOLUTIONS...")
    
    # Build search query based on category and error
    search_query = f"{state['category']} {state['input']} fix solution 2026"
    
    try:
        search_results = search_tool.invoke({"query": search_query})
        
        # Format research notes
        research_text = "📚 RESEARCH FINDINGS:\n\n"
        for i, result in enumerate(search_results, 1):
            research_text += f"Source {i}: {result.get('url', 'Unknown URL')}\n"
            research_text += f"Content: {result.get('content', 'No content')}\n\n"
        
        print(f"✓ Found {len(search_results)} relevant sources")
        
    except Exception as e:
        research_text = f"⚠️ Search failed: {str(e)}\n Using general knowledge instead."
        print(f"⚠️ Search error: {e}")
    
    # Add previous attempts to context
    if state["history"]:
        previous_context = "\n".join(state["history"])
        research_text = f"PREVIOUS ATTEMPTS:\n{previous_context}\n\n{research_text}"
    
    return {"research_notes": research_text}

def coder_node(state: AgentState) -> dict:
    """
    Generate a solution based on research.
    """
    print("\n💻 [STEP 3/4] GENERATING SOLUTION...")
    
    prompt = f"""You are a Senior DevOps Engineer. Generate a fix for this error.

ERROR CATEGORY: {state['category']}
ERROR MESSAGE: {state['input']}

RESEARCH DATA:
{state['research_notes']}

Provide a comprehensive fix with:

1. ROOT CAUSE
   Explain why this error occurred.

2. SOLUTION (Step-by-step)
   Provide clear, actionable steps. Include code if applicable.

3. VERIFICATION
   How to test that the fix works.

4. PREVENTION
   Best practice to avoid this in the future.

Format clearly with headers. Be concise but complete."""
    
    solution = call_llm_with_retry(prompt)
    
    print("✓ Solution generated")
    
    return {"generated_patch": solution}

def reviewer_node(state: AgentState) -> dict:
    """
    Review the generated solution for safety and completeness.
    """
    print("\n🔐 [STEP 4/4] REVIEWING SOLUTION...")
    
    prompt = f"""You are a Senior QA & Security Engineer. Review this fix.

ORIGINAL ERROR:
{state['input']}

PROPOSED FIX:
{state['generated_patch']}

Evaluate on these criteria:

1. SAFETY: Does it introduce security risks?
2. CORRECTNESS: Does it actually fix the root cause?
3. COMPLETENESS: Does it handle edge cases?
4. BEST_PRACTICES: Does it follow industry standards?

Respond with EXACTLY one of these:

CLEAN: [2-3 sentence explanation why it's safe and correct]

or

REDO: [Explain what's wrong and what to try instead]"""
    
    review = call_llm_with_retry(prompt).strip()
    
    if "CLEAN" in review.upper():
        print("✓ Solution passed review")
    else:
        print("⚠️ Solution needs refinement")
    
    # Return review as a single-item list (operator.add will append it)
    return {"history": [review]}

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_refine(state: AgentState) -> str:
    """
    Decide whether to refine the solution or finish.
    """
    if not state["history"]:
        return "finish"
    
    last_review = state["history"][-1]
    
    # If solution passed review, we're done
    if "CLEAN" in last_review.upper():
        return "finish"
    
    # Prevent infinite loops
    if len(state["history"]) >= 3:
        print("⚠️ Max refinement attempts reached. Finishing with best solution.")
        return "finish"
    
    # Otherwise, try again
    print("🔄 Refining solution based on feedback...\n")
    return "research"

# ============================================================================
# BUILD THE WORKFLOW
# ============================================================================

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classifier", classifier_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("reviewer", reviewer_node)

# Set entry point
workflow.set_entry_point("classifier")

# Define edges
workflow.add_edge("classifier", "researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "reviewer")

# Conditional edge: Should we refine or finish?
workflow.add_conditional_edges(
    "reviewer",
    should_refine,
    {"research": "researcher", "finish": END}
)

# Compile the workflow
app = workflow.compile()

# ============================================================================
# TEST THE AGENT (if run directly)
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 LUMINA - AI DevOps Troubleshooter")
    print("=" * 70)
    
    test_error = "docker: Error response from daemon: Bind for 0.0.0.0:8000 failed."
    
    print(f"\nProcessing error: {test_error}\n")
    
    try:
        result = app.invoke({
            "input": test_error,
            "history": [],
            "category": "",
            "research_notes": "",
            "generated_patch": "",
            "is_fixed": False
        })
        
        print("\n" + "=" * 70)
        print("✅ FINAL SOLUTION")
        print("=" * 70)
        print(f"\nCategory: {result['category']}")
        print(f"Refinement Loops: {len(result['history'])}")
        print(f"\n{result['generated_patch']}")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error during execution:\n{e}")
        print("\nMake sure:")
        print("  1. API keys are set in .env")
        print("  2. All packages are installed: pip install -r requirements.txt")
        print("  3. You have internet connection")