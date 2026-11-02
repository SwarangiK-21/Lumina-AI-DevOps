"""Settings shared across the agent."""

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"
TEMPERATURE = 0.7
LLM_TIMEOUT_SECONDS = 30

MAX_REVIEWS = 3          # Total review rounds before the run stops
MAX_SOURCES = 3          # Web sources used per search
MAX_QUERY_CHARS = 400    # Tavily rejects or degrades longer queries
MAX_FEEDBACK_QUERY_CHARS = 120

# Provider errors that are usually temporary and worth retrying
RETRYABLE_ERRORS = (
    "429", "RESOURCE_EXHAUSTED",
    "503", "UNAVAILABLE",
    "504", "DEADLINE_EXCEEDED",
    "INTERNAL",
)

# Appears in quota errors that last until the daily reset, so retrying is pointless
DAILY_QUOTA_MARKER = "PerDay"


class ConfigError(Exception):
    """Required configuration is missing."""
