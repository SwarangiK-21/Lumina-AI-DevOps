"""
LUMINA UI - AI DevOps Agent
Balanced Modern Design - Professional & Engaging without being overdone
"""

import streamlit as st
from app import app
import time

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="LUMINA - AI DevOps Agent",
    page_icon="🧑🏻‍💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# BALANCED MODERN STYLING
# ============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {
        --primary-blue: #0066cc;
        --primary-blue-dark: #004da6;
        --accent-orange: #ff6b35;
        --success-green: #2dd4bf;
        --bg-light: #f8f6f3;
        --bg-white: #ffffff;
        --text-dark: #1a1a1a;
        --text-gray: #666666;
        --border-light: #e5e0db;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f8f6f3 0%, #ede9e4 50%, #faf8f5 100%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fdfbf8 0%, #f5f1ed 100%);
        border-right: 2px solid var(--border-light);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text-dark);
    }
    
    /* MAIN HEADER */
    .main-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        color: var(--primary-blue);
        margin-bottom: 0;
        letter-spacing: -0.5px;
    }
    
    .subtitle-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        color: var(--text-gray);
        margin-bottom: 2rem;
        letter-spacing: 1px;
    }
    
    /* INPUT AREA */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.95rem !important;
        background: white !important;
        border: 2px solid var(--border-light) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        color: var(--text-dark) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 0 0 4px rgba(0, 102, 204, 0.1) !important;
    }
    
    /* BUTTON */
    .stButton > button {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        padding: 0.8rem 2rem !important;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-blue-dark) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 102, 204, 0.2) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0, 102, 204, 0.3) !important;
    }
    
    /* METRIC CARDS */
    [data-testid="metric-container"] {
        background: white !important;
        border-radius: 14px !important;
        padding: 1.5rem !important;
        border: 2px solid var(--border-light) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="metric-container"]:hover {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 8px 20px rgba(0, 102, 204, 0.1) !important;
        transform: translateY(-3px) !important;
    }
    
    [data-testid="stMetricValue"] {
        color: var(--primary-blue) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-gray) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    
    /* SECTION HEADERS */
    .stMarkdown h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        color: var(--primary-blue) !important;
        margin: 1.5rem 0 1rem 0 !important;
    }
    
    /* EXPANDERS */
    .streamlit-expanderHeader {
        background: white !important;
        border-radius: 10px !important;
        border: 2px solid var(--border-light) !important;
        padding: 1rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        color: var(--primary-blue) !important;
        transition: all 0.3s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.1) !important;
    }
    
    /* CONTAINER */
    .stContainer {
        background: white !important;
        border-radius: 14px !important;
        border: 2px solid var(--border-light) !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }
    
    /* CODE BLOCKS */
    .stCode {
        font-family: 'JetBrains Mono', monospace !important;
        background: #f8f6f3 !important;
        border-left: 4px solid var(--primary-blue) !important;
        border-radius: 10px !important;
        color: var(--text-dark) !important;
    }
    
    /* ALERTS */
    .stAlert {
        border-radius: 10px !important;
        border: 2px solid transparent !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stAlertSuccess"] {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%) !important;
        border-color: var(--success-green) !important;
        color: #166534 !important;
    }
    
    [data-testid="stAlertWarning"] {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%) !important;
        border-color: var(--accent-orange) !important;
        color: #92400e !important;
    }
    
    [data-testid="stAlertInfo"] {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
        border-color: var(--primary-blue) !important;
        color: #1e40af !important;
    }
    
    [data-testid="stAlertError"] {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%) !important;
        border-color: #ef4444 !important;
        color: #7f1d1d !important;
    }
    
    /* DIVIDER */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--border-light), transparent);
        margin: 2rem 0;
    }
    
    /* TEXT */
    p, span {
        color: var(--text-dark) !important;
        font-family: 'Inter', sans-serif;
    }
    
    [data-testid="stMarkdownContainer"] p {
        color: var(--text-dark) !important;
        line-height: 1.6;
    }
    
    [data-testid="stMarkdownContainer"] code {
        font-family: 'JetBrains Mono', monospace !important;
        background: #f8f6f3 !important;
        color: var(--accent-orange) !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 4px !important;
        font-size: 0.9em !important;
    }
    
    /* JSON DISPLAY */
    [data-testid="stJson"] {
        background: white !important;
        border: 2px solid var(--border-light) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        color: var(--text-dark) !important;
    }
    
    /* FOOTER */
    .footer-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: var(--text-gray);
        text-align: center;
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 2px solid var(--border-light);
        letter-spacing: 0.5px;
    }
    
    /* LABEL */
    label {
        color: var(--text-dark) !important;
        font-weight: 600 !important;
    }
    
    /* SIDEBAR HEADINGS */
    [data-testid="stSidebar"] h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--primary-blue) !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 🔧 **How It Works**")
    st.markdown("""
    **LUMINA** analyzes your error in 4 steps:
    
    1. **Analyze** — Categorize the error type
    2. **Research** — Find solutions from real docs
    3. **Generate** — Create a tailored fix
    4. **Review** — Verify safety & completeness
    """)
    
    st.divider()
    
    st.markdown("### ⚡ **Best For**")
    st.markdown("""
    - Docker & Kubernetes errors
    - Python exceptions
    - Node.js issues
    - Cloud deployment problems
    - API integration errors
    """)
    
    st.divider()
    
    st.markdown("### 🛠️ **Tech Stack**")
    st.markdown("""
    **Orchestration:** LangGraph
    
    **LLM:** Google Gemini 2.5 Flash
    
    **Search:** Tavily AI
    """)

# ============================================================================
# MAIN CONTENT
# ============================================================================

# Header
col_header = st.columns([1])
with col_header[0]:
    st.markdown('<h1 class="main-header">🧑🏻‍💻 LUMINA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-text">// AI DevOps Troubleshooter</p>', unsafe_allow_html=True)

st.divider()

# Input Section
col_input, col_status = st.columns([3.5, 1], gap="large")

with col_input:
    st.markdown("### 📋 **Your Error**")
    error_input = st.text_area(
        "Paste your error:",
        placeholder="Paste your error message, stack trace, or logs here...",
        height=200,
        label_visibility="collapsed"
    )

with col_status:
    st.markdown("### **Status**")
    status_container = st.empty()

st.divider()

# Button
col_button = st.columns([1, 2, 1])
with col_button[1]:
    submit_button = st.button(
        "⚡ Analyze & Fix",
        use_container_width=True,
        key="analyze_button"
    )

# ============================================================================
# RESULTS
# ============================================================================

if submit_button:
    if not error_input.strip():
        st.warning("⚠️ Please paste an error first!")
        st.stop()
    
    status_container.info("🔍 Analyzing...")
    
    try:
        start_time = time.time()
        
        result = app.invoke({
            "input": error_input,
            "history": [],
            "category": "",
            "research_notes": "",
            "generated_patch": "",
            "is_fixed": False
        })
        
        elapsed_time = time.time() - start_time
        
        status_container.success(f"✅ Done in {elapsed_time:.1f}s")
        
        st.divider()
        
        # METRICS
        st.markdown("### 📊 **Results**")
        
        m1, m2, m3 = st.columns(3, gap="large")
        
        with m1:
            st.metric(
                "Error Type",
                result.get('category', 'Unknown').replace('_', ' ').title(),
                help="Categorized error type"
            )
        
        with m2:
            refinements = max(0, len(result.get('history', [])) - 1)
            st.metric(
                "Refinements",
                f"{refinements}",
                help="Self-correction loops"
            )
        
        with m3:
            is_clean = "CLEAN" in str(result.get('history', []))
            confidence = "High" if is_clean else "Medium"
            st.metric(
                "Confidence",
                confidence,
                help="Solution verification"
            )
        
        st.divider()
        
        # SOLUTION
        st.markdown("### 🛠️ **Solution**")
        with st.container(border=True):
            st.markdown(result.get("generated_patch", "No solution generated"))
        
        st.divider()
        
        # ANALYSIS
        st.markdown("### 📚 **Analysis**")
        
        c1, c2, c3 = st.columns(3, gap="large")
        
        with c1:
            with st.expander("🧠 **Reasoning**"):
                history = result.get('history', [])
                if history:
                    for i, step in enumerate(history, 1):
                        if "CLEAN" in step:
                            st.success(f"Loop {i}: Verified")
                        elif "REDO" in step:
                            st.warning(f"Loop {i}: Refined")
                        st.caption(step[:100] + "..." if len(step) > 100 else step)
                else:
                    st.info("First attempt - no revisions")
        
        with c2:
            with st.expander("📖 **Research**"):
                research = result.get("research_notes", "No data")
                st.code(research[:400] + "..." if len(research) > 400 else research)
        
        with c3:
            with st.expander("⚙️ **Stats**"):
                st.json({
                    "category": result.get('category'),
                    "refinement_loops": len(result.get('history', [])),
                    "processing_time_ms": int(elapsed_time * 1000)
                })
        
        st.divider()
        
        # NEXT STEPS
        st.markdown("### 🚀 **Next Steps**")
        st.info("✓ Review the solution | ✓ Test in your environment | ✓ Deploy with confidence")
        
    except Exception as e:
        error_str = str(e)
        status_container.error("❌ Error")
        
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            st.error("**API Quota Exceeded**")
            st.markdown("""
            1. Upgrade your Google Cloud plan
            2. Wait 24 hours for free tier reset
            3. Switch to OpenAI or Claude API
            """)
        elif "TAVILY" in error_str:
            st.error("**Search Service Error**")
        elif "No module named" in error_str:
            st.error("**Missing Package**")
            st.markdown("```bash\npip install -r requirements.txt\n```")
        else:
            st.error("**Unexpected Error**")
            with st.expander("Details"):
                st.code(error_str)
        
        st.info("Check: API keys | Packages installed | Internet connection")

# ============================================================================
# FOOTER
# ============================================================================



st.markdown("""
<div class="footer-text">
⚡ LUMINA | AI DevOps Troubleshooter | 2026
</div>
""", unsafe_allow_html=True)