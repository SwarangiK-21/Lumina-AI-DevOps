"""
Re-apply the text rules to saved results, with no model or search calls.

Use this after changing a rule in evals/score.py, so old answers are
scored the same way as new ones.

Usage:
    python -m evals.rescore
"""

import argparse
import json
import sys
from pathlib import Path

from evals.run import CASES_PATH, RESULTS_PATH, load_jsonl
from evals.score import score_text


def rescore(records: list[dict], cases: list[dict]) -> list[dict]:
    """Return records with their text-based scores recomputed."""
    cases_by_id = {case["id"]: case for case in cases}
    return [
        {**record, **score_text(cases_by_id[record["id"]], record["solution"], record["sources"])}
        for record in records
    ]


def main(argv: list[str]) -> int:
    """Rescore a results file in place and list what changed."""
    parser = argparse.ArgumentParser(description="Rescore saved LUMINA results.")
    parser.add_argument("--results", type=Path, default=RESULTS_PATH, help="Results file")
    args = parser.parse_args(argv)

    old = load_jsonl(args.results)
    new = rescore(old, load_jsonl(CASES_PATH))

    with args.results.open("w", encoding="utf-8") as file:
        file.writelines(json.dumps(record) + "\n" for record in new)

    for before, after in zip(old, new, strict=True):
        changed = [key for key in after if before.get(key) != after[key]]
        if changed:
            print(f"{after['id']}: {', '.join(changed)} changed")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
