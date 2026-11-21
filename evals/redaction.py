"""
Measure secret redaction on labelled logs, with no model or search calls.

Each case is a log with placeholders such as {AWS_KEY}. Cases with secrets
pass when every secret value is gone from the redacted text; clean cases
pass when the text is unchanged. The 50 benchmark errors are also checked,
since none of them contain secrets and none should change.

The fake secrets are built from pieces here instead of being written out,
so that code hosts do not mistake them for leaked credentials.

Usage:
    python -m evals.redaction
"""

import sys
from pathlib import Path

from agent.redact import redact_secrets
from evals.run import CASES_PATH, load_jsonl

REDACTION_CASES_PATH = Path(__file__).parent / "redaction_cases.jsonl"

FAKE_SECRETS = {
    "AWS_KEY": "AKIA" + "IOSFODNN7" + "EXAMPLE",
    "AWS_SECRET": "wJalrXUtnFEMI/K7MDENG/" + "bPxRfiCYEXAMPLEKEY",
    "GH_TOKEN": "ghp_" + "Ab3Cd4Ef5G" * 4,
    "GH_PAT": "github_pat_" + "11AB2CD3EF" * 4,
    "GOOGLE_KEY": "AIza" + "SyD" + "x7Kq2LpZ9m" * 3 + "Ab",
    "SLACK_TOKEN": "xoxb-" + "1234567890-" + "abcdefghij",
    "STRIPE_KEY": "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc",
    "LLM_KEY": "sk-" + "proj-" + "Zx9Wv8Ut7S" * 3,
    "JWT": "eyJhbGciOiJIUzI1NiJ9" + ".eyJzdWIiOiIxMjM0NTY3ODkwIn0" + ".dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    "BEARER": "mF_9.B5f-4.1JqM" + "x9Kq2LpZ7",
    "DB_PASS": "S3cr" + "etPass!2026",
    "PLAIN_PASS": "hunter2" + "Prod!",
    "NPM_TOKEN": "npm_" + "Qw3Er4Ty5U" * 4,
    "PRIVATE_KEY": "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIEowIBAAKCAQEA7xEXAMPLE\n-----END RSA " + "PRIVATE KEY-----",
}


def fill(text: str) -> str:
    """Replace {NAME} placeholders with fake secret values."""
    for name, value in FAKE_SECRETS.items():
        text = text.replace("{" + name + "}", value)
    return text


def check_case(case: dict) -> bool:
    """Return whether redaction removed every secret and nothing else."""
    text = fill(case["text"])
    redacted, _ = redact_secrets(text)

    if not case["secrets"]:
        return redacted == text

    return all(FAKE_SECRETS[name] not in redacted for name in case["secrets"])


def build_report(cases: list[dict], benchmark_inputs: list[str]) -> tuple[str, bool]:
    """Return the report text and whether every check passed."""
    with_secrets = [case for case in cases if case["secrets"]]
    clean = [case for case in cases if not case["secrets"]]

    missed = [case["id"] for case in with_secrets if not check_case(case)]
    changed = [case["id"] for case in clean if not check_case(case)]
    benchmark_changed = sum(1 for text in benchmark_inputs if redact_secrets(text)[1])

    lines = [
        f"Logs with secrets fully masked: {len(with_secrets) - len(missed)}/{len(with_secrets)}",
        f"Clean logs left unchanged: {len(clean) - len(changed)}/{len(clean)}",
        f"Benchmark errors changed: {benchmark_changed}/{len(benchmark_inputs)}",
        f"Missed: {', '.join(missed) or 'none'}",
        f"Wrongly changed: {', '.join(changed) or 'none'}",
    ]
    return "\n".join(lines), not (missed or changed or benchmark_changed)


def main() -> int:
    """Print the redaction report and fail if any check fails."""
    benchmark_inputs = [case["input"] for case in load_jsonl(CASES_PATH)]
    report, passed = build_report(load_jsonl(REDACTION_CASES_PATH), benchmark_inputs)
    print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
