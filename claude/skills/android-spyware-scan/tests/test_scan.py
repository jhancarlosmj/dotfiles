"""Tests for collect.sh and analyze.py, on synthetic phone data.

Run: python3 -I -m unittest discover -s claude/skills/android-spyware-scan/tests
"""

import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

PKGS_ALL = """\
package:/data/app/~~a1==/com.systemservice-b2==/base.apk=com.systemservice  installer=null uid:10900
package:/data/app/~~c3==/com.whatsapp-d4==/base.apk=com.whatsapp  installer=com.android.vending uid:10901
package:/data/app/~~e5==/com.apple.qrcode.reader-f6==/base.apk=com.apple.qrcode.reader  installer=com.android.vending uid:10902
package:/data/app/~~g7==/taxi.android.client-h8==/base.apk=taxi.android.client  installer=com.android.vending uid:10903
package:/data/app/OPNote/OppoNote2.apk=com.oneplus.note  installer=null uid:10904
package:/system/priv-app/Settings/Settings.apk=com.android.settings  installer=null uid:1000
"""
THIRD = ["com.systemservice", "com.whatsapp", "com.apple.qrcode.reader", "taxi.android.client", "com.oneplus.note"]

DUMPSYS_PACKAGE = """\
Packages:
  Package [com.systemservice] (aa):
    versionName=1.0
    firstInstallTime=2026-01-01 10:00:00
    initiatingPackageName=com.android.shell
    pkgFlags=[ HAS_CODE ]
      android.permission.RECEIVE_BOOT_COMPLETED: granted=true
        android.permission.RECORD_AUDIO: granted=true, flags=[ USER_SET ]
        android.permission.CAMERA: granted=true, flags=[ USER_SET ]
        android.permission.READ_SMS: granted=true, flags=[ USER_SET ]
  Package [com.whatsapp] (bb):
    versionName=2.0
        android.permission.RECORD_AUDIO: granted=true, flags=[ USER_SET ]
  Package [com.apple.qrcode.reader] (cc):
    versionName=1.0
  Package [taxi.android.client] (dd):
    versionName=1.0
  Package [com.oneplus.note] (ee):
    versionName=1.0
"""

IOC = """\
- name: TheTruthSpy
  type: stalkerware
  packages:
  - com.systemservice
  certificates:
  - 31A6ECECD97CF39BC4126B8745CD94A7C30BF81C
"""


def write_capture(d: Path, *, accessibility="null", admin=True):
    files = {
        "device.txt": "ro.product.manufacturer=OnePlus\nro.product.model=TEST\nro.boot.verifiedbootstate=green\n",
        "settings.txt": f"accessibility={accessibility}\nnotification_listeners=null\nrole_SMS=com.google.android.apps.messaging\n",
        "pkgs_all.txt": PKGS_ALL,
        "pkgs_3.txt": "".join(f"package:{p}\n" for p in THIRD),
        "pkgs_sys.txt": "package:com.android.settings\n",
        "pkgs_disabled.txt": "",
        "launcher_raw.txt": "com.whatsapp/.Main\ncom.apple.qrcode.reader/.Main\ntaxi.android.client/.Main\ncom.oneplus.note/.Main\n",
        "dumpsys_package.txt": DUMPSYS_PACKAGE,
        "device_policy.txt": ("  Enabled Device Admins (User 0, provisioningState: 0):\n    com.systemservice/.Admin:\n      uid=10900\n"
                              if admin else "  Enabled Device Admins (User 0, provisioningState: 0):\n    mPasswordOwner=-1\n"),
        "appops.txt": "## com.systemservice\nGET_USAGE_STATS: allow\n## com.whatsapp\nCAMERA: allow\n",
        "doze_whitelist.txt": "user,com.systemservice,10900\n",
        "accounts.txt": "    Account {name=user@example.com, type=com.google}\n",
        "usagestats.txt": "package=com.gone.app\n",
    }
    for name, body in files.items():
        (d / name).write_text(body)


def analyze(d: Path, ioc: Path | None = None) -> str:
    args = [sys.executable, "-I", str(SCRIPTS / "analyze.py"), str(d)]
    if ioc:
        args += ["--ioc", str(ioc)]
    subprocess.run(args, check=True, capture_output=True, text=True)
    return (d / "report.md").read_text()


def candidates(report: str) -> list[str]:
    section = report.split("## Pre-ranked candidates", 1)[1].split("\n## ", 1)[0]
    return [l.split("** ", 1)[1].split(":", 1)[0] for l in section.splitlines() if l.startswith("- **")]


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.ioc = self.d / "ioc.yaml"
        self.ioc.write_text(IOC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_stalkerware_with_admin_accessibility_and_ioc_ranks_first(self):
        write_capture(self.d, accessibility="com.systemservice/.Acc")
        report = analyze(self.d, self.ioc)
        self.assertEqual(candidates(report)[0], "com.systemservice")
        self.assertIn("accessibility enabled: ['com.systemservice/.Acc']", report)
        self.assertIn("device admins: ['com.systemservice/.Admin']", report)
        self.assertIn("('com.systemservice', 'TheTruthSpy')", report)

    def test_play_app_with_icon_is_not_a_candidate(self):
        write_capture(self.d)
        self.assertNotIn("com.whatsapp", candidates(analyze(self.d)))

    def test_maker_preload_is_not_reported_as_sideloaded(self):
        write_capture(self.d)
        report = analyze(self.d)
        outside = report.split("## User-installed apps from outside the Play Store", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("com.oneplus.note", outside)
        self.assertIn("com.systemservice: adb from a computer", outside)

    def test_brand_vendor_is_flagged_but_brand_word_later_is_not(self):
        write_capture(self.d)
        found = candidates(analyze(self.d))
        self.assertIn("com.apple.qrcode.reader", found)
        self.assertNotIn("taxi.android.client", found)

    def test_no_admins_reports_none(self):
        write_capture(self.d, admin=False)
        self.assertIn("device admins: none", analyze(self.d))

    def test_package_path_with_equals_signs_parses_to_the_package_name(self):
        write_capture(self.d)
        tsv = analyze(self.d) and (self.d / "apps.tsv").read_text()
        self.assertEqual([l.split("\t")[0] for l in tsv.splitlines()[1:]], sorted(THIRD))

    def test_uninstalled_package_from_usage_history_is_listed(self):
        write_capture(self.d)
        self.assertIn("com.gone.app", analyze(self.d))


FAKE_ADB = textwrap.dedent("""\
    #!/usr/bin/env bash
    # Reads stdin like the real adb shell does, so a loop that feeds it is swallowed.
    [[ "$1" == "-s" ]] && shift 2
    case "$1" in
      get-state) echo device; exit 0 ;;
      devices) exit 0 ;;
    esac
    cat >/dev/null
    shift
    case "$*" in
      "pm list packages -3") printf 'package:com.a\\npackage:com.b\\npackage:com.c\\n' ;;
      "appops get "*) echo "CAMERA: allow" ;;
    esac
""")


class CollectTest(unittest.TestCase):
    def test_appops_collected_for_every_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            adb = tmp / "bin" / "adb"
            adb.parent.mkdir()
            adb.write_text(FAKE_ADB)
            adb.chmod(adb.stat().st_mode | stat.S_IXUSR)
            env = {**os.environ, "PATH": f"{adb.parent}:{os.environ['PATH']}"}
            out = tmp / "out"
            subprocess.run(["bash", str(SCRIPTS / "collect.sh"), str(out)], check=True, env=env,
                           capture_output=True, text=True, timeout=60)
            headers = [l for l in (out / "appops.txt").read_text().splitlines() if l.startswith("## ")]
            self.assertEqual(headers, ["## com.a", "## com.b", "## com.c"])

    def test_no_device_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            adb = tmp / "bin" / "adb"
            adb.parent.mkdir()
            adb.write_text("#!/usr/bin/env bash\nexit 1\n")
            adb.chmod(adb.stat().st_mode | stat.S_IXUSR)
            env = {**os.environ, "PATH": f"{adb.parent}:{os.environ['PATH']}"}
            r = subprocess.run(["bash", str(SCRIPTS / "collect.sh"), str(tmp / "out")], env=env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2)
            self.assertIn("NO_DEVICE", r.stderr)


if __name__ == "__main__":
    unittest.main()
