"""
Fixed rules for commands that are dangerous in almost any fix.

The AI reviewer can approve an unsafe fix, so these rules run first and
send the fix back for changes. They only see commands: fenced code, and
inline code that is not on a line warning against it.
"""

import re

# Each rule is a pattern and the reason shown to the coder and the user
RISKY_COMMANDS = (
    (r"rm\s+-rf\s+/(\s|\*|$)", "deletes the whole filesystem"),
    (r"chmod\s+(-R\s+)?0?777", "gives every user full access"),
    (r"mkfs\.", "formats a disk"),
    (r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh", "runs a downloaded script without reading it"),
    (r"curl\s+(-[a-zA-Z]*k\b|--insecure)", "turns off TLS certificate checks"),
    (r"--insecure-skip-tls-verify", "turns off TLS certificate checks"),
    (r"--no-check-certificate", "turns off TLS certificate checks"),
    (r"verify\s*=\s*False", "turns off TLS certificate checks"),
    (r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0", "turns off TLS certificate checks"),
    (r"setenforce\s+0", "turns off SELinux"),
    (r"ufw\s+disable|iptables\s+-F\b", "turns off the firewall"),
    (r"--privileged", "gives a container full access to the host"),
    (r"prune\s[^\n]*--volumes", "deletes Docker volumes and their data"),
)

FENCED_PATTERN = re.compile(r"```.*?```", re.DOTALL)
INLINE_PATTERN = re.compile(r"`[^`\n]+`")
WARNING_PATTERN = re.compile(
    r"\b(never|avoid|warning|danger\w*|unsafe|insecure\w*|risk\w*|bypass\w*|do not|don't)\b",
    re.IGNORECASE,
)


def code_in(text: str) -> str:
    """Return fenced code, plus inline code from lines that are not warnings."""
    fenced = FENCED_PATTERN.findall(text)
    prose = FENCED_PATTERN.sub("", text)
    inline = [
        code
        for line in prose.splitlines()
        if not WARNING_PATTERN.search(line)
        for code in INLINE_PATTERN.findall(line)
    ]
    return "\n".join([*fenced, *inline])


def find_risky_commands(text: str) -> list[str]:
    """Return a description of each risky command found in the text's code."""
    code = code_in(text)
    issues = []

    for pattern, reason in RISKY_COMMANDS:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            issues.append(f"`{match.group(0).strip()}` {reason}")

    return issues
