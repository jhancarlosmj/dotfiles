"""Turn the files written by collect.sh into a findings report.

Usage: python3 -I analyze.py <out_dir> [--ioc <ioc.yaml>]

Writes <out_dir>/report.md (the evidence, grouped by check) and
<out_dir>/apps.tsv (one row per user-installed app). Reads only local files.
"""

import collections
import re
import sys
from pathlib import Path

GOOGLE_PREFIXES = ("com.google.", "com.android.", "android.", "com.chrome.")
OEM_PREFIXES = {
    "oneplus": ("com.oneplus.", "net.oneplus.", "com.oplus.", "com.coloros.", "com.heytap.", "com.nearme.", "oplus."),
    "oppo": ("com.oppo.", "com.oplus.", "com.coloros.", "com.heytap.", "com.nearme."),
    "realme": ("com.realme.", "com.oplus.", "com.coloros.", "com.heytap.", "com.nearme."),
    "samsung": ("com.samsung.", "com.sec.", "com.knox."),
    "xiaomi": ("com.miui.", "com.xiaomi.", "com.mi.", "miui."),
    "google": ("com.google.",),
    "motorola": ("com.motorola.", "com.lenovo."),
    "huawei": ("com.huawei.", "com.hihonor."),
    "honor": ("com.hihonor.", "com.honor."),
    "sony": ("com.sony.", "com.sonyericsson."),
    "nothing": ("com.nothing.",),
}
CHIP_PREFIXES = ("com.qualcomm.", "com.qti.", "vendor.qti.", "org.codeaurora.", "com.mediatek.", "vendor.mediatek.")
# A package "imitates" when a label looks like OS plumbing, or the vendor label
# (second segment, com.<vendor>.x) claims a platform brand it may not own.
BAIT_LABEL = re.compile(r"^(system|sys|service|services|sync|update|updater|security|secure|monitor|tracker|spy|guard|battery|settings|framework|gms|daemon)", re.I)
BRAND_VENDORS = {"android", "google", "apple", "samsung", "system", "systemservice", "security", "update"}
RISKY_OPS = ("SYSTEM_ALERT_WINDOW", "GET_USAGE_STATS", "REQUEST_INSTALL_PACKAGES",
             "MANAGE_EXTERNAL_STORAGE", "PROJECT_MEDIA", "ACTIVATE_VPN", "READ_CLIPBOARD")
PERM_GROUPS = {
    "mic": ("RECORD_AUDIO",),
    "camera": ("CAMERA",),
    "location": ("ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"),
    "bg_location": ("ACCESS_BACKGROUND_LOCATION",),
    "sms": ("READ_SMS", "RECEIVE_SMS", "SEND_SMS", "RECEIVE_MMS"),
    "call_log": ("READ_CALL_LOG", "PROCESS_OUTGOING_CALLS"),
    "contacts": ("READ_CONTACTS",),
    "boot_start": ("RECEIVE_BOOT_COMPLETED",),
}


def read(out, name):
    p = out / name
    return p.read_text(errors="ignore") if p.exists() else ""


def lines_of(out, name):
    return [l.strip() for l in read(out, name).splitlines() if l.strip()]


def kv(text):
    d = {}
    for l in text.splitlines():
        if "=" in l:
            k, _, v = l.partition("=")
            d[k.strip()] = v.strip()
    return d


def uid_num(token):
    m = re.fullmatch(r"u(\d+)a(\d+)", token)
    if m:
        return int(m.group(1)) * 100000 + 10000 + int(m.group(2))
    return int(token) if token.isdigit() else None


def parse_pkg_list(out):
    rows = {}
    for l in lines_of(out, "pkgs_all.txt"):
        parts = l.split()
        head = parts[0][len("package:"):]
        path, _, pkg = head.rpartition("=")
        attrs = dict(p.split("=", 1) if "=" in p else p.split(":", 1) for p in parts[1:])
        rows[pkg] = {"path": path, "installer": attrs.get("installer", "?"), "uid": int(attrs.get("uid", "-1"))}
    return rows


def parse_dumpsys_package(out):
    text = read(out, "dumpsys_package.txt")
    if "\nPackages:\n" not in text:
        return {}
    sec = text.split("\nPackages:\n", 1)[1]
    info = {}
    for blk in re.split(r"\n  Package \[", sec)[1:]:
        pkg = blk.split("]", 1)[0]
        if pkg in info:
            continue
        get = lambda k: (re.search(rf"\b{k}=(\S+(?: \S+)?)", blk) or [None, ""])[1]
        granted = set(re.findall(r"android\.permission\.([A-Z_]+): granted=true", blk))
        info[pkg] = {
            "version": get("versionName"),
            "first_install": get("firstInstallTime"),
            "last_update": get("lastUpdateTime"),
            "initiating": get("initiatingPackageName"),
            "originating": get("originatingPackageName"),
            "flags": (re.search(r"pkgFlags=\[([^\]]*)\]", blk) or [None, ""])[1].split(),
            "granted": granted,
        }
    return info


def parse_appops(out):
    ops, cur = collections.defaultdict(set), None
    for l in read(out, "appops.txt").splitlines():
        if l.startswith("## "):
            cur = l[3:].strip()
            continue
        m = re.match(r"\s*(\w+): (allow|foreground)", l)
        if cur and m and m.group(1) in RISKY_OPS:
            ops[cur].add(m.group(1))
    return ops


def parse_device_admins(out):
    text = read(out, "device_policy.txt")
    admins, owners = [], []
    for m in re.finditer(r"Enabled Device Admins[^\n]*\n((?:    [^\n]*\n)*)", text):
        admins += re.findall(r"^    ([\w.]+/[\w.$]+):?\s*$", m.group(1), re.M)
    owners += re.findall(r"(?:Device|Profile) Owner[^\n]*?(ComponentInfo\{[^}]+\}|[\w.]+/[\w.$]+)", text)
    return sorted(set(admins)), sorted(set(owners))


def components(value):
    if not value or value == "null":
        return []
    return [c for c in value.split(":") if c]


def parse_battery(out, uid2pkgs):
    text = read(out, "batterystats.txt")
    window = re.search(r"Time on battery: ([^(]+)", text)
    sec = text[text.find("Estimated power use"):] if "Estimated power use" in text else ""
    rows = []
    for blk in re.split(r"\n  UID ", sec)[1:]:
        head = blk.split("\n", 1)[0]
        token, _, rest = head.partition(":")
        try:
            total = float(rest.split()[0])
        except (IndexError, ValueError):
            continue
        off = re.search(r"\(on battery, screen off/doze\)([^\n]*)", blk)
        off_mah = sum(float(x) for x in re.findall(r" (?:cpu|wifi|wakelock|sensors|gnss|bluetooth|camera)=([\d.]+)", off.group(1))) if off else 0.0
        wl = re.search(r"wakelock=[\d.]+ \(([^)]*)\)", off.group(1)) if off else None
        uid = uid_num(token)
        rows.append({"who": label(uid, uid2pkgs, token), "total": total, "off": off_mah, "wakelock_off": wl.group(1) if wl else ""})
    return (window.group(1).strip() if window else "unknown"), rows


def parse_netstats(out, uid2pkgs):
    text = read(out, "netstats.txt")
    i = text.find("UID stats:")
    if i < 0:
        return []
    sec = text[i:text.find("UID tag stats:", i) if "UID tag stats:" in text[i:] else None]
    tot, cur = collections.Counter(), None
    for l in sec.splitlines():
        m = re.search(r"\buid=(-?\d+)", l)
        if m:
            cur = int(m.group(1))
            continue
        m = re.search(r"rb=(\d+).*tb=(\d+)", l)
        if m and cur is not None:
            tot[cur] += int(m.group(1)) + int(m.group(2))
    return [(label(u, uid2pkgs, str(u)), b) for u, b in tot.most_common(25)]


def label(uid, uid2pkgs, fallback):
    pkgs = uid2pkgs.get(uid)
    return ",".join(pkgs)[:70] if pkgs else f"uid {fallback}"


def parse_ioc(path):
    """Minimal reader for AssoEchap stalkerware-indicators ioc.yaml: name -> packages."""
    iocs, name, in_pkgs = {}, None, False
    for raw in Path(path).read_text(errors="ignore").splitlines():
        if raw.startswith("- name:"):
            name, in_pkgs = raw.split(":", 1)[1].strip(), False
        elif re.match(r"^  \w+:", raw):
            in_pkgs = raw.strip() == "packages:"
        elif in_pkgs and raw.startswith("  - "):
            iocs[raw[4:].strip()] = name
    return iocs


def trusted(pkg, oem):
    return (pkg in ("android", oem) or pkg.startswith(GOOGLE_PREFIXES)
            or pkg.startswith(OEM_PREFIXES.get(oem, ())) or pkg.startswith(CHIP_PREFIXES))


def imitates(pkg, oem):
    if trusted(pkg, oem):
        return False
    labels = pkg.split(".")
    vendor = labels[1] if len(labels) > 1 and labels[0] in ("com", "net", "org", "io", "app") else labels[0]
    return vendor.lower() in BRAND_VENDORS or any(BAIT_LABEL.match(l) for l in labels[1:])


def main():
    args = sys.argv[1:]
    out = Path(args[0])
    ioc = parse_ioc(args[args.index("--ioc") + 1]) if "--ioc" in args else None

    dev = kv(read(out, "device.txt"))
    settings = kv(read(out, "settings.txt"))
    oem = dev.get("ro.product.manufacturer", "").lower()
    rows = parse_pkg_list(out)
    third = sorted(l.replace("package:", "") for l in lines_of(out, "pkgs_3.txt"))
    system = sorted(l.replace("package:", "") for l in lines_of(out, "pkgs_sys.txt"))
    launcher = {l.split("/")[0].strip() for l in lines_of(out, "launcher_raw.txt") if "/" in l}
    info = parse_dumpsys_package(out)
    ops = parse_appops(out)
    uid2pkgs = collections.defaultdict(list)
    for pkg, r in rows.items():
        uid2pkgs[r["uid"]].append(pkg)

    a11y = components(settings.get("accessibility"))
    listeners = components(settings.get("notification_listeners"))
    admins, owners = parse_device_admins(out)
    a11y_pkgs = {c.split("/")[0] for c in a11y}
    nl_pkgs = {c.split("/")[0] for c in listeners}
    admin_pkgs = {c.split("/")[0] for c in admins}
    doze = {l.split(",")[1] for l in lines_of(out, "doze_whitelist.txt") if l.startswith("user,")}
    running = set(re.findall(r"ServiceRecord\{\S+ u0 ([\w.]+)/", read(out, "services.txt")))

    def perms(pkg):
        g = info.get(pkg, {}).get("granted", set())
        return {k for k, ps in PERM_GROUPS.items() if g & set(ps)}

    def source(pkg):
        r, i = rows.get(pkg, {}), info.get(pkg, {})
        inst = r.get("installer", "?")
        if inst == "com.android.vending":
            return "Play Store"
        # OEM preloads live in /data/app/<Name>/ with no installer; user installs get a /~~ path.
        if inst == "null" and "/~~" not in r.get("path", "") and trusted(pkg, oem):
            return "preloaded by maker"
        if i.get("initiating") == "com.android.shell" or inst == "pc":
            return "adb from a computer"
        if i.get("originating") not in (None, "", "null"):
            return f"{inst} (file from {i['originating']})"
        return inst

    # Pre-ranking score: a hint for the agent, never the verdict.
    flagged = []
    for pkg in third:
        p, o = perms(pkg), ops.get(pkg, set())
        reasons, score = [], 0
        if pkg in a11y_pkgs: score += 5; reasons.append("accessibility service enabled")
        if pkg in admin_pkgs: score += 5; reasons.append("device admin")
        if pkg in nl_pkgs: score += 3; reasons.append("reads all notifications")
        if ioc and pkg in ioc: score += 10; reasons.append(f"listed stalkerware ({ioc[pkg]})")
        if pkg not in launcher: score += 2; reasons.append("no home-screen icon")
        if source(pkg) not in ("Play Store", "preloaded by maker"): score += 1; reasons.append(f"installed outside Play: {source(pkg)}")
        if imitates(pkg, oem): score += 2; reasons.append("name imitates system/brand")
        if {"sms", "call_log"} & p: score += 1; reasons.append("SMS/call log")
        if "bg_location" in p: score += 1; reasons.append("background location")
        if {"mic", "camera"} <= p and pkg not in launcher: score += 2; reasons.append("mic+camera with no icon")
        if pkg in doze and "boot_start" in p: score += 1; reasons.append("starts at boot, no battery limit")
        for op in o & {"GET_USAGE_STATS", "PROJECT_MEDIA", "REQUEST_INSTALL_PACKAGES", "SYSTEM_ALERT_WINDOW"}:
            score += 1; reasons.append(f"app-op {op}")
        if score >= 2:
            flagged.append((score, pkg, reasons))

    seen_in_usage = set(re.findall(r"package=([\w.]+)", read(out, "usagestats.txt")))
    gone = sorted(p for p in seen_in_usage - set(rows) if "." in p)

    with open(out / "apps.tsv", "w") as f:
        cols = ["package", "source", "icon", "accessibility", "device_admin", "notifications", *PERM_GROUPS, "app_ops", "doze_exempt", "running_now", "first_install", "version"]
        f.write("\t".join(cols) + "\n")
        for pkg in third:
            p = perms(pkg)
            f.write("\t".join([pkg, source(pkg), "yes" if pkg in launcher else "NO",
                               "YES" if pkg in a11y_pkgs else "", "YES" if pkg in admin_pkgs else "",
                               "yes" if pkg in nl_pkgs else "", *("yes" if k in p else "" for k in PERM_GROUPS),
                               ",".join(sorted(ops.get(pkg, ()))), "yes" if pkg in doze else "",
                               "yes" if pkg in running else "", info.get(pkg, {}).get("first_install", ""),
                               info.get(pkg, {}).get("version", "")]) + "\n")

    window, battery = parse_battery(out, uid2pkgs)
    net = parse_netstats(out, uid2pkgs)
    accounts = sorted(set(re.findall(r"Account \{name=([^,]+), type=([^}]+)\}", read(out, "accounts.txt"))), key=lambda a: a[1])

    R = []
    w = R.append
    w(f"# Android scan: {dev.get('ro.product.manufacturer')} {dev.get('ro.product.model')}\n")
    w("## Device integrity")
    for k in ("ro.build.version.release", "ro.build.version.security_patch", "ro.build.display.id",
              "ro.boot.verifiedbootstate", "ro.boot.flash.locked", "ro.debuggable", "su_present"):
        w(f"- {k}: `{dev.get(k, '')}`")
    for k in ("adb_wifi", "always_on_vpn", "verify_adb_installs", "package_verifier"):
        w(f"- {k}: `{settings.get(k, '')}`")
    w(f"\n## Counts\n- total {len(rows)}, system {len(system)}, user-installed {len(third)}, disabled {len(lines_of(out, 'pkgs_disabled.txt'))}")
    w("\n## High-power access")
    w(f"- accessibility enabled: {a11y or 'none'}")
    w(f"- device admins: {admins or 'none'}; device/profile owners: {owners or 'none'}")
    w(f"- notification listeners: {listeners or 'none'}")
    w("- roles: " + "; ".join(f"{k[5:]}={v.strip()}" for k, v in settings.items() if k.startswith("role_")))
    if ioc is not None:
        hits = sorted(p for p in rows if p in ioc)
        w(f"- stalkerware IOC matches ({len(ioc)} indicators): {[(p, ioc[p]) for p in hits] or 'none'}")
    w("\n## User-installed apps with no home-screen icon")
    w("\n".join(f"- {p} ({source(p)})" for p in third if p not in launcher) or "- none")
    w("\n## System packages from an unexpected publisher")
    w("\n".join(f"- {p}  {rows.get(p, {}).get('path', '')}" for p in system if not trusted(p, oem)) or "- none")
    w("\n## User-installed apps from outside the Play Store")
    for p in third:
        if source(p) not in ("Play Store", "preloaded by maker"):
            i = info.get(p, {})
            w(f"- {p}: {source(p)}, installed {i.get('first_install', '?')}, flags {' '.join(f for f in i.get('flags', []) if f in ('DEBUGGABLE', 'TEST_ONLY'))}")
    w("\n## Pre-ranked candidates (score is a hint; read each one)")
    for score, pkg, reasons in sorted(flagged, reverse=True):
        w(f"- **{score}** {pkg}: {'; '.join(reasons)}")
    w("\n## Sensitive permissions (user-installed)")
    for pkg in third:
        p, o = perms(pkg) - {"boot_start"}, ops.get(pkg, set())
        if p or o:
            w(f"- {pkg}: {' '.join(sorted(p))} {' '.join(sorted(o))}".rstrip())
    w(f"\n## Background: doze-exempt user apps\n- " + (", ".join(sorted(doze & set(third))) or "none"))
    w(f"\n## Background: user apps with a running service now\n- " + (", ".join(sorted(running & set(third))) or "none"))
    w(f"\n## Battery (window: {window} on battery)")
    for r in sorted(battery, key=lambda r: -r["total"])[:15]:
        w(f"- {r['total']:.1f} mAh total, {r['off']:.2f} screen-off, wakelock off {r['wakelock_off'] or '-'}: {r['who']}")
    w("\nTop screen-off:")
    for r in sorted(battery, key=lambda r: -r["off"])[:10]:
        w(f"- {r['off']:.2f} mAh screen-off: {r['who']}")
    w("\n## Network data (netstats retention window)")
    w("\n".join(f"- {b / 1e6:.1f} MB: {who}" for who, b in net) or "- unavailable")
    w("\n## Accounts on the device")
    w("\n".join(f"- {t}: {n}" for n, t in accounts) or "- none")
    w("\n## Packages in usage history that are no longer installed")
    w("- " + (", ".join(gone) or "none"))
    (out / "report.md").write_text("\n".join(R) + "\n")
    print(f"wrote {out / 'report.md'} and {out / 'apps.tsv'} ({len(third)} apps, {len(flagged)} candidates)")


if __name__ == "__main__":
    main()
