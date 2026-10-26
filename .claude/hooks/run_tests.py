#!/usr/bin/env python3
"""Stop hook: run the snip test suite and stop Claude from finishing while it is red.

Protocol (https://code.claude.com/docs/en/hooks, "Stop decision control"):
  * stdin  - JSON with the common fields plus `stop_hook_active`.
  * stdout - on failure, exit 0 and print {"decision": "block", "reason": "..."};
             `reason` is required and tells Claude why it must keep working.
  * on success, print nothing and exit 0, which lets Claude stop.

Claude Code caps consecutive stop-hook continuations at 8, so a failure that
cannot be fixed cannot loop forever.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PYTEST_ARGS = ["-m", "pytest", "tests/unit", "tests/api", "-q", "-p", "no:warnings"]
TIMEOUT_SECONDS = 120
MAX_REASON_CHARS = 6000
PYTEST_NO_TESTS_COLLECTED = 5


def project_dir(hook_input: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or hook_input.get("cwd") or ".")


def venv_python(root: Path) -> str:
    for candidate in (root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    root = project_dir(hook_input)
    try:
        result = subprocess.run(
            [venv_python(root), *PYTEST_ARGS],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        block(f"pytest did not finish within {TIMEOUT_SECONDS}s. Find out why before ending the turn.")
        return 0

    if result.returncode in (0, PYTEST_NO_TESTS_COLLECTED):
        return 0

    output = (result.stdout + result.stderr).strip()
    if len(output) > MAX_REASON_CHARS:
        output = "... (truncated)\n" + output[-MAX_REASON_CHARS:]
    block(
        "The test suite is failing (pytest exit code "
        f"{result.returncode}). Fix the failing tests, or tell the user clearly that you "
        "could not and which tests are still red.\n\n" + output
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
