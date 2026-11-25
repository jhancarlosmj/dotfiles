"""Claude Code turns artifacts, or their database and comments, off when one of
these is set: each stops it fetching its feature flags.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VARS = ("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "DISABLE_TELEMETRY", "DO_NOT_TRACK")


class ArtifactsEnabledTest(unittest.TestCase):
    def test_zshrc_does_not_export_it(self) -> None:
        zshrc = (REPO / "shell" / ".zshrc").read_text()
        for var in VARS:
            self.assertIsNone(re.search(rf"^\s*export\s+{var}=", zshrc, re.M), var)

    def test_claude_settings_do_not_set_it(self) -> None:
        settings = json.loads((REPO / "claude" / "settings.json").read_text())
        for var in VARS:
            self.assertNotIn(var, settings.get("env", {}))


if __name__ == "__main__":
    unittest.main()
