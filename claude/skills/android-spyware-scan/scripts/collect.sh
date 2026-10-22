#!/usr/bin/env bash
# Read-only evidence collection from an Android phone over adb.
# Every command here only reads state: pm list, dumpsys, settings get,
# appops get, cmd role get-role-holders, getprop. Nothing is installed,
# changed, deleted or pulled from app storage.
#
# Usage: collect.sh <out_dir> [serial]
set -euo pipefail

OUT=${1:?usage: collect.sh <out_dir> [serial]}
SERIAL=${2:-}
mkdir -p "$OUT"

ADB=(adb)
[[ -n "$SERIAL" ]] && ADB+=(-s "$SERIAL")
# </dev/null: adb shell reads stdin and would swallow the package loop below.
sh_() { "${ADB[@]}" shell "$@" </dev/null 2>/dev/null || true; }

state=$("${ADB[@]}" get-state 2>/dev/null || true)
if [[ "$state" != "device" ]]; then
  echo "NO_DEVICE: adb get-state returned '${state:-nothing}'" >&2
  "${ADB[@]}" devices -l >&2 || true
  exit 2
fi

{
  for p in ro.product.manufacturer ro.product.model ro.build.version.release \
           ro.build.version.sdk ro.build.version.security_patch ro.build.display.id \
           ro.boot.verifiedbootstate ro.boot.flash.locked ro.debuggable; do
    echo "$p=$(sh_ getprop "$p" | tr -d '\r')"
  done
  echo "su_present=$(sh_ 'command -v su' | tr -d '\r')"
} > "$OUT/device.txt"

sh_ pm list packages -f -i -U > "$OUT/pkgs_all.txt"
sh_ pm list packages -3       > "$OUT/pkgs_3.txt"
sh_ pm list packages -s       > "$OUT/pkgs_sys.txt"
sh_ pm list packages -d       > "$OUT/pkgs_disabled.txt"
sh_ cmd package query-activities --brief -a android.intent.action.MAIN \
    -c android.intent.category.LAUNCHER > "$OUT/launcher_raw.txt"

{
  echo "accessibility=$(sh_ settings get secure enabled_accessibility_services | tr -d '\r')"
  echo "notification_listeners=$(sh_ settings get secure enabled_notification_listeners | tr -d '\r')"
  echo "always_on_vpn=$(sh_ settings get secure always_on_vpn_app | tr -d '\r')"
  echo "adb_wifi=$(sh_ settings get global adb_wifi_enabled | tr -d '\r')"
  echo "unknown_sources_legacy=$(sh_ settings get secure install_non_market_apps | tr -d '\r')"
  echo "verify_adb_installs=$(sh_ settings get global verifier_verify_adb_installs | tr -d '\r')"
  echo "package_verifier=$(sh_ settings get global package_verifier_user_consent | tr -d '\r')"
  for r in SMS DIALER ASSISTANT HOME BROWSER; do
    echo "role_$r=$(sh_ cmd role get-role-holders android.app.role.$r | tr -d '\r' | tr '\n' ' ')"
  done
} > "$OUT/settings.txt"

sh_ dumpsys device_policy          > "$OUT/device_policy.txt"
sh_ dumpsys accessibility          > "$OUT/accessibility.txt"
sh_ dumpsys package                > "$OUT/dumpsys_package.txt"
sh_ dumpsys account                > "$OUT/accounts.txt"
sh_ dumpsys deviceidle whitelist   > "$OUT/doze_whitelist.txt"
sh_ dumpsys activity services      > "$OUT/services.txt"
sh_ dumpsys batterystats           > "$OUT/batterystats.txt"
sh_ dumpsys netstats detail        > "$OUT/netstats.txt"
sh_ dumpsys usagestats             > "$OUT/usagestats.txt"
sh_ dumpsys connectivity           > "$OUT/connectivity.txt"

: > "$OUT/appops.txt"
while read -r line; do
  pkg=${line#package:}; pkg=${pkg%$'\r'}
  [[ -z "$pkg" ]] && continue
  { echo "## $pkg"; sh_ appops get "$pkg"; } >> "$OUT/appops.txt"
done < "$OUT/pkgs_3.txt"

echo "OK $(wc -l < "$OUT/pkgs_all.txt" | tr -d ' ') packages collected into $OUT"
