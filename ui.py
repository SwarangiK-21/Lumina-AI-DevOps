"""LUMINA web interface."""

import logging
import time
from pathlib import Path

import streamlit as st

from agent.config import DAILY_QUOTA_MARKER, MAX_REVIEWS, MODEL_NAME, ConfigError
from agent.graph import run_agent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STYLE_PATH = Path(__file__).parent / "assets" / "style.css"

STEPS = (
    ("classifier", "Classify", "Pick the error type"),
    ("researcher", "Research", "Search the web"),
    ("coder", "Draft", "Write the fix"),
    ("reviewer", "Review", "Safety rules and AI check"),
)

EXAMPLES = {
    "Docker port clash": "docker: Error response from daemon: driver failed programming external connectivity: "
                         "Bind for 0.0.0.0:8080 failed: port is already allocated.",
    "Missing Python module": "ModuleNotFoundError: No module named 'requests'",
    "SSH key rejected": "git@github.com: Permission denied (publickey).\nfatal: Could not read from remote repository.",
}


def use_example(text: str) -> None:
    """Put an example error in the input box."""
    st.session_state.error_input = text


def clear_page() -> None:
    """Empty the input box and remove the last result."""
    st.session_state.error_input = ""
    st.session_state.pop("outcome", None)


def steps_html(active: int, attempt: int) -> str:
    """Build the progress strip. Every step before active is finished."""
    cards = []

    for index, (_, title, detail) in enumerate(STEPS):
        state = "done" if index < active else "active" if index == active else ""
        cards.append(f'<div class="step {state}"><strong>{title}</strong><span>{detail}</span></div>')

    note = f'<p class="attempt">Review asked for changes: attempt {attempt} of {MAX_REVIEWS}</p>' if attempt > 1 else ""
    return f'<div class="steps">{"".join(cards)}</div>{note}'


def analyze(error: str, progress) -> dict:
    """Run the agent with live progress and return what to show."""
    names = [name for name, _, _ in STEPS]
    attempt = 1

    def on_step(node: str, update: dict) -> None:
        nonlocal attempt

        active = names.index(node) + 1
        if node == "reviewer":
            active = 1
            attempt += 1

        progress.markdown(steps_html(active, attempt), unsafe_allow_html=True)

    progress.markdown(steps_html(0, attempt), unsafe_allow_html=True)
    start_time = time.time()

    try:
        return {"result": run_agent(error, on_step), "seconds": time.time() - start_time}

    except Exception as e:
        logger.exception("Run failed")
        return {"failure": e}

    finally:
        progress.empty()


def fix_as_markdown(result: dict) -> str:
    """Build the downloadable copy of the fix and its sources."""
    lines = [result["generated_patch"]]

    if result["sources"]:
        lines.extend(["", "## Sources"])
        lines.extend(f"[{i}] {source['title']}: {source['url']}" for i, source in enumerate(result["sources"], 1))

    return "\n".join(lines)


def show_failure(failure: Exception) -> None:
    """Explain a failed run."""
    message = str(failure)

    if isinstance(failure, ConfigError):
        st.error("**Setup Needed**")
        st.markdown(message)
    elif DAILY_QUOTA_MARKER in message:
        st.error("**Daily Gemini Quota Used**")
        st.markdown("The quota resets daily. Try again after the reset, or upgrade your Gemini plan.")
    elif "RESOURCE_EXHAUSTED" in message or "429" in message:
        st.error("**Gemini Rate Limit Reached**")
        st.markdown("Wait a minute and try again.")
    elif any(code in message for code in ("503", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED")):
        st.error("**Gemini Is Busy Right Now**")
        st.markdown("This is usually temporary. Please try again shortly.")
    elif "No module named" in message:
        st.error("**Missing Package**")
        st.markdown("```bash\npip install -r requirements.txt\n```")
    else:
        st.error("**Unexpected Error**")
        st.markdown("Check your API keys and internet connection.")
        with st.expander("Details"):
            st.code(message)


def show_result(result: dict, seconds: float) -> None:
    """Show the verdict, the fix and the evidence behind it."""
    history = result["history"]
    sources = result["sources"]
    passed = result["passed_review"]

    if result["safety_issues"]:
        issues = "\n".join(f"- {issue}" for issue in result["safety_issues"])
        st.error(f"**Unsafe commands found.** LUMINA could not remove them. Do not run:\n{issues}")
    elif passed:
        st.success("**Passed AI review.** LUMINA has not run this fix, so test it somewhere safe first.")
    elif history:
        st.warning(f"**This fix did not pass AI review.** {history[-1]['feedback']}")

    if not sources:
        st.warning("**No web sources were found.** This fix relies on the model's own knowledge.")

    type_column, review_column, sources_column, time_column = st.columns(4)
    type_column.metric("Error Type", result["category"].replace("_", " ").title())
    review_column.metric(
        "AI Review",
        "Passed" if passed else "Not passed",
        help="A second AI check of the written fix. The fix has not been run.",
    )
    sources_column.metric("Web Sources", len(sources))
    time_column.metric("Time", f"{seconds:.1f}s")

    st.subheader("Proposed fix")

    with st.container(border=True):
        st.markdown(result["generated_patch"])

    st.download_button(
        "Download as Markdown",
        fix_as_markdown(result),
        file_name="lumina-fix.md",
        mime="text/markdown",
        on_click="ignore",
    )

    sources_tab, reviews_tab = st.tabs([f"Sources ({len(sources)})", f"Reviews ({len(history)})"])

    with sources_tab:
        if not sources:
            st.caption("No web sources")
        for i, source in enumerate(sources, 1):
            st.markdown(f"[{i}] [{source['title']}]({source['url']})")

    with reviews_tab:
        for i, review in enumerate(history, 1):
            verdict = "Passed" if review["verdict"] == "CLEAN" else "Changes requested"
            if review.get("checked_by") == "rules":
                verdict += " by safety rules"
            st.markdown(f"**Review {i}: {verdict}**")
            st.caption(review["feedback"])


st.set_page_config(page_title="LUMINA", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.markdown('<p class="brand">LUMINA</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="tagline">Paste an error. Get a researched, reviewed fix to try yourself.</p>',
    unsafe_allow_html=True,
)

error_input = st.text_area(
    "Your error",
    key="error_input",
    placeholder="Paste an error message, stack trace or logs...",
    height=180,
)

st.caption("Sent to Gemini and Tavily, so remove passwords, keys and private data first.")

example_columns = st.columns(len(EXAMPLES))
for column, (label, text) in zip(example_columns, EXAMPLES.items(), strict=True):
    column.button(label, key=f"example_{label}", on_click=use_example, args=(text,), use_container_width=True)

analyze_column, clear_column = st.columns([4, 1])
submitted = analyze_column.button("Analyze error", key="analyze_button", type="primary", use_container_width=True)
clear_column.button("Clear", key="clear_button", on_click=clear_page, use_container_width=True)

progress = st.empty()

if submitted:
    st.session_state.pop("outcome", None)

    if error_input.strip():
        st.session_state.outcome = analyze(error_input, progress)
    else:
        st.warning("Paste an error first.")

outcome = st.session_state.get("outcome")

if outcome:
    st.divider()
    if "failure" in outcome:
        show_failure(outcome["failure"])
    else:
        show_result(outcome["result"], outcome["seconds"])

st.caption(f"LUMINA proposes fixes and never runs them. Model: {MODEL_NAME}")
