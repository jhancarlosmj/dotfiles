"""Claude Code turns artifacts off when CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC is set.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VAR = "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"


class ArtifactsEnabledTest(unittest.TestCase):
    def test_zshrc_does_not_export_it(self) -> None:
        zshrc = (REPO / "shell" / ".zshrc").read_text()
        self.assertIsNone(re.search(rf"^\s*export\s+{VAR}=", zshrc, re.M))

    def test_claude_settings_do_not_set_it(self) -> None:
        settings = json.loads((REPO / "claude" / "settings.json").read_text())
        self.assertNotIn(VAR, settings.get("env", {}))


if __name__ == "__main__":
    unittest.main()
