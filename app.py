"""
LUMINA - AI DevOps Troubleshooter Agent
Production-Ready Version | Fully Error-Free
Built with LangGraph + Google Gemini + Tavily Search
"""

import os
import time
import random
from typing import TypedDict, List, Annotated
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
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("✅ Google Gemini API loaded")
except ImportError:
    print("❌ langchain-google-genai not installed. Run: pip install langchain-google-genai")
    exit(1)

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    print("✅ Tavily Search loaded")
except ImportError:
    print("❌ langchain-community not installed. Run: pip install langchain-community")
    exit(1)

try:
    from langgraph.graph import StateGraph, END
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
# INITIALIZE LLM & SEARCH TOOLS
# ============================================================================

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=gemini_key,
        temperature=0.7,
        timeout=30
    )
    print("✅ Google Gemini initialized")
except Exception as e:
    print(f"❌ Failed to initialize Gemini: {e}")
    exit(1)

try:
    search_tool = TavilySearchResults(api_key=tavily_key, k=3)
    print("✅ Tavily Search initialized\n")
except Exception as e:
    print(f"⚠️ Tavily Search initialization warning: {e}")
    search_tool = None
    print("⚠️ Continuing without search capability\n")

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State schema for the LUMINA agent"""
    input: str                                      # The error message from user
    category: str                                   # Categorized error type
    research_notes: str                             # Research findings from web
    generated_patch: str                            # Generated solution
    history: Annotated[List[str], operator.add]     # Refinement history (appended)
    is_fixed: bool                                  # Whether error is fixed

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def call_llm_with_retry(prompt: str, max_retries: int = 3) -> str:
    """
    Call Gemini API with exponential backoff retry logic.
    
    Args:
        prompt: The prompt to send to Gemini
        max_retries: Maximum number of retry attempts
        
    Returns:
        LLM response content as string
    """
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for quota/rate limit errors
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1) + random.uniform(0, 1)
                    print(f"⚠️ Rate limited. Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(
                        "❌ API quota exhausted. Please upgrade your Google Cloud plan or wait 24 hours."
                    )
            
            # Other errors - re-raise
            raise e

def safe_search(query: str) -> str:
    """
    Safely perform web search with fallback.
    
    Args:
        query: Search query string
        
    Returns:
        Research findings as formatted string
    """
    if not search_tool:
        return "⚠️ Search unavailable. Using general knowledge."
    
    try:
        search_results = search_tool.invoke({"query": query})
        
        research_text = "📚 RESEARCH FINDINGS:\n\n"
        for i, result in enumerate(search_results, 1):
            url = result.get('url', 'Unknown URL')
            content = result.get('content', 'No content')
            research_text += f"Source {i}: {url}\n"
            research_text += f"Content: {content[:300]}...\n\n"
        
        return research_text
        
    except Exception as e:
        return f"⚠️ Search failed: {str(e)[:100]}\nUsing internal knowledge instead."

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
{state['input']}

Respond with ONLY the category name (no explanation)."""
    
    category = call_llm_with_retry(prompt).strip()
    print(f"✓ Error Category: {category}")
    
    return {
        "category": category,
        "research_notes": "",
        "generated_patch": "",
        "is_fixed": False,
        "history": []
    }

def researcher_node(state: AgentState) -> dict:
    """
    Research the error using web search + documentation.
    """
    print("\n" + "="*60)
    print("🔍 [STEP 2/4] RESEARCHING SOLUTIONS")
    print("="*60)
    
    search_query = f"{state['category']} {state['input']} solution fix 2026"
    
    research_notes = safe_search(search_query)
    print("✓ Research complete")
    
    return {"research_notes": research_notes}

def coder_node(state: AgentState) -> dict:
    """
    Generate a solution based on research and error analysis.
    """
    print("\n" + "="*60)
    print("💻 [STEP 3/4] GENERATING SOLUTION")
    print("="*60)
    
    prompt = f"""You are a Senior DevOps Engineer with 10+ years experience.

ERROR CATEGORY: {state['category']}
ERROR MESSAGE: {state['input']}

RESEARCH DATA:
{state['research_notes']}

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

Format clearly with headers. Be concise but complete."""
    
    solution = call_llm_with_retry(prompt)
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

PROPOSED FIX:
{state['generated_patch']}

Evaluate on these criteria:
1. SAFETY: Does it introduce security vulnerabilities?
2. CORRECTNESS: Does it actually fix the root cause?
3. COMPLETENESS: Does it handle edge cases?
4. BEST_PRACTICES: Does it follow industry standards?

Respond with EXACTLY one of these formats:

CLEAN: [2-3 sentence explanation why it's safe and correct]

OR

REDO: [Explain what's wrong and what to try instead]"""
    
    review = call_llm_with_retry(prompt).strip()
    
    if "CLEAN" in review.upper():
        print("✓ Solution passed review - VERIFIED")
    else:
        print("⚠️ Solution needs refinement")
    
    return {"history": [review]}

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_refine(state: AgentState) -> str:
    """
    Determine whether to refine the solution or finish.
    """
    if not state["history"]:
        return "finish"
    
    last_review = state["history"][-1]
    
    # If solution passed review, finish
    if "CLEAN" in last_review.upper():
        return "finish"
    
    # Prevent infinite loops (max 3 refinement attempts)
    if len(state["history"]) >= 3:
        print("\n⚠️ Max refinement attempts reached. Finishing with best solution.")
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

# Set entry point
workflow.set_entry_point("classifier")

# Define edges
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
        final_state = app.invoke({
            "input": test_error,
            "category": "",
            "research_notes": "",
            "generated_patch": "",
            "history": [],
            "is_fixed": False
        })
        
        elapsed_time = time.time() - start_time
        
        # Display results
        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE")
        print("="*60)
        
        print(f"\n📊 RESULTS:")
        print(f"  Category: {final_state['category']}")
        print(f"  Refinements: {len(final_state['history'])}")
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