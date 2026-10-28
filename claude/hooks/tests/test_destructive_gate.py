"""Tests for destructive-gate.sh: destructive shell commands need a named go.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "destructive-gate.sh"
SCRATCH = "/private/tmp/claude-501/-Users-me/session/scratchpad"


def human(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool_call(name, tool_input, result, cwd="/Users/me/project", call_id="t1"):
    """An assistant tool call and its result, as the transcript records them."""
    return [
        {"type": "assistant", "cwd": cwd, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}]}},
        {"type": "user", "cwd": cwd, "toolUseResult": {}, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": result}]}},
    ]


def run_gate(command, said=(), cwd="/Users/me/project", tool="Bash", history=()):
    """Return the deny reason, or None when the command is allowed."""
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "t.jsonl"
        records = [human(t) for t in said] + list(history)
        transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
        payload = {
            "tool_name": tool,
            "tool_input": {"command": command},
            "cwd": cwd,
            "transcript_path": str(transcript),
        }
        proc = subprocess.run(
            ["bash", str(GATE)], input=json.dumps(payload),
            capture_output=True, text=True, timeout=15, check=True,
        )
    if not proc.stdout.strip():
        return None
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


class DetectionTest(unittest.TestCase):
    def assertBlocked(self, command, **kw):
        self.assertIsNotNone(run_gate(command, **kw), command)

    def assertAllowed(self, command, **kw):
        self.assertIsNone(run_gate(command, **kw), command)

    def test_blocks_deletes_outside_scratch(self):
        for cmd in [
            "rm -rf ~/Movies/old",
            "rm notes.md",
            "cd /Volumes/NAS && rm -r Fotos",
            "sudo rm -f /etc/hosts",
            "/bin/rm x",
            "unlink ~/a",
            "find ~/Downloads -name '*.mkv' -delete",
            "find . -type f -exec rm {} +",
            "ls | xargs rm",
            "rsync -a --delete src/ /Volumes/NAS/dst/",
            "ssh minipc 'rm -rf /srv/media/old'",
            "bash -c 'rm -rf build'",
            "shred -u secret.txt",
            "dd if=/dev/zero of=/dev/disk4",
            "diskutil eraseDisk APFS X disk4",
            "rm -rf $DIR",
            "rm -rf /private/tmp/claude-501",
        ]:
            self.assertBlocked(cmd)

    def test_blocks_git_commands_that_discard_work(self):
        for cmd in [
            "git reset --hard HEAD~1",
            "git -C ~/repo clean -fdx",
            "git checkout -- src/app.ts",
            "git checkout .",
            "git restore src/app.ts",
            "git stash drop",
            "git branch -D feature",
            "git branch --delete --force feature",
        ]:
            self.assertBlocked(cmd)

    def test_allows_session_scratch(self):
        self.assertAllowed(f"rm -rf {SCRATCH}/repo")
        self.assertAllowed(f"rm -f {SCRATCH}/a.txt 2>/dev/null")
        self.assertAllowed(f"cd {SCRATCH} && rm -rf repo out.tsv")
        self.assertAllowed("rm -rf repo", cwd=SCRATCH)
        self.assertAllowed(f"find {SCRATCH}/old -delete")

    def test_resolves_variables_assigned_in_the_same_command(self):
        self.assertAllowed(f"S={SCRATCH}; rm -rf $S/out ${{S}}/b")
        self.assertAllowed(f"export SP={SCRATCH}/apk; cd $SP && rm -f *.apk")
        self.assertBlocked("S=~/Movies; rm -rf $S/old")
        self.assertBlocked(f"S=$HOME/x; rm -rf $S")
        self.assertBlocked("rm -rf $UNSET/old")

    def test_scratch_escape_is_blocked(self):
        self.assertBlocked(f"rm -rf {SCRATCH}/../../../../Users/me")
        self.assertBlocked(f"rm -rf {SCRATCH}/a ~/b")

    def test_allows_safe_commands(self):
        for cmd in [
            "ls -la",
            "git status --porcelain",
            "git restore --staged src/app.ts",
            "git branch -d merged",
            'git commit -m "rm the old flag"',
            "grep -rn 'rm -rf' scripts",
            "echo done; trash ~/old.txt",
            "cat > notes.md <<'EOF'\nrm -rf / is the classic mistake\nEOF",
        ]:
            self.assertAllowed(cmd)

    def test_ignores_other_tools(self):
        self.assertAllowed("rm -rf ~", tool="Read")


class SessionCreatedTest(unittest.TestCase):
    def test_file_the_session_wrote_new_can_be_removed(self):
        history = tool_call("Write", {"file_path": "/Users/me/project/.pr-body.md", "content": "x"},
                            "File created successfully at: /Users/me/project/.pr-body.md")
        self.assertIsNone(run_gate("rm .pr-body.md", history=history))

    def test_file_the_session_overwrote_is_still_gated(self):
        history = tool_call("Write", {"file_path": "/Users/me/project/README.md", "content": "x"},
                            "The file /Users/me/project/README.md has been updated successfully.")
        self.assertIsNotNone(run_gate("rm README.md", history=history))

    def test_cp_and_redirect_targets_count_as_created(self):
        history = tool_call("Bash", {"command": "cp .env.example .env && echo hi > out.txt"}, "hi")
        self.assertIsNone(run_gate("rm .env out.txt", history=history))
        self.assertIsNotNone(run_gate("rm .env.example", history=history))

    def test_create_and_remove_in_the_same_command(self):
        cmd = "cat > .pr-body.md <<'EOF'\nBody\nEOF\ngh pr create --body-file .pr-body.md && rm .pr-body.md"
        self.assertIsNone(run_gate(cmd))

    def test_mv_destination_is_not_treated_as_created(self):
        history = tool_call("Bash", {"command": "mv ~/notes.md /Users/me/project/n.md"}, "")
        self.assertIsNotNone(run_gate("rm n.md", history=history))

    def test_one_unknown_target_keeps_the_gate(self):
        history = tool_call("Bash", {"command": "echo x > a.txt"}, "")
        self.assertIsNotNone(run_gate("rm a.txt b.txt", history=history))


class ApprovalTest(unittest.TestCase):
    CMD = "rm -rf ~/Movies/old"

    def test_named_go_in_spanish_or_english_allows(self):
        for said in ["sí, bórralos", "Elimina esos 3 ficheros", "ok, delete them", "descarta los cambios"]:
            self.assertIsNone(run_gate(self.CMD, said=[said]), said)

    def test_bare_yes_is_not_enough(self):
        self.assertIsNotNone(run_gate(self.CMD, said=["sí", "adelante"]))

    def test_veto_cancels_an_earlier_go(self):
        self.assertIsNotNone(run_gate(self.CMD, said=["borra la carpeta", "espera, no borres nada"]))
        self.assertIsNotNone(run_gate(self.CMD, said=["don't delete anything yet"]))

    def test_go_expires_after_three_turns(self):
        said = ["borra la carpeta", "otra cosa", "y esto", "y aquello"]
        self.assertIsNotNone(run_gate(self.CMD, said=said))

    def test_reason_explains_how_to_ask(self):
        reason = run_gate(self.CMD)
        self.assertIn("rm ~/Movies/old", reason)
        self.assertIn("sample", reason)


if __name__ == "__main__":
    unittest.main()
