"""Auto-consent: let a repository's own reviewed rules approve an outward command.

consent-gate.sh asks this module before it refuses a Bash command that has no
go word from Jhan Carlos. A repository opts in by committing
`.claude/auto-consent.py`. The rules are read from the remote-tracking branch
(`origin/develop`, else `origin/main`), never from the working tree, so a
branch cannot approve its own push by editing them: a change to the rules
counts only once it has been merged on the remote.

The rule script gets on stdin a JSON object {command, cwd, transcript_path,
repo} and prints one JSON object: {"allow": true, "reason": "..."} or
{"allow": false, "reason": "..."}. Anything else (an error, a timeout, a
missing key, more output) is a refusal: consent fails closed.

Only a repository whose `remote.origin.url` is a line of
~/.claude/auto-consent-repos runs its rules: the script is code from the
repository, and a clone of someone else's must not run on every outward
command. The list is local to this Mac and not versioned.

Every allow is appended to ~/.claude/auto-consent.log, so each command that
passed without Jhan Carlos's word can be read back.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

RULES_PATH = ".claude/auto-consent.py"
REFS = ("refs/remotes/origin/develop", "refs/remotes/origin/main")
TIMEOUT = 20
LOG = Path(os.environ.get("AUTO_CONSENT_LOG", Path.home() / ".claude" / "auto-consent.log"))
TRUSTED = Path(os.environ.get("AUTO_CONSENT_REPOS", Path.home() / ".claude" / "auto-consent-repos"))


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)


def _main_checkout(cwd):
    """The repository's main checkout, also from a linked worktree, or None."""
    if not cwd or not os.path.isdir(cwd):
        return None
    out = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if out.returncode != 0:
        return None
    return str(Path(out.stdout.strip()).parent)


def _trusted(repo):
    url = _git(repo, "config", "--get", "remote.origin.url").stdout.strip()
    try:
        lines = TRUSTED.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    return bool(url) and url in {l.strip() for l in lines if l.strip() and not l.startswith("#")}


def _rules(repo):
    """The committed rule script and the ref it came from, or (None, None)."""
    for ref in REFS:
        out = _git(repo, "show", f"{ref}:{RULES_PATH}")
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout, ref
    return None, None


def decide(command, cwd, transcript_path):
    """Return (allowed, reason). reason is None when the repository has no rules."""
    try:
        repo = _main_checkout(cwd)
        if not repo or not _trusted(repo):
            return False, None
        source, ref = _rules(repo)
        if source is None:
            return False, None
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "auto_consent_rules.py"
            script.write_text(source, encoding="utf-8")
            payload = json.dumps({"command": command, "cwd": cwd,
                                  "transcript_path": transcript_path, "repo": repo})
            proc = subprocess.run(["python3", "-I", str(script)], input=payload, cwd=cwd,
                                  capture_output=True, text=True, timeout=TIMEOUT)
        verdict = json.loads(proc.stdout)
        allowed = proc.returncode == 0 and verdict.get("allow") is True
        reason = str(verdict.get("reason") or "").strip()
        if not reason:
            return False, f"the rules in {ref}:{RULES_PATH} gave no reason"
        if allowed and not _log(repo, cwd, command, ref, reason):
            return False, f"the rules allowed it, but {LOG} could not be written, so it is refused"
        return allowed, f"{ref}:{RULES_PATH}: {reason}"
    except subprocess.TimeoutExpired:
        return False, f"the auto-consent rules did not answer within {TIMEOUT} s"
    except Exception as exc:  # consent fails closed on anything unexpected
        return False, f"the auto-consent rules failed ({type(exc).__name__})"


def _log(repo, cwd, command, ref, reason):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "repo": repo, "cwd": cwd,
                                 "command": command, "rules": ref, "reason": reason}) + "\n")
        return True
    except OSError:
        return False
