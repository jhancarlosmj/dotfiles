#!/bin/bash
# PreToolUse gate: an outward-facing write needs a fresh, explicit go from Warren.
#
# Covers Bash commands that post, comment, edit, merge or push to a shared or
# public surface (gh pr/issue writes, gh api mutations, curl mutations to a
# remote host, every git push) and MCP tools that send, post, create, update or
# delete on a colleague-visible system (email, calendar, Jira, Slack, GitHub,
# Notion, Composio). Reads and local-only tools pass straight through.
#
# The go has to be in Warren's most recent message: post, send, publish, push,
# deploy, go ahead, approved, ship it, submit, merge. A negated form ("don't
# post") does not count. That makes approval per action and per batch: once he
# has said anything else, the next outward write is blocked again and the draft
# has to be shown afresh. The 7 and 8 September Jira incidents and the four
# unasked deploys on 3 September are the reason this exists.
set -uo pipefail
input=$(cat)
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$input" HOOKS_DIR="$HOOKS_DIR" python3 - <<'PY'
import json, os, re, sys
sys.path.insert(0, os.environ["HOOKS_DIR"])
from lib_transcript import human_turns

try:
    call = json.loads(os.environ["INPUT"])
except Exception:
    sys.exit(0)
tool = call.get("tool_name", "")
inp = call.get("tool_input", {}) or {}
transcript = call.get("transcript_path", "")

BASH_RULES = [
    (r"\bgh\s+(pr|issue)\s+(comment|review|edit|close|merge|create|reopen|lock|ready)\b", "a GitHub PR/issue write"),
    (r"\bgh\s+api\b.*(-X\s*(POST|PATCH|PUT|DELETE)|--method[=\s]*(POST|PATCH|PUT|DELETE)|\s-[fF]\s|--field|--raw-field|--input)", "a GitHub API mutation"),
    (r"\bgh\s+(release|repo)\s+(create|edit|delete|archive|rename)\b", "a GitHub repo/release write"),
    (r"\bgit\s+(-C\s+\S+\s+)?push\b", "a git push"),
    (r"\bcurl\b(?![^\n|;&]*(localhost|127\.0\.0\.1|192\.168\.|minipc))[^\n|;&]*(\s-X\s*(POST|PUT|PATCH|DELETE)|\s--request\s*(POST|PUT|PATCH|DELETE)|\s-d\s|\s--data|\s--json\b|\s-F\s|\s--form\b)", "an HTTP mutation to a remote host"),
]

MCP_LOCAL = re.compile(r"^mcp__(rag|ccd_[a-z_]+|scheduled-tasks|computer-use|Claude_Browser|claude-in-chrome|visualize|terminal|mcp-registry|Claude_Code_iOS_Simulator)__")
MCP_LOCAL_TOOLS = re.compile(r"__(read_me|show_widget)$")
AIRMAIL_OUTWARD = {
    "send_email", "reply_to_message", "forward_message", "quick_reply",
    "create_event", "update_event", "delete_event", "set_vacation_settings",
    "create_rule", "toggle_rule", "delete_rule", "share_icloud", "update_user_profile",
}
READ_VERBS = re.compile(r"^(notion-)?(search|list|get|fetch|read|query|download|find|analy[sz]e|suggest|check|wait|show|refresh|export|batch_triage|manage_capabilities)", re.I)
WRITE_VERBS = re.compile(r"(send|reply|forward|post|publish|create|update|delete|trash|archive|move|transition|assign|comment|edit|execute|spawn|stop|convert|duplicate|add|remove|set|empty)", re.I)


def classify():
    if tool == "Bash":
        # Quoted strings are data (a commit body, a grep pattern), never the command.
        cmd = re.sub(r"'[^']*'|\"[^\"]*\"", " ", inp.get("command", "") or "")
        for pat, label in BASH_RULES:
            if re.search(pat, cmd, re.S):
                return label
        return None
    if not tool.startswith("mcp__"):
        return None
    if MCP_LOCAL.match(tool) or MCP_LOCAL_TOOLS.search(tool):
        return None
    name = tool.rsplit("__", 1)[-1]
    if tool.startswith("mcp__airmail__"):
        return f"an outward email/calendar action ({name})" if name in AIRMAIL_OUTWARD else None
    if READ_VERBS.match(name):
        return None
    if WRITE_VERBS.search(name):
        return f"a write to a shared system ({tool})"
    return None


label = classify()
if not label:
    sys.exit(0)

# A go stays live until the action is done or Warren redirects. Scanning only
# the newest message voided consent whenever he added a follow-up instruction
# before the authorised command had run (10 Sep, the SCB-5786 force-push), so
# look back over the last few turns and let a later veto override.
WINDOW = 3
GO = r"(post|send|publish|push|deploy|go ahead|approved|approve|ship it|submit|merge|comment it|reply to)"
NEG = r"\b(don'?t|do not|never|stop|without|no)\s+(\w+\s+){0,2}" + GO + r"\b"

turns = [t.lower() for t in human_turns(transcript)][-WINDOW:]
go_at = None
for i, t in enumerate(turns):
    neg = re.search(NEG, t)
    pos = list(re.finditer(r"\b" + GO + r"\b", t))
    if pos and not (neg and len(pos) == 1):
        go_at = i
# A veto in the same turn or any turn after the go cancels it.
if go_at is not None and not any(re.search(NEG, t) for t in turns[go_at + 1:]):
    sys.exit(0)

reason = (
    f"Blocked: this is {label} and Warren's latest message does not authorise it. "
    "Show him the exact draft or command, stop, and ask him to reply with the action word "
    "(post / send / publish / push / deploy / merge). One go covers one named batch, and stays live across follow-up instructions until the action runs or he vetoes it."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
PY
