"""Tests for reply-length-gate.sh: a short message gets a short reply.

Run: python3 -I -m unittest discover -s claude/hooks/tests
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "reply-length-gate.sh"
LONG_REPLY = " ".join(["palabra"] * 150)


def run_gate(said, replied):
    """Return the block reason, or None when the reply goes out."""
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "t.jsonl"
        records = [
            {"type": "user", "message": {"role": "user", "content": said}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "text", "text": replied}]}},
        ]
        transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
        payload = {"transcript_path": str(transcript)}
        out = subprocess.run(["bash", str(GATE)], input=json.dumps(payload),
                             capture_output=True, text=True, timeout=20).stdout
    return json.loads(out)["reason"] if out.strip() else None


class ReplyLengthGate(unittest.TestCase):
    def test_long_reply_to_short_message_is_bounced(self):
        self.assertIsNotNone(run_gate("¿ese hook es necesario?", LONG_REPLY))

    def test_short_reply_goes_out(self):
        self.assertIsNone(run_gate("¿ese hook es necesario?", "Sí."))

    def test_asking_for_information_allows_length(self):
        # "dame más información" asked for detail and was bounced (1 Nov).
        self.assertIsNone(run_gate("dame más información sobre el panel de Arsys", LONG_REPLY))

    def test_information_without_accent_allows_length(self):
        self.assertIsNone(run_gate("dame mas informacion sobre el panel", LONG_REPLY))

    def test_castilian_explain_allows_length(self):
        self.assertIsNone(run_gate("explícame por qué falla", LONG_REPLY))

    def test_long_message_allows_long_reply(self):
        self.assertIsNone(run_gate(" ".join(["palabra"] * 40), LONG_REPLY))


if __name__ == "__main__":
    unittest.main()
