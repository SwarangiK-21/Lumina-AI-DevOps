"""
Mask secrets in pasted text before it is sent to the LLM or search API.

Each rule replaces only the secret value with a labelled placeholder, so
the rest of the error stays readable. Rules are checked in order, from the
most specific formats to generic "password=..." pairs.
"""

import re

# Each rule is a label and a pattern. When the pattern has a group named
# "secret", only that group is masked; otherwise the whole match is.
SECRET_RULES = (
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
    ("AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b"),
    ("Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("Stripe key", r"\b[sr]k_(?:live|test)_[0-9A-Za-z]{16,}"),
    ("API key", r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}"),
    ("JWT", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    ("bearer token", r"\bBearer\s+(?P<secret>[A-Za-z0-9._~+/\-]{16,}=*)"),
    ("URL password", r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]*:(?P<secret>[^\s@/]+)@"),
    # A setting whose name ends in a secret word, such as POSTGRES_PASSWORD=
    # or _authToken=. Names like max_tokens or secretName do not end in one.
    # Values need 8+ characters, so prose like "secret: secrets" is left alone.
    (
        "secret value",
        (
            r"\b[\w.\-]*(?:password|passwd|pwd|secret|token|api_?key|secret_?key|access_?key|private_?key)"
            r"\s*[=:]\s*[\"']?(?P<secret>[^\s\"',;&]{8,})"
        ),
    ),
)

COMPILED_RULES = tuple(
    (label, re.compile(pattern, re.IGNORECASE | re.DOTALL)) for label, pattern in SECRET_RULES
)


def placeholder(label: str) -> str:
    """Return the text that replaces a masked secret."""
    return f"[REDACTED {label.upper()}]"


def redact_secrets(text: str) -> tuple[str, list[str]]:
    """Return the text with secrets masked, and the label of each one masked."""
    found = []

    for label, pattern in COMPILED_RULES:

        def mask(match: re.Match, label: str = label) -> str:
            secret_start, secret_end = match.span("secret") if "secret" in match.re.groupindex else match.span()

            # Earlier rules may already have masked this value
            if match.string[secret_start:secret_end].startswith("[REDACTED"):
                return match.group(0)

            found.append(label)
            start = secret_start - match.start()
            end = secret_end - match.start()
            return match.group(0)[:start] + placeholder(label) + match.group(0)[end:]

        text = pattern.sub(mask, text)

    return text, found


def describe(found: list[str]) -> str:
    """Summarise masked secrets, such as "2 secret values, 1 JWT"."""
    counts = {label: found.count(label) for label in dict.fromkeys(found)}
    return ", ".join(f"{count} {label}{'s' if count > 1 else ''}" for label, count in counts.items())
