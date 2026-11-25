"""Tests for agent-shell.sh, the SessionStart hook that gives the Bash tool plain commands.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
HOOK = HOOKS / "agent-shell.sh"
ZSHRC = HOOKS.parent.parent / "shell" / ".zshrc"


def run_hook(env_file: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    if env_file is not None:
        env["CLAUDE_ENV_FILE"] = env_file
    return subprocess.run(
        ["bash", str(HOOK)],
        input='{"hook_event_name": "SessionStart"}',
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


class AgentShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.env_file = os.path.join(self.dir, "env.sh")

    def tearDown(self) -> None:
        shutil.rmtree(self.dir)

    def test_exits_quietly_without_an_env_file(self) -> None:
        proc = run_hook(None)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_writes_each_line_once_when_run_twice(self) -> None:
        Path(self.env_file).write_text("export FROM_ANOTHER_HOOK=1\n")
        self.assertEqual(run_hook(self.env_file).returncode, 0)
        self.assertEqual(run_hook(self.env_file).returncode, 0)
        lines = Path(self.env_file).read_text().splitlines()
        self.assertEqual(lines[0], "export FROM_ANOTHER_HOOK=1")
        self.assertEqual(len(lines), len(set(lines)))
        self.assertEqual(len(lines), 3)

    @unittest.skipUnless(shutil.which("zsh"), "needs zsh")
    def test_the_agent_shell_gets_plain_commands_and_options(self) -> None:
        run_hook(self.env_file)
        # The aliases as the shell snapshot carries them, then the env file,
        # then the command, as Claude Code runs a Bash call.
        script = (
            "alias ls='eza -a' rm=trash find=fd du=ncdu\n"
            f"source {self.env_file}\n"
            "type rm; type ls; echo =====; echo nada-*.xyz\n"
        )
        proc = subprocess.run(
            ["zsh", "-f"], input=script, capture_output=True, text=True,
            timeout=10, cwd=self.dir,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.splitlines()
        self.assertEqual(out[0], "rm is /bin/rm")
        self.assertEqual(out[1], "ls is /bin/ls")
        self.assertEqual(out[2:], ["=====", "nada-*.xyz"])

    def test_undoes_every_command_replacing_alias_of_zshrc(self) -> None:
        # The aliases of .zshrc that stand in for a standard command, and the
        # hook's unalias line, name the same commands.
        replacing = {"ls", "ll", "lt", "cat", "find", "rm", "top", "man", "diff", "du"}
        aliased = set()
        for line in ZSHRC.read_text().splitlines():
            line = line.strip()
            if line.startswith("alias "):
                aliased.add(line[len("alias "):].split("=", 1)[0])
        self.assertTrue(replacing <= aliased, replacing - aliased)
        unalias = next(
            l for l in HOOK.read_text().splitlines() if "'unalias " in l
        )
        for name in replacing:
            self.assertIn(f" {name} ", unalias + " ")


if __name__ == "__main__":
    unittest.main()
