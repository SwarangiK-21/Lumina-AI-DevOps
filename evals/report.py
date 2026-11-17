"""
Summarise saved benchmark results.

Usage:
    python -m evals.report
"""

import argparse
import sys
from pathlib import Path
from statistics import median

from evals.run import CASES_PATH, RESULTS_PATH, TRAPS_PATH, load_jsonl, select_cases

METRICS = (
    ("Category correct", "category_correct"),
    ("Root cause found", "root_cause_found"),
    ("Safe", "is_safe"),
    ("Citations valid", "citations_valid"),
    ("Has a citation", "has_citation"),
    ("Passed AI review", "passed_review"),
)


def rate(records: list[dict], field: str) -> str:
    """Format how many records have a true value in field."""
    hits = sum(1 for record in records if record[field])
    return f"{hits}/{len(records)} ({hits / len(records):.0%})"


def build_report(records: list[dict], total_cases: int) -> str:
    """Build the text report for saved results."""
    if not records:
        return "No results yet. Run: python -m evals.run"

    lines = [f"Cases finished: {len(records)}/{total_cases}"]

    if len(records) < total_cases:
        lines.append("PARTIAL RESULTS: these numbers do not represent the full benchmark yet.")

    lines.append(f"Models: {', '.join(sorted({r['model'] for r in records}))}")
    lines.append(f"Commits: {', '.join(sorted({r['commit'] for r in records}))}")
    lines.append("")

    lines.extend(f"{label}: {rate(records, field)}" for label, field in METRICS)

    traps = [record for record in records if record["trap"]]
    if traps:
        lines.append(f"Safe on trap cases: {rate(traps, 'is_safe')}")

    lines.append(f"Median seconds per case: {median(r['seconds'] for r in records):.1f}")
    lines.append(f"Refined at least once: {sum(1 for r in records if r['reviews'] > 1)}/{len(records)}")

    # Older results were saved before the safety rules existed
    if any("safety_redos" in r for r in records):
        lines.append(f"Sent back by safety rules: {sum(1 for r in records if r.get('safety_redos'))}/{len(records)}")

    lines.extend(["", "By category (root cause found):"])
    for category in sorted({record["category"] for record in records}):
        group = [record for record in records if record["category"] == category]
        lines.append(f"  {category}: {rate(group, 'root_cause_found')}")

    misses = [r["id"] for r in records if not r["root_cause_found"]]
    unsafe = [r["id"] for r in records if not r["is_safe"]]
    lines.extend(["", f"Root cause misses: {', '.join(misses) or 'none'}"])
    lines.append(f"Unsafe cases: {', '.join(unsafe) or 'none'}")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """Print the report for a results file."""
    parser = argparse.ArgumentParser(description="Summarise LUMINA benchmark results.")
    parser.add_argument("--traps", action="store_true", help="Report on the trap-only run")
    parser.add_argument("--results", type=Path, help="Results file")
    args = parser.parse_args(argv)

    cases = select_cases(load_jsonl(CASES_PATH), args.traps)
    results = args.results or (TRAPS_PATH if args.traps else RESULTS_PATH)

    print(build_report(load_jsonl(results), len(cases)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
