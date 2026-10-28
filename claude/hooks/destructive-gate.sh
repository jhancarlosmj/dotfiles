#!/bin/bash
# PreToolUse gate: a destructive shell command needs an explicit go in Spanish
# or English from one of the last few human messages.
#
# Covers what the global rules call "can't cheaply undo" on the shell: rm and
# unlink, find -delete / -exec rm, rsync --delete, shred, truncate, dd of=,
# diskutil erase, and the git commands that throw away uncommitted work
# (reset --hard, clean -f, checkout/restore of paths, stash drop/clear,
# branch -D). ssh, bash -c and xargs payloads are read the same way.
#
# Session scratch is exempt: rm whose every target sits under a claude-*
# temporary directory passes, because that space is disposable by design.
# Anything the gate cannot resolve (a $variable, a ~user path) counts as
# outside scratch, so the gate errs towards asking.
#
# The go word must name the deletion (borra, elimina, delete, remove, descarta,
# discard, reset): a bare "sí" cannot tell which batch it approves. A later
# veto ("no borres", "don't delete") cancels it. Before this gate the global
# rules said destructive Bash had no mechanical control at all.
set -uo pipefail
input=$(cat)
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$input" HOOKS_DIR="$HOOKS_DIR" python3 - <<'PY'
import json, os, re, shlex, sys, unicodedata
sys.path.insert(0, os.environ["HOOKS_DIR"])
from lib_transcript import human_turns

try:
    call = json.loads(os.environ["INPUT"])
except Exception:
    sys.exit(0)
if call.get("tool_name") != "Bash":
    sys.exit(0)
command = (call.get("tool_input") or {}).get("command", "") or ""
cwd = call.get("cwd") or os.getcwd()
transcript = call.get("transcript_path", "")

SCRATCH = re.compile(r"^(/private)?/tmp/claude-[^/]+/.+")
WRAPPERS = {"sudo", "command", "exec", "nohup", "time", "nice", "env"}
SEPARATORS = {";", "&&", "||", "|", "&", "\n"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.S | re.M)
REDIRECT = re.compile(r"^\d*(>>?|<|>&|&>)")


def tokens(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        return list(lexer)
    except ValueError:
        # Unbalanced quotes: fall back to a plain split so detection still runs.
        return text.split()


def segments(text):
    # A heredoc body is data (a commit message, a file being written), not commands.
    text = HEREDOC.sub(" ", text)
    seg = []
    for tok in tokens(text.replace("\n", " ; ")):
        if tok in SEPARATORS or set(tok) <= set(";&|"):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(tok)
    if seg:
        yield seg


def strip_prefix(seg):
    seg = list(seg)
    while seg and (seg[0] in WRAPPERS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0])):
        seg.pop(0)
        if seg and seg[0].startswith("-") and seg[0] != "--":
            seg.pop(0)  # a wrapper's own flag, e.g. sudo -n
    return seg


def in_scratch(path, here):
    if not path or "$" in path or "`" in path or path.startswith("~"):
        return False
    full = os.path.normpath(path if path.startswith("/") else os.path.join(here, path))
    return bool(SCRATCH.match(full))


def operands(args):
    out, done, skip = [], False, False
    for a in args:
        if skip:
            skip = False
        elif REDIRECT.match(a):
            skip = REDIRECT.match(a).end() == len(a)  # "2>" alone: the target follows
        elif not done and a == "--":
            done = True
        elif done or not a.startswith("-"):
            out.append(a)
    return out


def classify(seg, remote, here):
    """Return a label for a destructive segment, or None."""
    seg = strip_prefix(seg)
    if not seg:
        return None
    prog = os.path.basename(seg[0])
    args = seg[1:]

    if prog in ("ssh",):
        # ssh [opts] host cmd...: the remote command is what runs.
        rest, i = args, 0
        while i < len(rest) and rest[i].startswith("-"):
            i += 2 if re.fullmatch(r"-[bcDEeFIiJLlmOopQRSWw]", rest[i]) else 1
        payload = " ".join(rest[i + 1:])
        return check(payload, remote=True, here=here) if payload else None
    if prog in ("bash", "sh", "zsh") and "-c" in args:
        idx = args.index("-c")
        return check(args[idx + 1], remote, here) if idx + 1 < len(args) else None
    if prog == "xargs":
        inner = [a for a in args if not a.startswith("-")]
        if inner and os.path.basename(inner[0]) in ("rm", "unlink", "shred"):
            return f"a bulk delete through xargs ({inner[0]})"
        return None

    if prog in ("rm", "unlink", "rmdir"):
        targets = operands(args)
        if not remote and targets and all(in_scratch(t, here) or resolve(t, here) in created() for t in targets):
            return None
        shown = ", ".join(targets[:3]) + (" ..." if len(targets) > 3 else "")
        where = "on a remote host" if remote else "outside session scratch"
        return f"a delete {where} ({prog} {shown})"
    if prog == "find" and ("-delete" in args or any(
            a == "-exec" and i + 1 < len(args) and os.path.basename(args[i + 1]) in ("rm", "unlink", "shred")
            for i, a in enumerate(args))):
        roots = operands(args)[:1]
        if not remote and roots and in_scratch(roots[0], here):
            return None
        return "a bulk delete through find"
    if prog == "rsync" and any(a.startswith("--delete") or a.startswith("--remove-source-files") for a in args):
        return "an rsync that deletes files"
    if prog in ("shred", "truncate"):
        return f"a destructive {prog}"
    if prog == "dd" and any(a.startswith("of=") for a in args):
        return "a dd write to a file or device"
    if prog == "diskutil" and args and re.match(r"(?i)(erase|zero|randomdisk|secureerase|partitiondisk|reformat)", args[0]):
        return f"a disk erase (diskutil {args[0]})"
    if prog == "git":
        # Skip global options such as -C dir to reach the subcommand.
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in ("-C", "-c", "--git-dir", "--work-tree") else 1
        sub, rest = (args[i], args[i + 1:]) if i < len(args) else ("", [])
        if sub == "reset" and "--hard" in rest:
            return "a git reset --hard, which discards uncommitted work"
        if sub == "clean" and any(re.match(r"^-[a-zA-Z]*f", a) or a == "--force" for a in rest):
            return "a git clean, which deletes untracked files"
        if sub == "checkout" and "--" in rest and rest.index("--") < len(rest) - 1:
            return "a git checkout of paths, which discards their changes"
        if sub == "checkout" and rest[:1] == ["."]:
            return "a git checkout of paths, which discards their changes"
        if sub == "restore" and "--staged" not in rest and operands(rest):
            return "a git restore, which discards working-tree changes"
        if sub == "stash" and rest[:1] in (["drop"], ["clear"]):
            return f"a git stash {rest[0]}"
        forced = "--force" in rest or "-f" in rest
        if sub == "branch" and ("-D" in rest or ("--delete" in rest and forced) or ("-d" in rest and forced)):
            return "a forced git branch delete"
    return None


ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def expand(tok, known):
    """Substitute variables assigned earlier in the same command; leave the rest."""
    return VAR_REF.sub(lambda m: known.get(m.group(1) or m.group(2), m.group(0)), tok)


def walk(text, here):
    """Yield (segment, directory it runs in), with assignments and cd applied."""
    known = {}
    for seg in segments(text):
        body = seg[1:] if seg[:1] == ["export"] else seg
        if body and all(ASSIGN.match(t) for t in body):
            # `S=/tmp/claude-x/scratchpad; rm -rf $S/out` resolves S. A value
            # that itself holds an unknown $var stays unresolved, so it is gated.
            for t in body:
                name, value = ASSIGN.match(t).groups()
                known[name] = expand(value, known)
            continue
        seg = strip_prefix([expand(t, known) for t in seg])
        if seg[:1] == ["cd"]:
            # Track `cd dir && rm x` so a relative target resolves where it runs.
            target = seg[1] if len(seg) > 1 else "~"
            here = "~unknown" if (target.startswith("~") or "$" in target) else os.path.normpath(os.path.join(here, target))
            continue
        yield seg, here


def check(text, remote=False, here=None):
    for seg, where in walk(text, here or cwd):
        label = classify(seg, remote, where)
        if label:
            return label
    return None


def resolve(path, here):
    if not path or "$" in path or "`" in path or path.startswith("~") or here.startswith("~"):
        return None
    return os.path.normpath(path if path.startswith("/") else os.path.join(here, path))


OUT_REDIRECT = re.compile(r"^(?:1?>|&>)(?!>)(.*)$")
_created = None


def created():
    """Absolute paths this session created: Write of a new file, `> f`, cp targets.

    A file the session made is its own scratch, so removing it needs no go. A
    Write that overwrote an existing file does not count: its result says
    "updated", not "created". The cost is one transcript read, paid only when an
    rm would otherwise be blocked.
    """
    global _created
    if _created is not None:
        return _created
    _created = set()
    write_paths, results = {}, set()
    try:
        fh = open(transcript, encoding="utf-8", errors="replace")
    except OSError:
        return _created
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content") if isinstance(rec, dict) else None
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_result":
                    text = b.get("content")
                    text = text if isinstance(text, str) else json.dumps(text)
                    if "File created successfully" in text:
                        results.add(b.get("tool_use_id"))
                    continue
                if b.get("type") != "tool_use" or not isinstance(b.get("input"), dict):
                    continue
                if b.get("name") == "Write" and isinstance(b["input"].get("file_path"), str):
                    write_paths[b.get("id")] = os.path.normpath(b["input"]["file_path"])
                elif b.get("name") == "Bash":
                    _created |= made_by(b["input"].get("command", "") or "", rec.get("cwd") or cwd)
    _created |= {p for tid, p in write_paths.items() if tid in results}
    # The command under review can create and remove in one go:
    # `... > .pr-body.md && gh pr create ... && rm .pr-body.md`.
    _created |= made_by(command, cwd)
    return _created


def made_by(cmd, here):
    """Paths a shell command creates through `> f` or as a cp destination."""
    out = set()
    for seg, where in walk(cmd, here):
        targets = []
        for i, tok in enumerate(seg):
            m = OUT_REDIRECT.match(tok)
            if m:
                targets.append(m.group(1) or (seg[i + 1] if i + 1 < len(seg) else ""))
        # cp only: after `mv mine dest`, dest holds the user's original.
        if seg and os.path.basename(seg[0]) == "cp":
            ops = operands(seg[1:])
            if len(ops) == 2:
                targets.append(ops[1])
        for t in targets:
            full = resolve(t, where)
            if full and not full.startswith("/dev/"):
                out.add(full)
    return out


label = check(command)
if not label:
    sys.exit(0)


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


WINDOW = 3
GO = r"(borr\w*|elimin\w*|delet\w*|remov\w*|descart\w*|discard\w*|wipe\w*|purg\w*|reset\w*)"
NEG = r"\b(no|don'?t|do not|never|nunca|sin|stop|ni)\s+(\w+\s+){0,2}" + GO + r"\b"

turns = [fold(t) for t in human_turns(transcript)][-WINDOW:]
go_at = None
for i, t in enumerate(turns):
    neg = re.search(NEG, t)
    pos = list(re.finditer(r"\b" + GO + r"\b", t))
    if pos and not (neg and len(pos) == 1):
        go_at = i
if go_at is not None and not any(re.search(NEG, t) for t in turns[go_at + 1:]):
    sys.exit(0)

reason = (
    f"Blocked: this is {label}, and none of the last {WINDOW} human messages authorises a deletion. "
    "Show the count of what goes, a 2-3 item sample and how each was verified safe, then stop and ask "
    "for a reply that names the action (borra / elimina / delete / descarta). A bare 'sí' does not count. "
    "Work in session scratch (/tmp/claude-*) is exempt."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
PY
