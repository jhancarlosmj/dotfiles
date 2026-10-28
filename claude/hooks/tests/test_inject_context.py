"""Tests for inject-context.sh, the per-prompt knowledge-routing reminder.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import re
import subprocess
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
GLOBAL_RULES = HOOKS.parent / "CLAUDE.md"


def run_hook() -> str:
    proc = subprocess.run(
        ["bash", str(HOOKS / "inject-context.sh")],
        input='{"prompt": "hola"}',
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return proc.stdout


class InjectContextTest(unittest.TestCase):
    def test_never_asks_for_a_hand_written_session_note(self) -> None:
        # The reminder once said "write or update a summary in ~/.wiki/sessions/",
        # contradicting the global rules on every prompt.
        out = run_hook()
        for line in out.splitlines():
            if "sessions/" in line and re.search(r"\b(write|update)\b", line, re.I):
                self.assertIn("never hand-write", line)

    def test_agrees_with_global_rules_on_session_notes(self) -> None:
        self.assertIn("auto-generated; never hand-write one", GLOBAL_RULES.read_text())
        self.assertIn("auto-generated", run_hook())

    def test_stays_short(self) -> None:
        # It fires on every prompt: a pointer, never a dump.
        self.assertLessEqual(len(run_hook().splitlines()), 8)


if __name__ == "__main__":
    unittest.main()
