#!/bin/bash
# Stop hook: a short message from Warren gets a short reply.
#
# When his latest message is under 30 words and did not ask for a written
# artefact (explain, draft, list, report, plan, review...), a reply over 120
# words of prose (code fences excluded) is bounced back once with a reason. The
# rewrite then goes out. Brevity had been written into CLAUDE.md, the output
# style and a memory file and was still the most repeated complaint of 2026;
# this is the first mechanical check of it.
set -uo pipefail
input=$(cat)
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$input" HOOKS_DIR="$HOOKS_DIR" python3 - <<'PY'
import json, os, re, sys
sys.path.insert(0, os.environ["HOOKS_DIR"])
from lib_transcript import last_turns, words

try:
    call = json.loads(os.environ["INPUT"])
except Exception:
    sys.exit(0)
if call.get("stop_hook_active"):
    sys.exit(0)
human, assistant = last_turns(call.get("transcript_path", ""))
if not human or not assistant:
    sys.exit(0)
hw, aw = words(human), words(assistant)
if hw >= 30 or aw <= 120:
    sys.exit(0)
ASKS_FOR_LENGTH_EN = (
    r"explain|detail|detailed|write|draft|list|report|summar\w*|teach|describe"
    r"|compare|plan|review|document|essay|article|deck|email|walk me|in depth"
    r"|elaborate|everything|all of|why"
)
# Warren writes to me in Castilian, so an English-only list let "resume esto"
# or "explícame por qué" be penalised for the length they asked for.
# Verbs only, and only ones that mean "produce something written": "crea",
# "arregla" or "añade" stay out, because the deliverable there is the file.
ASKS_FOR_LENGTH_ES = (
    r"resum\w*|res\u00fam\w*|explic\w*|expl\u00edc\w*|detall\w*|describ\w*|desglos\w*"
    r"|redact\w*|escrib\w*|escr\u00edb\w*|document\w*|informes?|an\u00e1lisis|analisis|analiz\w*"
    r"|audit\w*|revis\w*|compara\w*|comparaci\w*|listad\w*|lista|listar"
    r"|planific\w*|profundiz\w*|ampl\u00ed\w*|elabor\w*|ense\u00f1\w*|ens\u00e9\u00f1\w*"
    r"|gu\u00eda|art\u00edculo|articulo|ensayo|propuest\w*|cu\u00e9nta\w*|cuenta\w*"
    r"|por qu\u00e9|porqu\w*|en detalle|a fondo|todo lo|todos los|todas las"
)
ASKS_FOR_LENGTH = r"\b(" + ASKS_FOR_LENGTH_EN + r"|" + ASKS_FOR_LENGTH_ES + r")\b"
if re.search(ASKS_FOR_LENGTH, human, re.I):
    sys.exit(0)
reason = (
    f"Reply is {aw} words of prose to a {hw}-word message. Send the answer alone: "
    "no headings, no recap of what was done, no bullets unless the content is a list, one decision at most."
)
print(json.dumps({"decision": "block", "reason": reason}))
PY
