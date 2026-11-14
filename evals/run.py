"""
Run benchmark cases through the agent, one saved result at a time.

Safe to rerun: finished cases are skipped, and the run stops cleanly when
the daily quota runs out, so a free-tier benchmark can finish over several days.

Usage:
    python -m evals.run                 # Run every unfinished case
    python -m evals.run --limit 3       # Run at most 3 cases
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from agent.config import DAILY_QUOTA_MARKER, MODEL_NAME
from agent.graph import run_agent
from evals.score import score_case

CASES_PATH = Path(__file__).parent / "cases.jsonl"
RESULTS_PATH = Path(__file__).parent / "results" / "baseline.jsonl"

logger = logging.getLogger(__name__)


def load_jsonl(path: Path) -> list[dict]:
    """Read a JSON Lines file, or return nothing if it does not exist."""
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def current_commit() -> str:
    """Return the short commit hash, so results can be tied to the code."""
    finished = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return finished.stdout.strip() or "unknown"


def run_case(case: dict, commit: str) -> dict:
    """Run one case and return its saved record."""
    start_time = time.time()
    result = run_agent(case["input"])

    return {
        "id": case["id"],
        "category": case["category"],
        "trap": case.get("trap", False),
        "model": MODEL_NAME,
        "commit": commit,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seconds": round(time.time() - start_time, 1),
        "predicted_category": result["category"],
        "solution": result["generated_patch"],
        **score_case(case, result),
    }


def run_benchmark(cases: list[dict], results_path: Path, limit: int | None = None, pause: float = 5) -> int:
    """Run unfinished cases and return how many finished in this call."""
    finished_ids = {record["id"] for record in load_jsonl(results_path)}
    pending = [case for case in cases if case["id"] not in finished_ids][:limit]
    commit = current_commit()
    completed = 0

    logger.info("%d finished, %d to run now", len(finished_ids), len(pending))
    results_path.parent.mkdir(parents=True, exist_ok=True)

    for case in pending:
        try:
            record = run_case(case, commit)

        except Exception as e:  # noqa: BLE001 - one bad case must not lose the run
            if DAILY_QUOTA_MARKER in str(e):
                logger.warning("Daily quota used up. Rerun after the reset to continue.")
                break

            logger.warning("Case %s failed and will be retried next run: %s", case["id"], str(e)[:150])
            continue

        with results_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")

        completed += 1
        logger.info("Finished %s (%d/%d)", case["id"], len(finished_ids) + completed, len(cases))
        time.sleep(pause)

    return completed


def main(argv: list[str]) -> int:
    """Parse arguments and run the benchmark."""
    parser = argparse.ArgumentParser(description="Run the LUMINA benchmark.")
    parser.add_argument("--limit", type=int, help="Maximum cases to run now")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH, help="Results file")
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    run_benchmark(load_jsonl(CASES_PATH), args.output, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
