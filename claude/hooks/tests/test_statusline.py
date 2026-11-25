"""Tests for statusline.sh: the month-to-date cost segment and its cache.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "statusline.sh"
PAYLOAD = json.dumps({"model": {"display_name": "Opus 5.5"}, "workspace": {"current_dir": "/"}})
SGR = re.compile(r"\x1b\[[0-9;]*m")

FAKE_CCUSAGE = """#!/bin/sh
echo "$@" >> "$CALLS"
cat <<JSON
{"monthly": [{"month": "$MONTH", "totalCost": 41.6}], "totals": {"totalCost": 41.6}}
JSON
"""


class MonthCostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        # Only jq from Homebrew: the real ccusage there must not leak in
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        self.cache = self.tmp / "cache" / "month-cost"
        self.calls = self.tmp / "calls"
        self.month = time.strftime("%Y-%m")

    def install_ccusage(self):
        fake = self.bin / "ccusage"
        fake.write_text(FAKE_CCUSAGE)
        fake.chmod(0o755)

    def write_cache(self, month, age, cost):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(f"{month} {int(time.time()) - age} {cost}\n")

    def run_line(self, locale="C"):
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.tmp),
            "MONTH_COST_CACHE": str(self.cache),
            "CALLS": str(self.calls),
            "MONTH": self.month,
            "LC_ALL": locale,
        }
        proc = subprocess.run(
            ["bash", str(SCRIPT)], input=PAYLOAD, env=env,
            capture_output=True, text=True, timeout=15, check=True,
        )
        return SGR.sub("", proc.stdout)

    def wait_for_refresh(self):
        for _ in range(50):
            if self.calls.exists() and self.cache.exists() and not (self.cache.parent / "refresh.lock").exists():
                return
            time.sleep(0.1)
        self.fail("background refresh did not finish")

    def test_no_segment_without_ccusage(self):
        self.assertNotIn("/mes", self.run_line())

    def test_first_run_shows_nothing_and_fills_the_cache(self):
        self.install_ccusage()
        self.assertNotIn("/mes", self.run_line())
        self.wait_for_refresh()
        self.assertEqual(self.cache.read_text().split()[::2], [self.month, "41.6"])
        self.assertIn("claude monthly --json --offline", self.calls.read_text())
        self.assertIn("~$42/mes", self.run_line())

    def test_fresh_cache_is_shown_without_a_refresh(self):
        self.install_ccusage()
        self.write_cache(self.month, 10, "1234.4")
        self.assertIn("~$1234/mes", self.run_line())
        time.sleep(0.5)
        self.assertFalse(self.calls.exists())

    def test_stale_cache_is_shown_and_refreshed(self):
        self.install_ccusage()
        self.write_cache(self.month, 600, "10")
        self.assertIn("~$10/mes", self.run_line())
        self.wait_for_refresh()
        self.assertIn("41.6", self.cache.read_text())

    def test_last_month_cost_is_never_shown(self):
        self.install_ccusage()
        self.write_cache("1999-01", 10, "999")
        self.assertNotIn("/mes", self.run_line())
        self.wait_for_refresh()

    def test_half_a_dollar_rounds_up(self):
        self.install_ccusage()
        self.write_cache(self.month, 10, "1234.5")
        self.assertIn("~$1235/mes", self.run_line())

    def test_spanish_locale_still_formats_the_cost(self):
        self.install_ccusage()
        self.write_cache(self.month, 10, "2521.93")
        self.assertIn("~$2522/mes", self.run_line(locale="es_ES.UTF-8"))


if __name__ == "__main__":
    unittest.main()
