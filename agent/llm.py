"""Gemini access with retries for temporary provider errors."""

import logging
import os
import random
import time
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.config import (
    DAILY_QUOTA_MARKER,
    LLM_TIMEOUT_SECONDS,
    MODEL_NAME,
    RETRYABLE_ERRORS,
    TEMPERATURE,
    ConfigError,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Create the Gemini client the first time it is needed."""
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ConfigError("GOOGLE_API_KEY is not set. Add it to your .env file.")

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key,
        temperature=TEMPERATURE,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=1    # invoke_with_retry handles retries, so the SDK must not multiply them
    )


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
            is_temporary = (
                any(code in error_msg for code in RETRYABLE_ERRORS)
                and DAILY_QUOTA_MARKER not in error_msg
            )

            if is_temporary and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1) + random.uniform(0, 1)
                logger.warning("Temporary provider error. Retrying in %.1fs.", wait_time)
                time.sleep(wait_time)
                continue

            raise


def call_llm(prompt: str) -> str:
    """Call Gemini and return plain text."""
    return invoke_with_retry(get_llm(), prompt).text


def call_llm_structured(schema, prompt: str):
    """Call Gemini and return a validated instance of schema."""
    result = invoke_with_retry(get_llm().with_structured_output(schema), prompt)

    if result is None:
        raise ValueError(f"Model returned no valid {schema.__name__}.")

    return result
