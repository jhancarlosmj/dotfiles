"""Tests for the file trail: which files a session wrote, edited and read."""

from __future__ import annotations

import json
from pathlib import Path

from src import summariser
from src.parsers.jsonl import extract_file_trail


def _tool_use(name: str, **tool_input: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "t", "name": name, "input": tool_input}],
        },
    }


def _write(path: Path, lines: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def test_trail_buckets_files_by_tool(tmp_path: Path) -> None:
    p = _write(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"role": "user", "content": "write the plan"}},
        _tool_use("Read", file_path="/repo/a.py"),
        _tool_use("Edit", file_path="/repo/b.py", old_string="x", new_string="y"),
        _tool_use("Write", file_path="/Users/me/Desktop/plan.md", content="# Plan"),
        _tool_use("NotebookEdit", notebook_path="/repo/n.ipynb", new_source="1"),
    ])
    assert extract_file_trail(p) == {
        "written": ["/Users/me/Desktop/plan.md"],
        "edited": ["/repo/b.py", "/repo/n.ipynb"],
        "read": ["/repo/a.py"],
    }


def test_trail_keeps_each_path_in_its_strongest_bucket_once(tmp_path: Path) -> None:
    p = _write(tmp_path / "s.jsonl", [
        _tool_use("Read", file_path="/repo/a.py"),
        _tool_use("Edit", file_path="/repo/a.py", old_string="x", new_string="y"),
        _tool_use("Read", file_path="/repo/a.py"),
        _tool_use("Write", file_path="/repo/new.md", content="1"),
        _tool_use("Edit", file_path="/repo/new.md", old_string="1", new_string="2"),
    ])
    assert extract_file_trail(p) == {
        "written": ["/repo/new.md"],
        "edited": ["/repo/a.py"],
        "read": [],
    }


def test_trail_ignores_bash_and_claude_bookkeeping(tmp_path: Path) -> None:
    p = _write(tmp_path / "s.jsonl", [
        _tool_use("Bash", command="echo secret > /tmp/out.txt", description="x"),
        _tool_use("Read", file_path="/Users/me/.claude/projects/p/abc/tool-results/x.txt"),
        "not a dict",
        _tool_use("Write", file_path="   "),
    ])
    assert extract_file_trail(p) == {"written": [], "edited": [], "read": []}


def test_trail_missing_file_is_empty(tmp_path: Path) -> None:
    assert extract_file_trail(tmp_path / "nope.jsonl") == {"written": [], "edited": [], "read": []}


def test_format_file_trail_empty_is_blank() -> None:
    assert summariser.format_file_trail(None) == ""
    assert summariser.format_file_trail({"written": [], "edited": [], "read": []}) == ""


def test_format_file_trail_caps_long_buckets() -> None:
    reads = [f"/repo/f{i}.py" for i in range(summariser.MAX_TRAIL_PATHS + 3)]
    block = summariser.format_file_trail({"written": ["/repo/w.md"], "edited": [], "read": reads})
    assert block.startswith("<file_trail>\nwritten: /repo/w.md\n")
    assert "read: ... and 3 more" in block
    assert f"/repo/f{summariser.MAX_TRAIL_PATHS}.py" not in block


def test_run_claude_puts_trail_before_transcript(monkeypatch) -> None:
    seen = {}

    class _Proc:
        returncode = 0
        stdout = json.dumps({"subtype": "success", "is_error": False, "result": "{}"})
        stderr = ""

    def _fake_run(cmd, input, **kwargs):  # noqa: A002 - subprocess's name
        seen["prompt"] = input
        return _Proc()

    monkeypatch.setattr(summariser.subprocess, "run", _fake_run)
    summariser.run_claude("hello", file_trail={"written": ["/x/plan.md"], "edited": [], "read": []})
    prompt = seen["prompt"]
    assert "written: /x/plan.md" in prompt
    # The intro sentence names the tag too, so match the opening tag on its own line.
    assert prompt.index("</file_trail>") < prompt.index("\n<transcript>\n")


def test_render_page_lists_files_from_the_trail() -> None:
    fields = {"title": "T", "tags": [], "request": "R.", "investigated": [],
              "learned": [], "completed": ["c"], "next_steps": []}
    common = dict(date="2026-10-25", domain="personal", project="p", session_id="s",
                  model="haiku", needs_review=False, transcript_path="/t.jsonl")
    page = summariser.render_page(
        fields, **common,
        file_trail={"written": ["/Users/me/Desktop/plan.md"], "edited": [], "read": ["/a.py"]},
    )
    assert "## Files\n\n- Written: `/Users/me/Desktop/plan.md`\n- Read: `/a.py`\n" in page
    assert page.index("## Files") < page.index("## Source")
    assert "## Files" not in summariser.render_page(fields, **common)
