---
name: android-spyware-scan
description: Read-only adb scan of an Android phone for spyware or stalkerware. Use when the user asks to check, scan or audit their Android phone over USB/adb for spyware, stalkerware, monitoring apps, or apps with suspicious access.
---

# Android spyware scan

A read-only, evidence-first check of a phone connected over adb. The phone is the user's own, and the output is a ranked list of apps with plain-language reasons and a one-word **verdict**.

## Guardrail: read-only

Run only commands that read state: `getprop`, `pm list`, `dumpsys`, `settings get`, `appops get`, `cmd role get-role-holders`, `cmd package query-activities`. Each change (uninstall, `pm disable`, `settings put`, `appops set`, revoking, `adb install`, `adb pull` of app data) is the user's to make on the phone, from the steps you give them. Phone data stays on this machine: the report, account names and package lists are shown to the user and written only to the scratchpad.

## Steps

1. **Connect.** Run `adb devices -l`. Done when the phone shows as `device`. If the list is empty, check the USB bus with `system_profiler SPUSBDataType` (macOS) and give the user the four fixes: a data cable, USB mode "File transfer", USB debugging on, accepting the RSA prompt. `unauthorized` means the prompt is still waiting on the phone.

2. **Collect.** Run `scripts/collect.sh <scratchpad>/android-scan-<date>` (add the serial as the second argument when several devices are attached). Done when it prints `OK <n> packages`, and `grep -c '^## ' appops.txt` equals the line count of `pkgs_3.txt`.

3. **Indicators.** Download the public stalkerware indicator list to its own empty directory: `curl -sf -o <dir>/ioc.yaml https://raw.githubusercontent.com/AssoEchap/stalkerware-indicators/master/ioc.yaml`. This is a download only, and nothing from the phone is sent. If it fails, go on without it and say so in the limits.

4. **Analyze.** Run `python3 -I scripts/analyze.py <out_dir> --ioc <dir>/ioc.yaml`. It writes `report.md` (the evidence by check) and `apps.tsv` (one row per user-installed app). Read the whole `report.md`.

5. **Investigate.** The pre-ranked candidates are hints from a heuristic score, not findings. For each candidate, and for any app in "high-power access", read `adb shell dumpsys package <pkg>` (install time, origin, granted permissions, receivers) and its line in `dumpsys usagestats`, then give it a disposition: _explained_ (a known app whose access fits its job), _ask_ (only the user can say whether they installed it), or _flagged_. Also review the accounts list: an account the user may not own is a candidate too, because a synced account can expose contacts, photos and location with no app installed. Done when every candidate and every account has a disposition, with the evidence line that settled it.

6. **Report.** Answer in the user's language, in this order:
   - the integrity facts (verified boot, bootloader, root, patch level) and the high-power access counts;
   - the inventory, with the full per-app table left in `apps.tsv` and its absolute path given;
   - background, battery and data, stating the battery window (it only covers time since the last charge);
   - the flagged apps, most worrying first, each with one plain sentence on why it is a problem;
   - the _ask_ items as direct questions;
   - removal and securing steps for each flagged app, from [REMEDIATION.md](REMEDIATION.md);
   - the limits of this scan;
   - the **verdict**.

## Verdict

- **compromised**: an IOC match; accessibility, device admin, device/profile owner or notification access held by an app the user does not recognise; root or an unlocked bootloader the user did not do; or an account the user does not own that syncs data.
- **suspicious**: an unexplained sideloaded or impersonating app with real access (sensitive permissions, boot start, battery exemption), or an _ask_ item still open.
- **clean**: every candidate is _explained_.

## Reading the evidence

- `installer=null` with a path like `/data/app/<Name>/` is a maker preload; a `/data/app/~~…` path with no installer came from a computer over adb. The script labels both.
- `originatingPackageName=com.android.chrome` means the APK file was downloaded in the browser. Patchers such as Morphe or ReVanced send users to the browser for microG, so this alone is normal.
- `com.oneplus.backuprestore` (Clone Phone) as installer means the app was restored from an old phone.
- `dumpsys usagestats` keeps packages that are no longer installed; the report lists them separately because they cannot be inspected any more.
- High screen-off battery from a game or media app usually lines up with background audio; check `audio:bg` in that app's batterystats block before calling it suspicious.

## Limits to state every time

- User-installed CA certificates need the phone's UI: Settings → Security → Credentials → User credentials.
- Malicious code inside an otherwise legitimate app, and signing-certificate matches, are out of reach without pulling APKs.
- Battery history covers only the time since the last full charge.
- Remind the user to turn USB debugging off when done.
