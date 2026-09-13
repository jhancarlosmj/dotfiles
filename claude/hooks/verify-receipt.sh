#!/bin/bash
# PreToolUse gate: a deliverable needs to exist before it's handed over.
#
# Covers SendUserFile and Artifact (publish action). Both take a file path and
# ship its contents to the user; if that path doesn't exist on disk, the tool
# is about to deliver something that was never produced (a hallucinated path,
# a file that failed to write, a stale reference). Blocks in that case and
# asks for the real path or for the file to be created first.
#
# Bash is in the PreToolUse matcher alongside these two tools but this hook
# does not gate it — there's no single "deliverable" shape for an arbitrary
# shell command, so Bash calls pass straight through.
set -uo pipefail
input=$(cat)
INPUT="$input" python3 - <<'PY'
import json, os, sys

try:
    call = json.loads(os.environ["INPUT"])
except Exception:
    sys.exit(0)

tool = call.get("tool_name", "")
inp = call.get("tool_input", {}) or {}

if tool == "Bash":
    sys.exit(0)

if tool == "Artifact":
    action = inp.get("action") or "publish"
    if action != "publish":
        sys.exit(0)
    path = inp.get("file_path")
elif tool == "SendUserFile":
    path = inp.get("file_path") or inp.get("path")
else:
    sys.exit(0)

if not path:
    sys.exit(0)

expanded = os.path.expanduser(path)
if os.path.isfile(expanded):
    sys.exit(0)

reason = (
    f"Blocked: {tool} is about to deliver '{path}', which does not exist on disk. "
    "Create the file first (or fix the path) before sending or publishing it."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
PY
