"""
LUMINA command line.

Usage:
    python cli.py "paste your error here"
    python cli.py    # Runs a built-in sample error
"""

import logging
import sys
import time

from agent.graph import run_agent

SAMPLE_ERROR = "docker: Error response from daemon: Bind for 0.0.0.0:8000 failed: port 8000 is already allocated"


def main(argv: list[str]) -> int:
    """Run the agent once and return a process exit code."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Keep library request logs out of the agent's progress output
    logging.getLogger("httpx").setLevel(logging.WARNING)

    error = argv[0] if argv else SAMPLE_ERROR

    try:
        start_time = time.time()
        result = run_agent(error)
        elapsed_time = time.time() - start_time

    except Exception:
        logging.getLogger(__name__).exception("Run failed")
        return 1

    print("\nRESULTS")
    print(f"  Category: {result['category']}")
    print(f"  Reviews: {len(result['history'])}")
    print(f"  Refinements: {len(result['history']) - 1}")
    print(f"  Passed review: {result['passed_review']}")
    print(f"  Sources: {len(result['sources'])}")
    print(f"  Time: {elapsed_time:.1f}s")

    print("\nSOLUTION")
    print("-" * 60)
    print(result["generated_patch"])
    print("-" * 60)

    for i, source in enumerate(result["sources"], 1):
        print(f"[{i}] {source['title']}: {source['url']}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
